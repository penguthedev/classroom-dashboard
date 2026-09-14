from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged
from app.api.notifications import (
    fan_out,
    notify_schedule_change,
    recipients_for_class,
)
from app.db.session import get_db
from app.models import Class, Enrollment, Room, Schedule, Subject, User
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.enums import to_api_role
from app.schemas.schedule import (
    ScheduleConflict,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
)

router = APIRouter()

ACTIVE_STATUSES = ("scheduled", "rescheduled")

CONSTRAINT_RESOURCES = {
    "ex_schedule_room_overlap": "room",
    "ex_schedule_lecturer_overlap": "lecturer",
    "ex_schedule_tutor_overlap": "tutor",
}

LOAD = [
    joinedload(Schedule.class_).joinedload(Class.subject).joinedload(Subject.department),
    joinedload(Schedule.room).joinedload(Room.building),
    joinedload(Schedule.lecturer),
    joinedload(Schedule.tutor),
]


def get_schedule_or_404(db: Session, schedule_id: int) -> Schedule:
    row = db.scalars(
        select(Schedule).where(Schedule.id == schedule_id).options(*LOAD)
    ).unique().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return row


def scope_for_user(stmt, current_user: User):
    if is_privileged(current_user):
        return stmt
    role = to_api_role(current_user.role)
    if role == "student":
        return stmt.where(
            Schedule.class_id.in_(
                select(Enrollment.class_id).where(
                    Enrollment.student_id == current_user.id
                )
            )
        )
    return stmt.where(
        or_(
            Schedule.lecturer_id == current_user.id,
            Schedule.tutor_id == current_user.id,
            Schedule.class_id.in_(
                select(Class.id).where(
                    or_(
                        Class.lecturer_id == current_user.id,
                        Class.tutor_id == current_user.id,
                    )
                )
            ),
        )
    )


def can_manage_class(db: Session, current_user: User, class_id: int) -> bool:
    if is_privileged(current_user):
        return True
    class_row = db.get(Class, class_id)
    if class_row is None:
        return False
    return current_user.id in (class_row.lecturer_id, class_row.tutor_id)


def find_conflicts(
    db: Session,
    room_id: int,
    lecturer_id: int,
    tutor_id: int | None,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: int | None = None,
) -> list[ScheduleConflict]:
    overlap = and_(Schedule.starts_at < ends_at, Schedule.ends_at > starts_at)
    targets = [Schedule.room_id == room_id, Schedule.lecturer_id == lecturer_id]
    if tutor_id is not None:
        targets.append(Schedule.tutor_id == tutor_id)

    stmt = (
        select(Schedule)
        .where(Schedule.status.in_(ACTIVE_STATUSES))
        .where(overlap)
        .where(or_(*targets))
        .options(joinedload(Schedule.room), joinedload(Schedule.lecturer))
    )
    if exclude_id is not None:
        stmt = stmt.where(Schedule.id != exclude_id)

    conflicts: list[ScheduleConflict] = []
    for row in db.scalars(stmt).unique().all():
        if row.room_id == room_id:
            conflicts.append(
                build_conflict(row, "room", f"Room {row.room.code} is already booked")
            )
        if row.lecturer_id == lecturer_id:
            conflicts.append(
                build_conflict(
                    row, "lecturer", f"{row.lecturer.name} already teaches at this time"
                )
            )
        if tutor_id is not None and row.tutor_id == tutor_id:
            conflicts.append(
                build_conflict(row, "tutor", "The tutor is already assigned at this time")
            )
    return conflicts


def shared_student_count(db: Session, class_id: int, other_class_id: int) -> int:
    cohort = select(Enrollment.student_id).where(Enrollment.class_id == class_id)
    stmt = (
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.class_id == other_class_id)
        .where(Enrollment.student_id.in_(cohort))
    )
    return db.scalar(stmt) or 0


