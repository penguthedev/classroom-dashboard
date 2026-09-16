from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged
from app.api.notifications import fan_out
from app.db.session import get_db
from app.models import Class, Enrollment, Subject, User
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.enrollment import EnrollmentCreate, EnrollmentJoin, EnrollmentOut
from app.schemas.enums import to_api_role

router = APIRouter()

LOAD = [
    joinedload(Enrollment.student),
    joinedload(Enrollment.class_).joinedload(Class.subject).joinedload(Subject.department),
]


def seats_taken(db: Session, class_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.class_id == class_id)
    ) or 0


def assert_capacity(db: Session, class_row: Class) -> None:
    if seats_taken(db, class_row.id) >= class_row.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{class_row.name} is full ({class_row.capacity} seats)",
        )


def assert_not_enrolled(db: Session, student_id: int, class_id: int) -> None:
    existing = db.scalars(
        select(Enrollment.id)
        .where(Enrollment.student_id == student_id, Enrollment.class_id == class_id)
        .limit(1)
    ).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student is already enrolled in that class",
        )


def load_enrollment(db: Session, enrollment_id: int) -> Enrollment:
    row = db.scalars(
        select(Enrollment).where(Enrollment.id == enrollment_id).options(*LOAD)
    ).unique().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return row


def can_manage_enrollment(db: Session, current_user: User, row: Enrollment) -> bool:
    if is_privileged(current_user):
        return True
    if row.student_id == current_user.id:
        return True
    class_row = db.get(Class, row.class_id)
    if class_row is None:
        return False
    return current_user.id in (class_row.lecturer_id, class_row.tutor_id)


def commit_enrollment(db: Session, row: Enrollment) -> Enrollment:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student is already enrolled in that class",
        ) from exc
    return load_enrollment(db, row.id)


@router.get("", response_model=ListResponse[EnrollmentOut])
def list_enrollments(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    class_id: int | None = None,
    student_id: int | None = None,
    search: str | None = None,
):
    stmt = select(Enrollment)

    if not is_privileged(current_user):
        if to_api_role(current_user.role) == "student":
            stmt = stmt.where(Enrollment.student_id == current_user.id)
        else:
            stmt = stmt.where(
                Enrollment.class_id.in_(
                    select(Class.id).where(
                        or_(
                            Class.lecturer_id == current_user.id,
                            Class.tutor_id == current_user.id,
                        )
                    )
                )
            )

    if class_id is not None:
        stmt = stmt.where(Enrollment.class_id == class_id)
    if student_id is not None:
        stmt = stmt.where(Enrollment.student_id == student_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.join(Enrollment.student).where(
            or_(User.name.ilike(pattern), User.email.ilike(pattern))
        )

    rows, pagination = paginate(
        db, stmt.order_by(Enrollment.id.desc()), page, limit, LOAD
    )
    return envelope([EnrollmentOut.model_validate(r) for r in rows], pagination)


@router.get("/{enrollment_id}", response_model=SingleResponse[EnrollmentOut])
def get_enrollment(
    enrollment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = load_enrollment(db, enrollment_id)
    if not can_manage_enrollment(db, current_user, row):
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return SingleResponse[EnrollmentOut](data=EnrollmentOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[EnrollmentOut], status_code=status.HTTP_201_CREATED
)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    class_row = db.get(Class, payload.class_id)
    if class_row is None:
        raise HTTPException(status_code=404, detail="Class not found")

    student = db.get(User, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if to_api_role(student.role) != "student":
        raise HTTPException(status_code=422, detail=f"{student.name} is not a student")

    allowed = is_privileged(current_user) or current_user.id in (
        class_row.lecturer_id,
        class_row.tutor_id,
    )
    if not allowed:
        raise HTTPException(
            status_code=403, detail="You do not have permission to enroll students"
        )

    if class_row.status != "active":
        raise HTTPException(status_code=409, detail="That class is archived")

    assert_not_enrolled(db, student.id, class_row.id)
    assert_capacity(db, class_row)

    row = Enrollment(student_id=student.id, class_id=class_row.id)
    db.add(row)
    db.flush()

    fan_out(
        db,
        {student.id},
        "enrollment",
        f"You have been enrolled in {class_row.name}",
        f"Subject {class_row.subject.code} - {class_row.subject.name}",
    )

    return SingleResponse[EnrollmentOut](
        data=EnrollmentOut.model_validate(commit_enrollment(db, row))
    )


@router.post(
    "/join",
    response_model=SingleResponse[EnrollmentOut],
    status_code=status.HTTP_201_CREATED,
)
def join_by_invite_code(
    payload: EnrollmentJoin,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if to_api_role(current_user.role) != "student":
        raise HTTPException(
            status_code=403, detail="Only students can join a class with an invite code"
        )

    class_row = db.scalars(
        select(Class)
        .where(Class.invite_code == payload.invite_code.strip().upper())
        .limit(1)
    ).one_or_none()
    if class_row is None:
        raise HTTPException(status_code=404, detail="That invite code is not valid")
    if class_row.status != "active":
        raise HTTPException(status_code=409, detail="That class is archived")

    assert_not_enrolled(db, current_user.id, class_row.id)
    assert_capacity(db, class_row)

    row = Enrollment(student_id=current_user.id, class_id=class_row.id)
    db.add(row)
    db.flush()

    recipients = {class_row.lecturer_id}
    if class_row.tutor_id is not None:
        recipients.add(class_row.tutor_id)
    fan_out(
        db,
        recipients,
        "enrollment",
        f"{current_user.name} joined {class_row.name}",
        f"Enrolled with invite code {class_row.invite_code}",
    )

    return SingleResponse[EnrollmentOut](
        data=EnrollmentOut.model_validate(commit_enrollment(db, row))
    )


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(
    enrollment_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = load_enrollment(db, enrollment_id)
    if not can_manage_enrollment(db, current_user, row):
        raise HTTPException(
            status_code=403, detail="You do not have permission to remove this enrollment"
        )
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
