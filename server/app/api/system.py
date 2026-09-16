import platform
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import AdminUser
from app.core.config import settings
from app.core.storage import get_client
from app.db.session import engine, get_db
from app.models import Document, Notification, Schedule, User
from app.schemas.common import SingleResponse
from app.schemas.system import (
    ActivityInfo,
    ComponentStatus,
    DatabaseInfo,
    StorageInfo,
    SystemStatusOut,
)

router = APIRouter()

STARTED_AT = time.monotonic()

API_VERSION = "0.2.0"


def check_database(db: Session) -> tuple[ComponentStatus, DatabaseInfo]:
    started = time.perf_counter()
    server_version: str | None = None
    revision: str | None = None

    try:
        db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - started) * 1000
        component = ComponentStatus(
            name="database",
            status="ok",
            detail="Accepting queries",
            latency_ms=round(latency, 2),
        )
    except SQLAlchemyError as exc:
        component = ComponentStatus(
            name="database",
            status="down",
            detail=str(exc.__class__.__name__),
            latency_ms=None,
        )
        return component, DatabaseInfo(dialect=engine.dialect.name)

    try:
        server_version = str(db.execute(text("SELECT version()")).scalar_one())
    except SQLAlchemyError:
        server_version = None

    try:
        revision = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
    except SQLAlchemyError:
        revision = None

    pool = getattr(engine, "pool", None)
    info = DatabaseInfo(
        dialect=engine.dialect.name,
        server_version=server_version,
        migration_revision=revision,
        pool_size=pool.size() if hasattr(pool, "size") else None,
        checked_out=pool.checkedout() if hasattr(pool, "checkedout") else None,
    )
    return component, info


def check_storage() -> tuple[ComponentStatus, StorageInfo]:
    info = StorageInfo(
        configured=settings.storage_enabled,
        endpoint=settings.S3_ENDPOINT or None,
        bucket=settings.S3_BUCKET or None,
        public_url=settings.S3_PUBLIC_URL or None,
    )

    if not settings.storage_enabled:
        return (
            ComponentStatus(
                name="storage",
                status="disabled",
                detail="No S3 endpoint or bucket configured",
            ),
            info,
        )

    started = time.perf_counter()
    try:
        get_client().head_bucket(Bucket=settings.S3_BUCKET)
        latency = (time.perf_counter() - started) * 1000
        return (
            ComponentStatus(
                name="storage",
                status="ok",
                detail=f"Bucket {settings.S3_BUCKET} reachable",
                latency_ms=round(latency, 2),
            ),
            info,
        )
    except Exception as exc:
        return (
            ComponentStatus(
                name="storage",
                status="down",
                detail=exc.__class__.__name__,
            ),
            info,
        )


def check_assistant() -> ComponentStatus:
    if not settings.assistant_enabled:
        return ComponentStatus(
            name="assistant",
            status="disabled",
            detail="No GEMINI_API_KEY configured",
        )
    return ComponentStatus(
        name="assistant",
        status="ok",
        detail=f"Model {settings.GEMINI_MODEL}",
    )


def check_mail() -> ComponentStatus:
    if not settings.mail_enabled:
        return ComponentStatus(
            name="mail",
            status="disabled",
            detail="No SMTP host configured, reset links are logged instead",
        )
    return ComponentStatus(
        name="mail",
        status="ok",
        detail=f"Relaying through {settings.SMTP_HOST}",
    )


def count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def gather_activity(db: Session) -> ActivityInfo:
    now = datetime.now(UTC)
    horizon = now + timedelta(days=7)

    return ActivityInfo(
        users_total=count(db, select(func.count()).select_from(User)),
        users_active=count(
            db, select(func.count()).select_from(User).where(User.is_active.is_(True))
        ),
        users_locked=count(
            db,
            select(func.count())
            .select_from(User)
            .where(User.locked_until.is_not(None))
            .where(User.locked_until > now),
        ),
        failed_logins_pending=count(
            db,
            select(func.coalesce(func.sum(User.failed_login_attempts), 0)).select_from(
                User
            ),
        ),
        schedules_upcoming=count(
            db,
            select(func.count())
            .select_from(Schedule)
            .where(Schedule.starts_at >= now)
            .where(Schedule.starts_at <= horizon)
            .where(Schedule.status.in_(("scheduled", "rescheduled"))),
        ),
        notifications_unread=count(
            db,
            select(func.count())
            .select_from(Notification)
            .where(Notification.read_at.is_(None)),
        ),
        documents_stored=count(db, select(func.count()).select_from(Document)),
    )


def overall(components: list[ComponentStatus]) -> str:
    if any(c.status == "down" for c in components):
        return "degraded"
    return "ok"


@router.get("/status", response_model=SingleResponse[SystemStatusOut])
def system_status(
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
):
    database_component, database_info = check_database(db)
    storage_component, storage_info = check_storage()
    components = [
        database_component,
        storage_component,
        check_assistant(),
        check_mail(),
    ]

    activity = (
        gather_activity(db)
        if database_component.status == "ok"
        else ActivityInfo(
            users_total=0,
            users_active=0,
            users_locked=0,
            failed_logins_pending=0,
            schedules_upcoming=0,
            notifications_unread=0,
            documents_stored=0,
        )
    )

    return SingleResponse[SystemStatusOut](
        data=SystemStatusOut(
            status=overall(components),
            checked_at=datetime.now(UTC),
            api_version=API_VERSION,
            python_version=sys.version.split()[0],
            platform=platform.platform(),
            uptime_seconds=round(time.monotonic() - STARTED_AT, 1),
            components=components,
            database=database_info,
            storage=storage_info,
            assistant_enabled=settings.assistant_enabled,
            mail_enabled=settings.mail_enabled,
            activity=activity,
        )
    )