def find_cohort_conflicts(
    db: Session,
    class_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: int | None = None,
) -> list[ScheduleConflict]:
    cohort = select(Enrollment.student_id).where(Enrollment.class_id == class_id)
    cohort_classes = select(Enrollment.class_id).where(
        Enrollment.student_id.in_(cohort)
    )

    stmt = (
        select(Schedule)
        .where(Schedule.status.in_(ACTIVE_STATUSES))
        .where(and_(Schedule.starts_at < ends_at, Schedule.ends_at > starts_at))
        .where(Schedule.class_id != class_id)
        .where(Schedule.class_id.in_(cohort_classes))
        .options(joinedload(Schedule.class_))
    )
    if exclude_id is not None:
        stmt = stmt.where(Schedule.id != exclude_id)

    conflicts: list[ScheduleConflict] = []
    for row in db.scalars(stmt).unique().all():
        affected = shared_student_count(db, class_id, row.class_id)
        if affected == 0:
            continue
        noun = "student" if affected == 1 else "students"
        conflicts.append(
            build_conflict(
                row,
                "students",
                f"{affected} enrolled {noun} already have {row.class_.name} at this time",
            )
        )
    return conflicts


def build_conflict(row: Schedule, resource: str, message: str) -> ScheduleConflict:
    return ScheduleConflict(
        resource=resource,
        schedule_id=row.id,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        message=message,
    )


def conflict_response(conflicts: list[ScheduleConflict]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "message": "This time slot conflicts with an existing schedule",
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
        },
    )


def integrity_to_conflict(exc: IntegrityError) -> HTTPException:
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    if sqlstate != "23P01":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "That schedule could not be saved", "conflicts": []},
        )

    text = str(original)
    resource = "schedule"
    for name, label in CONSTRAINT_RESOURCES.items():
        if name in text:
            resource = label
            break

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "message": f"This time slot conflicts with another booking for that {resource}",
            "conflicts": [
                {
                    "resource": resource,
                    "schedule_id": None,
                    "starts_at": None,
                    "ends_at": None,
                    "message": f"The {resource} is already booked for an overlapping slot",
                }
            ],
        },
    )


def validate_targets(db: Session, class_id: int, room_id: int, lecturer_id: int, tutor_id: int | None) -> None:
    if db.get(Class, class_id) is None:
        raise HTTPException(status_code=404, detail="Class not found")
    if db.get(Room, room_id) is None:
        raise HTTPException(status_code=404, detail="Room not found")

    lecturer = db.get(User, lecturer_id)
    if lecturer is None:
        raise HTTPException(status_code=404, detail="Lecturer not found")
    if to_api_role(lecturer.role) not in ("lecturer", "tutor"):
        raise HTTPException(
            status_code=422, detail=f"{lecturer.name} is not teaching staff"
        )

    if tutor_id is not None:
        tutor = db.get(User, tutor_id)
        if tutor is None:
            raise HTTPException(status_code=404, detail="Tutor not found")
        if to_api_role(tutor.role) not in ("tutor", "lecturer"):
            raise HTTPException(status_code=422, detail=f"{tutor.name} is not a tutor")


@router.get("", response_model=ListResponse[ScheduleOut])
def list_schedules(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    class_id: int | None = None,
    room_id: int | None = None,
    lecturer_id: int | None = None,
    schedule_status: str | None = Query(None, alias="status"),
):
    stmt = select(Schedule)
    stmt = scope_for_user(stmt, current_user)

    if date_from is not None:
        stmt = stmt.where(Schedule.ends_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Schedule.starts_at <= date_to)
    if class_id is not None:
        stmt = stmt.where(Schedule.class_id == class_id)
    if room_id is not None:
        stmt = stmt.where(Schedule.room_id == room_id)
    if lecturer_id is not None:
        stmt = stmt.where(
            or_(Schedule.lecturer_id == lecturer_id, Schedule.tutor_id == lecturer_id)
        )
    if schedule_status:
        stmt = stmt.where(Schedule.status == schedule_status)

    rows, pagination = paginate(
        db, stmt.order_by(Schedule.starts_at, Schedule.id), page, limit, LOAD
    )
    return envelope([ScheduleOut.model_validate(r) for r in rows], pagination)


