from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.classes import generate_invite_code
from app.api.enrollments import assert_capacity, assert_not_enrolled
from app.api.notifications import fan_out, notify_schedule_change, recipients_for_class
from app.api.schedules import find_conflicts, validate_targets
from app.models import (
    Building,
    Class,
    Department,
    Enrollment,
    Faculty,
    Notification,
    Programme,
    Room,
    Schedule,
    StaffProfile,
    StudentProfile,
    Subject,
    User,
)
from app.schemas.enums import PRIVILEGED_ROLES, TEACHING_ROLES, to_api_role, to_db_role

MAX_ROWS = 50


@dataclass
class ToolContext:
    db: Session
    user: User
    mutations: list[dict[str, Any]] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)


class ToolError(Exception):
    pass


def role_of(user: User) -> str:
    return to_api_role(user.role)


def is_privileged(user: User) -> bool:
    return role_of(user) in PRIVILEGED_ROLES


def is_teacher(user: User) -> bool:
    return role_of(user) in TEACHING_ROLES


def clamp(value: Any, default: int = 20) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, MAX_ROWS))


def parse_time(value: Any, label: str) -> datetime:
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ToolError(f"{label} is not a valid ISO 8601 timestamp") from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def department_brief(row: Department | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {"id": row.id, "code": row.code, "name": row.name}


def subject_brief(row: Subject | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "department": department_brief(row.department),
    }


def person_brief(row: User | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "full_name": row.name,
        "email": row.email,
        "role": to_api_role(row.role),
    }


def class_brief(row: Class) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "capacity": row.capacity,
        "invite_code": row.invite_code,
        "subject": subject_brief(row.subject),
        "lecturer": person_brief(row.lecturer),
        "tutor": person_brief(row.tutor),
    }


def room_brief(row: Room | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "capacity": row.capacity,
        "room_type": row.room_type,
        "building": row.building.name if row.building else None,
    }


def schedule_brief(row: Schedule) -> dict[str, Any]:
    return {
        "id": row.id,
        "class_id": row.class_id,
        "class_name": row.class_.name if row.class_ else None,
        "subject": row.class_.subject.code if row.class_ and row.class_.subject else None,
        "starts_at": iso(row.starts_at),
        "ends_at": iso(row.ends_at),
        "status": row.status,
        "room": room_brief(row.room),
        "lecturer": person_brief(row.lecturer),
        "tutor": person_brief(row.tutor),
        "notes": row.notes,
    }


def visible_class_ids(ctx: ToolContext):
    if role_of(ctx.user) == "student":
        return select(Enrollment.class_id).where(Enrollment.student_id == ctx.user.id)
    return select(Class.id).where(
        or_(Class.lecturer_id == ctx.user.id, Class.tutor_id == ctx.user.id)
    )


def may_touch_class(ctx: ToolContext, row: Class) -> bool:
    if is_privileged(ctx.user):
        return True
    return ctx.user.id in (row.lecturer_id, row.tutor_id)


def require_confirmation(args: dict[str, Any], summary: str) -> dict[str, Any] | None:
    if bool(args.get("confirmed")):
        return None
    return {
        "status": "confirmation_required",
        "summary": summary,
        "instruction": "Tell the user exactly what will change and ask them to confirm. Call this tool again with confirmed=true only after they agree.",
    }


def get_my_profile(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    user = ctx.user
    payload: dict[str, Any] = {
        "id": user.id,
        "full_name": user.name,
        "username": user.username,
        "email": user.email,
        "role": role_of(user),
        "phone_number": user.phone,
        "is_active": user.is_active,
    }

    if user.student_profile is not None:
        student = user.student_profile
        payload["student_number"] = student.student_number
        payload["year_of_study"] = student.year_of_study
        payload["programme"] = (
            {"id": student.programme.id, "code": student.programme.code, "name": student.programme.name}
            if student.programme
            else None
        )
        payload["enrolled_class_count"] = ctx.db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.student_id == user.id)
        )

    if user.staff_profile is not None:
        staff = user.staff_profile
        payload["staff_number"] = staff.staff_number
        payload["position"] = staff.position
        payload["specialization"] = staff.specialization
        payload["qualification"] = staff.qualification
        payload["department"] = department_brief(staff.department)
        payload["classes_taught"] = ctx.db.scalar(
            select(func.count())
            .select_from(Class)
            .where(or_(Class.lecturer_id == user.id, Class.tutor_id == user.id))
        )

    return payload


