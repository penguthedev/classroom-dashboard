from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser
from app.db.session import get_db
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
    Subject,
    User,
)
from app.schemas.common import SingleResponse
from app.schemas.enums import to_api_role
from app.schemas.stats import OverviewOut, RoleBreakdown

router = APIRouter()


def total(db: Session, stmt: Select) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


@router.get("/overview", response_model=SingleResponse[OverviewOut])
def overview(db: Annotated[Session, Depends(get_db)], current_user: AdminUser):
    now = datetime.now(UTC)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)

    role_rows = db.execute(select(User.role, func.count()).group_by(User.role)).all()
    breakdown = RoleBreakdown()
    for role, count in role_rows:
        setattr(breakdown, to_api_role(role), count)

    unread = total(
        db,
        select(Notification.id).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        ),
    )

    data = OverviewOut(
        faculties=total(db, select(Faculty.id)),
        departments=total(db, select(Department.id)),
        programmes=total(db, select(Programme.id)),
        subjects=total(db, select(Subject.id)),
        classes=total(db, select(Class.id)),
        active_classes=total(db, select(Class.id).where(Class.status == "active")),
        users=total(db, select(User.id)),
        enrollments=total(db, select(Enrollment.id)),
        buildings=total(db, select(Building.id)),
        rooms=total(db, select(Room.id)),
        schedules_this_week=total(
            db,
            select(Schedule.id).where(
                Schedule.starts_at >= week_start, Schedule.starts_at < week_end
            ),
        ),
        unread_notifications=unread,
        users_by_role=breakdown,
    )
    return SingleResponse[OverviewOut](data=data)