@router.get("/{schedule_id}", response_model=SingleResponse[ScheduleOut])
def get_schedule(
    schedule_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = get_schedule_or_404(db, schedule_id)
    allowed = db.scalars(
        scope_for_user(select(Schedule.id).where(Schedule.id == schedule_id), current_user)
    ).one_or_none()
    if allowed is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return SingleResponse[ScheduleOut](data=ScheduleOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[ScheduleOut], status_code=status.HTTP_201_CREATED
)
def create_schedule(
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not can_manage_class(db, current_user, payload.class_id):
        raise HTTPException(
            status_code=403, detail="You do not have permission to schedule this class"
        )

    validate_targets(
        db, payload.class_id, payload.room_id, payload.lecturer_id, payload.tutor_id
    )

    conflicts = find_conflicts(
        db,
        payload.room_id,
        payload.lecturer_id,
        payload.tutor_id,
        payload.starts_at,
        payload.ends_at,
    )
    conflicts += find_cohort_conflicts(
        db, payload.class_id, payload.starts_at, payload.ends_at
    )
    if conflicts:
        raise conflict_response(conflicts)

    row = Schedule(**payload.model_dump())
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_to_conflict(exc) from exc

    class_row = db.get(Class, row.class_id)
    notify_schedule_change(
        db,
        row,
        "schedule_created",
        f"New session for {class_row.name}",
        f"{row.starts_at.isoformat()} to {row.ends_at.isoformat()}",
        actor_id=current_user.id,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_to_conflict(exc) from exc

    return SingleResponse[ScheduleOut](
        data=ScheduleOut.model_validate(get_schedule_or_404(db, row.id))
    )


@router.patch("/{schedule_id}", response_model=SingleResponse[ScheduleOut])
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = get_schedule_or_404(db, schedule_id)
    if not can_manage_class(db, current_user, row.class_id):
        raise HTTPException(
            status_code=403, detail="You do not have permission to edit this schedule"
        )

    data = payload.model_dump(exclude_unset=True)

    class_id = data.get("class_id", row.class_id)
    room_id = data.get("room_id", row.room_id)
    lecturer_id = data.get("lecturer_id", row.lecturer_id)
    tutor_id = data.get("tutor_id", row.tutor_id)
    starts_at = data.get("starts_at", row.starts_at)
    ends_at = data.get("ends_at", row.ends_at)
    new_status = data.get("status", row.status)

    if ends_at <= starts_at:
        raise HTTPException(status_code=422, detail="ends_at must be after starts_at")

    validate_targets(db, class_id, room_id, lecturer_id, tutor_id)

    if new_status in ACTIVE_STATUSES:
        conflicts = find_conflicts(
            db, room_id, lecturer_id, tutor_id, starts_at, ends_at, exclude_id=row.id
        )
        conflicts += find_cohort_conflicts(
            db, class_id, starts_at, ends_at, exclude_id=row.id
        )
        if conflicts:
            raise conflict_response(conflicts)

    time_changed = starts_at != row.starts_at or ends_at != row.ends_at
    status_changed = new_status != row.status

    for key, value in data.items():
        setattr(row, key, value)

    if time_changed and new_status == "scheduled":
        row.status = "rescheduled"

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_to_conflict(exc) from exc

    class_row = db.get(Class, row.class_id)
    if new_status == "cancelled" and status_changed:
        notify_schedule_change(
            db,
            row,
            "schedule_cancelled",
            f"Session cancelled for {class_row.name}",
            f"The session on {row.starts_at.isoformat()} has been cancelled",
            actor_id=current_user.id,
        )
    elif time_changed or status_changed:
        notify_schedule_change(
            db,
            row,
            "schedule_updated",
            f"Session updated for {class_row.name}",
            f"{row.starts_at.isoformat()} to {row.ends_at.isoformat()}",
            actor_id=current_user.id,
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise integrity_to_conflict(exc) from exc

    return SingleResponse[ScheduleOut](
        data=ScheduleOut.model_validate(get_schedule_or_404(db, row.id))
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = get_schedule_or_404(db, schedule_id)
    if not can_manage_class(db, current_user, row.class_id):
        raise HTTPException(
            status_code=403, detail="You do not have permission to remove this schedule"
        )

    class_row = db.get(Class, row.class_id)
    starts_at = row.starts_at.isoformat()
    recipients = recipients_for_class(db, class_row) if class_row else set()

    db.delete(row)
    db.flush()

    fan_out(
        db,
        recipients,
        "schedule_cancelled",
        f"Session removed for {class_row.name}" if class_row else "Session removed",
        f"The session on {starts_at} has been removed",
        schedule_id=None,
        exclude=current_user.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