def get_dashboard_overview(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    db = ctx.db

    def count(stmt) -> int:
        return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    now = datetime.now(UTC)
    week_end = now + timedelta(days=7)

    overview = {
        "faculties": count(select(Faculty.id)),
        "departments": count(select(Department.id)),
        "programmes": count(select(Programme.id)),
        "subjects": count(select(Subject.id)),
        "classes": count(select(Class.id)),
        "active_classes": count(select(Class.id).where(Class.status == "active")),
        "buildings": count(select(Building.id)),
        "rooms": count(select(Room.id)),
        "unread_notifications": count(
            select(Notification.id).where(
                Notification.user_id == ctx.user.id, Notification.read_at.is_(None)
            )
        ),
    }

    if is_privileged(ctx.user):
        overview["users"] = count(select(User.id))
        overview["enrollments"] = count(select(Enrollment.id))
        overview["users_by_role"] = {
            to_api_role(role): total
            for role, total in db.execute(
                select(User.role, func.count()).group_by(User.role)
            ).all()
        }

    overview["my_sessions_next_7_days"] = count(
        select(Schedule.id).where(
            Schedule.class_id.in_(visible_class_ids(ctx)),
            Schedule.starts_at >= now,
            Schedule.starts_at <= week_end,
            Schedule.status.in_(("scheduled", "rescheduled")),
        )
        if not is_privileged(ctx.user)
        else select(Schedule.id).where(
            Schedule.starts_at >= now, Schedule.starts_at <= week_end
        )
    )
    return overview


def list_my_classes(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    limit = clamp(args.get("limit"), 20)
    stmt = (
        select(Class)
        .where(Class.id.in_(visible_class_ids(ctx)))
        .options(
            joinedload(Class.subject).joinedload(Subject.department),
            joinedload(Class.lecturer),
            joinedload(Class.tutor),
        )
        .order_by(Class.name)
        .limit(limit)
    )
    rows = ctx.db.scalars(stmt).unique().all()
    return {
        "role": role_of(ctx.user),
        "count": len(rows),
        "classes": [class_brief(r) for r in rows],
    }


def list_my_schedule(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(UTC)
    starts = parse_time(args["from_date"], "from_date") if args.get("from_date") else now
    ends = (
        parse_time(args["to_date"], "to_date")
        if args.get("to_date")
        else starts + timedelta(days=14)
    )
    limit = clamp(args.get("limit"), 25)

    stmt = (
        select(Schedule)
        .where(Schedule.ends_at >= starts, Schedule.starts_at <= ends)
        .options(
            joinedload(Schedule.class_).joinedload(Class.subject),
            joinedload(Schedule.room).joinedload(Room.building),
            joinedload(Schedule.lecturer),
            joinedload(Schedule.tutor),
        )
        .order_by(Schedule.starts_at)
        .limit(limit)
    )

    if not is_privileged(ctx.user):
        stmt = stmt.where(
            or_(
                Schedule.class_id.in_(visible_class_ids(ctx)),
                Schedule.lecturer_id == ctx.user.id,
                Schedule.tutor_id == ctx.user.id,
            )
        )

    rows = ctx.db.scalars(stmt).unique().all()
    return {
        "window": {"from": iso(starts), "to": iso(ends)},
        "count": len(rows),
        "sessions": [schedule_brief(r) for r in rows],
    }


def get_class(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    db = ctx.db
    stmt = select(Class).options(
        joinedload(Class.subject).joinedload(Subject.department),
        joinedload(Class.lecturer),
        joinedload(Class.tutor),
    )

    if args.get("class_id"):
        stmt = stmt.where(Class.id == int(args["class_id"]))
    elif args.get("invite_code"):
        stmt = stmt.where(Class.invite_code == str(args["invite_code"]).strip().upper())
    else:
        raise ToolError("Provide either class_id or invite_code")

    row = db.scalars(stmt).unique().one_or_none()
    if row is None:
        raise ToolError("No class matches that identifier")

    enrolled = db.scalar(
        select(func.count()).select_from(Enrollment).where(Enrollment.class_id == row.id)
    )
    upcoming = db.scalars(
        select(Schedule)
        .where(
            Schedule.class_id == row.id,
            Schedule.starts_at >= datetime.now(UTC),
            Schedule.status.in_(("scheduled", "rescheduled")),
        )
        .options(joinedload(Schedule.room).joinedload(Room.building), joinedload(Schedule.lecturer))
        .order_by(Schedule.starts_at)
        .limit(5)
    ).unique().all()

    payload = class_brief(row)
    payload["description"] = row.description
    payload["enrolled_count"] = enrolled
    payload["seats_left"] = max(row.capacity - (enrolled or 0), 0)
    payload["upcoming_sessions"] = [schedule_brief(s) for s in upcoming]

    if not may_touch_class(ctx, row) and role_of(ctx.user) == "student":
        payload.pop("invite_code", None)

    return payload


def list_class_roster(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    class_id = int(args["class_id"])
    row = ctx.db.get(Class, class_id)
    if row is None:
        raise ToolError("No class with that id")
    if not may_touch_class(ctx, row):
        raise ToolError("You can only view the roster of classes you teach or administer")

    limit = clamp(args.get("limit"), 50)
    enrollments = ctx.db.scalars(
        select(Enrollment)
        .where(Enrollment.class_id == class_id)
        .options(joinedload(Enrollment.student).joinedload(User.student_profile))
        .order_by(Enrollment.id)
        .limit(limit)
    ).unique().all()

    return {
        "class": {"id": row.id, "name": row.name, "capacity": row.capacity},
        "count": len(enrollments),
        "students": [
            {
                "enrollment_id": e.id,
                "student_id": e.student_id,
                "full_name": e.student.name,
                "email": e.student.email,
                "student_number": (
                    e.student.student_profile.student_number
                    if e.student.student_profile
                    else None
                ),
                "enrolled_at": iso(e.enrolled_at),
            }
            for e in enrollments
        ],
    }


def search_classes(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Class).options(
        joinedload(Class.subject).joinedload(Subject.department),
        joinedload(Class.lecturer),
        joinedload(Class.tutor),
    )

    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(
            or_(Class.name.ilike(pattern), Class.description.ilike(pattern))
        )
    if args.get("subject"):
        stmt = stmt.join(Class.subject).where(
            or_(
                Subject.name.ilike(f"%{args['subject']}%"),
                Subject.code.ilike(f"%{args['subject']}%"),
            )
        )
    if args.get("department"):
        stmt = stmt.join(Class.subject).join(Subject.department).where(
            or_(
                Department.name.ilike(f"%{args['department']}%"),
                Department.code.ilike(f"%{args['department']}%"),
            )
        )
    if args.get("status"):
        stmt = stmt.where(Class.status == args["status"])

    rows = ctx.db.scalars(
        stmt.order_by(Class.name).limit(clamp(args.get("limit"), 20))
    ).unique().all()
    return {"count": len(rows), "classes": [class_brief(r) for r in rows]}


def search_subjects(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Subject).options(joinedload(Subject.department))
    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(or_(Subject.name.ilike(pattern), Subject.code.ilike(pattern)))
    if args.get("department"):
        stmt = stmt.join(Subject.department).where(
            or_(
                Department.name.ilike(f"%{args['department']}%"),
                Department.code.ilike(f"%{args['department']}%"),
            )
        )
    rows = ctx.db.scalars(
        stmt.order_by(Subject.code).limit(clamp(args.get("limit"), 25))
    ).unique().all()
    return {"count": len(rows), "subjects": [subject_brief(r) for r in rows]}


def list_departments(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Department).options(joinedload(Department.faculty))
    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(
            or_(Department.name.ilike(pattern), Department.code.ilike(pattern))
        )
    if args.get("faculty"):
        stmt = stmt.join(Department.faculty).where(
            or_(
                Faculty.name.ilike(f"%{args['faculty']}%"),
                Faculty.code.ilike(f"%{args['faculty']}%"),
            )
        )
    rows = ctx.db.scalars(
        stmt.order_by(Department.code).limit(clamp(args.get("limit"), 25))
    ).unique().all()
    return {
        "count": len(rows),
        "departments": [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "description": r.description,
                "faculty": r.faculty.name if r.faculty else None,
            }
            for r in rows
        ],
    }


def list_programmes(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Programme).options(joinedload(Programme.department))
    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(
            or_(Programme.name.ilike(pattern), Programme.code.ilike(pattern))
        )
    if args.get("department"):
        stmt = stmt.join(Programme.department).where(
            or_(
                Department.name.ilike(f"%{args['department']}%"),
                Department.code.ilike(f"%{args['department']}%"),
            )
        )
    rows = ctx.db.scalars(
        stmt.order_by(Programme.code).limit(clamp(args.get("limit"), 25))
    ).unique().all()
    return {
        "count": len(rows),
        "programmes": [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "duration_years": r.duration_years,
                "department": department_brief(r.department),
            }
            for r in rows
        ],
    }


def search_people(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(User).options(
        joinedload(User.staff_profile).joinedload(StaffProfile.department),
        joinedload(User.student_profile).joinedload(StudentProfile.programme),
    )

    if not is_privileged(ctx.user):
        stmt = stmt.where(User.role.in_([to_db_role(r) for r in TEACHING_ROLES]))

    if args.get("role"):
        stmt = stmt.where(User.role == to_db_role(args["role"]))
    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
    if args.get("department"):
        stmt = stmt.join(User.staff_profile).join(StaffProfile.department).where(
            or_(
                Department.name.ilike(f"%{args['department']}%"),
                Department.code.ilike(f"%{args['department']}%"),
            )
        )

    rows = ctx.db.scalars(
        stmt.order_by(User.name).limit(clamp(args.get("limit"), 20))
    ).unique().all()

    people = []
    for row in rows:
        entry = person_brief(row)
        if row.staff_profile is not None:
            entry["position"] = row.staff_profile.position
            entry["specialization"] = row.staff_profile.specialization
            entry["department"] = department_brief(row.staff_profile.department)
        if row.student_profile is not None and is_privileged(ctx.user):
            entry["student_number"] = row.student_profile.student_number
            entry["year_of_study"] = row.student_profile.year_of_study
        people.append(entry)

    return {"count": len(people), "people": people}


def list_rooms(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Room).options(joinedload(Room.building))
    if args.get("query"):
        pattern = f"%{args['query']}%"
        stmt = stmt.where(or_(Room.code.ilike(pattern), Room.name.ilike(pattern)))
    if args.get("building"):
        stmt = stmt.join(Room.building).where(
            or_(
                Building.name.ilike(f"%{args['building']}%"),
                Building.code.ilike(f"%{args['building']}%"),
            )
        )
    if args.get("room_type"):
        stmt = stmt.where(Room.room_type == args["room_type"])
    if args.get("min_capacity"):
        stmt = stmt.where(Room.capacity >= int(args["min_capacity"]))

    rows = ctx.db.scalars(
        stmt.order_by(Room.code).limit(clamp(args.get("limit"), 25))
    ).unique().all()
    return {"count": len(rows), "rooms": [room_brief(r) for r in rows]}


def find_free_rooms(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    starts = parse_time(args["starts_at"], "starts_at")
    ends = parse_time(args["ends_at"], "ends_at")
    if ends <= starts:
        raise ToolError("ends_at must be after starts_at")

    busy = select(Schedule.room_id).where(
        Schedule.status.in_(("scheduled", "rescheduled")),
        Schedule.starts_at < ends,
        Schedule.ends_at > starts,
    )

    stmt = select(Room).options(joinedload(Room.building)).where(Room.id.not_in(busy))
    if args.get("min_capacity"):
        stmt = stmt.where(Room.capacity >= int(args["min_capacity"]))
    if args.get("room_type"):
        stmt = stmt.where(Room.room_type == args["room_type"])
    if args.get("building"):
        stmt = stmt.join(Room.building).where(
            or_(
                Building.name.ilike(f"%{args['building']}%"),
                Building.code.ilike(f"%{args['building']}%"),
            )
        )

    rows = ctx.db.scalars(
        stmt.order_by(Room.capacity).limit(clamp(args.get("limit"), 15))
    ).unique().all()
    return {
        "window": {"starts_at": iso(starts), "ends_at": iso(ends)},
        "count": len(rows),
        "rooms": [room_brief(r) for r in rows],
    }


def list_my_notifications(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Notification).where(Notification.user_id == ctx.user.id)
    if args.get("unread_only"):
        stmt = stmt.where(Notification.read_at.is_(None))

    rows = ctx.db.scalars(
        stmt.order_by(Notification.created_at.desc()).limit(clamp(args.get("limit"), 15))
    ).all()
    return {
        "count": len(rows),
        "notifications": [
            {
                "id": r.id,
                "type": r.type,
                "title": r.title,
                "body": r.body,
                "created_at": iso(r.created_at),
                "read": r.read_at is not None,
            }
            for r in rows
        ],
    }


def join_class_by_invite_code(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if role_of(ctx.user) != "student":
        raise ToolError("Only students can join a class with an invite code")

    code = str(args["invite_code"]).strip().upper()
    row = ctx.db.scalars(
        select(Class).where(Class.invite_code == code).limit(1)
    ).one_or_none()
    if row is None:
        raise ToolError("That invite code does not match any class")
    if row.status != "active":
        raise ToolError("That class is archived and cannot accept new students")

    pending = require_confirmation(args, f"Enroll you in {row.name} ({row.subject.code})")
    if pending:
        return pending

    try:
        assert_not_enrolled(ctx.db, ctx.user.id, row.id)
        assert_capacity(ctx.db, row)
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from exc

    enrollment = Enrollment(student_id=ctx.user.id, class_id=row.id)
    ctx.db.add(enrollment)
    ctx.db.flush()

    recipients = {row.lecturer_id}
    if row.tutor_id is not None:
        recipients.add(row.tutor_id)
    fan_out(
        ctx.db,
        recipients,
        "enrollment",
        f"{ctx.user.name} joined {row.name}",
        "Enrolled through the assistant with an invite code",
    )
    ctx.mutations.append(
        {"action": "enrollment.created", "resource": "enrollments", "id": enrollment.id}
    )
    return {
        "status": "enrolled",
        "enrollment_id": enrollment.id,
        "class": class_brief(row),
    }


def enroll_student(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    row = ctx.db.get(Class, int(args["class_id"]))
    if row is None:
        raise ToolError("No class with that id")
    if not may_touch_class(ctx, row):
        raise ToolError("You can only enroll students into classes you teach or administer")

    student = ctx.db.get(User, int(args["student_id"]))
    if student is None:
        raise ToolError("No user with that id")
    if role_of(student) != "student":
        raise ToolError(f"{student.name} is not a student")

    pending = require_confirmation(args, f"Enroll {student.name} in {row.name}")
    if pending:
        return pending

    try:
        assert_not_enrolled(ctx.db, student.id, row.id)
        assert_capacity(ctx.db, row)
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from exc

    enrollment = Enrollment(student_id=student.id, class_id=row.id)
    ctx.db.add(enrollment)
    ctx.db.flush()
    fan_out(
        ctx.db,
        {student.id},
        "enrollment",
        f"You have been enrolled in {row.name}",
        f"Added by {ctx.user.name}",
    )
    ctx.mutations.append(
        {"action": "enrollment.created", "resource": "enrollments", "id": enrollment.id}
    )
    return {
        "status": "enrolled",
        "enrollment_id": enrollment.id,
        "student": person_brief(student),
        "class": class_brief(row),
    }


def remove_enrollment(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    row = ctx.db.get(Enrollment, int(args["enrollment_id"]))
    if row is None:
        raise ToolError("No enrollment with that id")

    class_row = ctx.db.get(Class, row.class_id)
    if not (row.student_id == ctx.user.id or (class_row and may_touch_class(ctx, class_row))):
        raise ToolError("You do not have permission to remove that enrollment")

    pending = require_confirmation(
        args,
        f"Remove {row.student.name} from {class_row.name if class_row else 'the class'}",
    )
    if pending:
        return pending

    ctx.db.delete(row)
    ctx.db.flush()
    ctx.mutations.append(
        {"action": "enrollment.deleted", "resource": "enrollments", "id": int(args["enrollment_id"])}
    )
    return {"status": "removed", "enrollment_id": int(args["enrollment_id"])}


def create_class(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if not (is_privileged(ctx.user) or role_of(ctx.user) == "lecturer"):
        raise ToolError("You do not have permission to create classes")

    subject = ctx.db.get(Subject, int(args["subject_id"]))
    if subject is None:
        raise ToolError("No subject with that id")

    lecturer_id = int(args.get("lecturer_id") or ctx.user.id)
    lecturer = ctx.db.get(User, lecturer_id)
    if lecturer is None or role_of(lecturer) != "lecturer":
        raise ToolError("lecturer_id must point at a user with the lecturer role")
    if not is_privileged(ctx.user) and lecturer_id != ctx.user.id:
        raise ToolError("Lecturers can only create classes they teach themselves")

    tutor_id = args.get("tutor_id")
    if tutor_id is not None:
        tutor = ctx.db.get(User, int(tutor_id))
        if tutor is None or role_of(tutor) not in ("tutor", "lecturer"):
            raise ToolError("tutor_id must point at a tutor or lecturer")
        tutor_id = int(tutor_id)

    capacity = int(args.get("capacity") or 30)
    pending = require_confirmation(
        args,
        f"Create class '{args['name']}' for {subject.code} with {capacity} seats",
    )
    if pending:
        return pending

    row = Class(
        subject_id=subject.id,
        lecturer_id=lecturer_id,
        tutor_id=tutor_id,
        name=str(args["name"]),
        description=args.get("description"),
        capacity=capacity,
        status="active",
        invite_code=generate_invite_code(ctx.db),
    )
    ctx.db.add(row)
    try:
        ctx.db.flush()
    except IntegrityError as exc:
        ctx.db.rollback()
        raise ToolError("That class could not be created") from exc

    ctx.mutations.append({"action": "class.created", "resource": "classes", "id": row.id})
    return {"status": "created", "class": class_brief(row)}


def update_class(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    row = ctx.db.get(Class, int(args["class_id"]))
    if row is None:
        raise ToolError("No class with that id")
    if not may_touch_class(ctx, row):
        raise ToolError("You do not have permission to edit that class")

    changes: dict[str, Any] = {}
    for key in ("name", "description", "status"):
        if args.get(key) is not None:
            changes[key] = args[key]
    if args.get("capacity") is not None:
        capacity = int(args["capacity"])
        enrolled = ctx.db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.class_id == row.id)
        ) or 0
        if capacity < enrolled:
            raise ToolError(
                f"Capacity cannot drop below the {enrolled} students already enrolled"
            )
        changes["capacity"] = capacity

    if not changes:
        raise ToolError("Nothing to update")

    pending = require_confirmation(
        args, f"Update {row.name}: " + ", ".join(f"{k} to {v}" for k, v in changes.items())
    )
    if pending:
        return pending

    for key, value in changes.items():
        setattr(row, key, value)
    ctx.db.flush()
    ctx.mutations.append({"action": "class.updated", "resource": "classes", "id": row.id})
    return {"status": "updated", "class": class_brief(row), "changed": list(changes)}


def create_schedule(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    class_row = ctx.db.get(Class, int(args["class_id"]))
    if class_row is None:
        raise ToolError("No class with that id")
    if not may_touch_class(ctx, class_row):
        raise ToolError("You do not have permission to schedule that class")

    starts = parse_time(args["starts_at"], "starts_at")
    ends = parse_time(args["ends_at"], "ends_at")
    if ends <= starts:
        raise ToolError("ends_at must be after starts_at")

    room_id = int(args["room_id"])
    lecturer_id = int(args.get("lecturer_id") or class_row.lecturer_id)
    tutor_id = args.get("tutor_id", class_row.tutor_id)
    tutor_id = int(tutor_id) if tutor_id is not None else None

    try:
        validate_targets(ctx.db, class_row.id, room_id, lecturer_id, tutor_id)
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from exc

    conflicts = find_conflicts(ctx.db, room_id, lecturer_id, tutor_id, starts, ends)
    if conflicts:
        return {
            "status": "conflict",
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
            "instruction": "Report these clashes to the user and offer a different slot or room.",
        }

    pending = require_confirmation(
        args, f"Schedule {class_row.name} from {iso(starts)} to {iso(ends)}"
    )
    if pending:
        return pending

    row = Schedule(
        class_id=class_row.id,
        room_id=room_id,
        lecturer_id=lecturer_id,
        tutor_id=tutor_id,
        starts_at=starts,
        ends_at=ends,
        notes=args.get("notes"),
    )
    ctx.db.add(row)
    try:
        ctx.db.flush()
    except IntegrityError as exc:
        ctx.db.rollback()
        raise ToolError(
            "The database rejected that slot because it overlaps an existing booking"
        ) from exc

    notify_schedule_change(
        ctx.db,
        row,
        "schedule_created",
        f"New session for {class_row.name}",
        f"{iso(starts)} to {iso(ends)}",
        actor_id=ctx.user.id,
    )
    ctx.mutations.append(
        {"action": "schedule.created", "resource": "schedules", "id": row.id}
    )
    return {"status": "created", "session": schedule_brief(row)}


def update_schedule(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    row = ctx.db.get(Schedule, int(args["schedule_id"]))
    if row is None:
        raise ToolError("No session with that id")

    class_row = ctx.db.get(Class, row.class_id)
    if class_row is None or not may_touch_class(ctx, class_row):
        raise ToolError("You do not have permission to edit that session")

    starts = parse_time(args["starts_at"], "starts_at") if args.get("starts_at") else row.starts_at
    ends = parse_time(args["ends_at"], "ends_at") if args.get("ends_at") else row.ends_at
    room_id = int(args["room_id"]) if args.get("room_id") else row.room_id
    new_status = args.get("status", row.status)

    if ends <= starts:
        raise ToolError("ends_at must be after starts_at")

    if new_status in ("scheduled", "rescheduled"):
        conflicts = find_conflicts(
            ctx.db, room_id, row.lecturer_id, row.tutor_id, starts, ends, exclude_id=row.id
        )
        if conflicts:
            return {
                "status": "conflict",
                "conflicts": [c.model_dump(mode="json") for c in conflicts],
                "instruction": "Report these clashes to the user and offer a different slot or room.",
            }

    pending = require_confirmation(
        args, f"Move {class_row.name} to {iso(starts)} - {iso(ends)}"
    )
    if pending:
        return pending

    time_changed = starts != row.starts_at or ends != row.ends_at
    row.starts_at = starts
    row.ends_at = ends
    row.room_id = room_id
    if args.get("notes") is not None:
        row.notes = args["notes"]
    row.status = "rescheduled" if time_changed and new_status == "scheduled" else new_status

    try:
        ctx.db.flush()
    except IntegrityError as exc:
        ctx.db.rollback()
        raise ToolError(
            "The database rejected that slot because it overlaps an existing booking"
        ) from exc

    notify_schedule_change(
        ctx.db,
        row,
        "schedule_updated",
        f"Session updated for {class_row.name}",
        f"{iso(starts)} to {iso(ends)}",
        actor_id=ctx.user.id,
    )
    ctx.mutations.append(
        {"action": "schedule.updated", "resource": "schedules", "id": row.id}
    )
    return {"status": "updated", "session": schedule_brief(row)}


def cancel_schedule(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    row = ctx.db.get(Schedule, int(args["schedule_id"]))
    if row is None:
        raise ToolError("No session with that id")

    class_row = ctx.db.get(Class, row.class_id)
    if class_row is None or not may_touch_class(ctx, class_row):
        raise ToolError("You do not have permission to cancel that session")

    pending = require_confirmation(
        args, f"Cancel {class_row.name} on {iso(row.starts_at)}"
    )
    if pending:
        return pending

    row.status = "cancelled"
    ctx.db.flush()
    notify_schedule_change(
        ctx.db,
        row,
        "schedule_cancelled",
        f"Session cancelled for {class_row.name}",
        args.get("reason") or f"The session on {iso(row.starts_at)} has been cancelled",
        actor_id=ctx.user.id,
    )
    ctx.mutations.append(
        {"action": "schedule.cancelled", "resource": "schedules", "id": row.id}
    )
    return {"status": "cancelled", "session": schedule_brief(row)}


def mark_notifications_read(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    stmt = select(Notification).where(
        Notification.user_id == ctx.user.id, Notification.read_at.is_(None)
    )
    ids = args.get("notification_ids")
    if ids:
        stmt = stmt.where(Notification.id.in_([int(i) for i in ids]))
    elif not args.get("all"):
        raise ToolError("Provide notification_ids or set all to true")

    rows = ctx.db.scalars(stmt).all()
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    ctx.db.flush()
    ctx.mutations.append(
        {"action": "notifications.read", "resource": "notifications", "id": None}
    )
    return {"status": "updated", "marked_read": len(rows)}


def create_subject(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if not is_privileged(ctx.user):
        raise ToolError("Only admin and technical services accounts can create subjects")

    department = ctx.db.get(Department, int(args["department_id"]))
    if department is None:
        raise ToolError("No department with that id")

    pending = require_confirmation(
        args, f"Create subject {args['code']} - {args['name']} in {department.name}"
    )
    if pending:
        return pending

    row = Subject(
        department_id=department.id,
        code=str(args["code"]).strip(),
        name=str(args["name"]).strip(),
        description=args.get("description"),
    )
    ctx.db.add(row)
    try:
        ctx.db.flush()
    except IntegrityError as exc:
        ctx.db.rollback()
        raise ToolError("A subject with that code already exists") from exc

    ctx.mutations.append({"action": "subject.created", "resource": "subjects", "id": row.id})
    return {"status": "created", "subject": subject_brief(row)}


def update_my_profile(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "full_name": "name",
        "phone_number": "phone",
        "address": "address",
        "emergency_contact_name": "emergency_contact_name",
        "emergency_contact_phone": "emergency_contact_phone",
    }
    changes = {column: args[key] for key, column in fields.items() if args.get(key) is not None}
    if not changes:
        raise ToolError("Nothing to update")

    pending = require_confirmation(
        args, "Update your profile: " + ", ".join(changes.keys())
    )
    if pending:
        return pending

    for column, value in changes.items():
        setattr(ctx.user, column, value)
    ctx.db.flush()
    ctx.mutations.append({"action": "user.updated", "resource": "users", "id": ctx.user.id})
    return {"status": "updated", "changed": list(changes)}


READ_TOOLS: dict[str, Callable[[ToolContext, dict[str, Any]], dict[str, Any]]] = {
    "get_my_profile": get_my_profile,
    "get_dashboard_overview": get_dashboard_overview,
    "list_my_classes": list_my_classes,
    "list_my_schedule": list_my_schedule,
    "get_class": get_class,
    "list_class_roster": list_class_roster,
    "search_classes": search_classes,
    "search_subjects": search_subjects,
    "list_departments": list_departments,
    "list_programmes": list_programmes,
    "search_people": search_people,
    "list_rooms": list_rooms,
    "find_free_rooms": find_free_rooms,
    "list_my_notifications": list_my_notifications,
}

WRITE_TOOLS: dict[str, Callable[[ToolContext, dict[str, Any]], dict[str, Any]]] = {
    "join_class_by_invite_code": join_class_by_invite_code,
    "enroll_student": enroll_student,
    "remove_enrollment": remove_enrollment,
    "create_class": create_class,
    "update_class": update_class,
    "create_schedule": create_schedule,
    "update_schedule": update_schedule,
    "cancel_schedule": cancel_schedule,
    "mark_notifications_read": mark_notifications_read,
    "create_subject": create_subject,
    "update_my_profile": update_my_profile,
}

HANDLERS = {**READ_TOOLS, **WRITE_TOOLS}


def run_tool(name: str, args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        result = handler(ctx, args or {})
    except ToolError as exc:
        return {"error": str(exc)}
    except HTTPException as exc:
        return {"error": str(exc.detail)}
    except (KeyError, TypeError, ValueError) as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}

    if name in READ_TOOLS:
        ctx.reads.append(name)
    return result
