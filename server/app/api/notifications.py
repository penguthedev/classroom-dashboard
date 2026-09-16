from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged
from app.db.session import get_db
from app.models import Class, Enrollment, Notification, Schedule
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.notification import NotificationCreate, NotificationOut

router = APIRouter()


def recipients_for_class(db: Session, class_row: Class) -> set[int]:
    student_ids = set(
        db.scalars(
            select(Enrollment.student_id).where(Enrollment.class_id == class_row.id)
        ).all()
    )
    student_ids.add(class_row.lecturer_id)
    if class_row.tutor_id is not None:
        student_ids.add(class_row.tutor_id)
    return student_ids


def fan_out(
    db: Session,
    user_ids: set[int],
    notification_type: str,
    title: str,
    body: str | None = None,
    schedule_id: int | None = None,
    exclude: int | None = None,
) -> None:
    for user_id in user_ids:
        if exclude is not None and user_id == exclude:
            continue
        db.add(
            Notification(
                user_id=user_id,
                schedule_id=schedule_id,
                type=notification_type,
                title=title,
                body=body,
            )
        )


def notify_schedule_change(
    db: Session,
    schedule: Schedule,
    notification_type: str,
    title: str,
    body: str | None = None,
    actor_id: int | None = None,
) -> None:
    class_row = db.get(Class, schedule.class_id)
    if class_row is None:
        return
    fan_out(
        db,
        recipients_for_class(db, class_row),
        notification_type,
        title,
        body,
        schedule_id=schedule.id,
        exclude=actor_id,
    )


@router.get("", response_model=ListResponse[NotificationOut])
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread: bool = False,
    notification_type: str | None = Query(None, alias="type"),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread:
        stmt = stmt.where(Notification.read_at.is_(None))
    if notification_type:
        stmt = stmt.where(Notification.type == notification_type)

    rows, pagination = paginate(
        db, stmt.order_by(Notification.created_at.desc(), Notification.id.desc()), page, limit
    )
    return envelope([NotificationOut.model_validate(r) for r in rows], pagination)


@router.get("/unread-count")
def unread_count(db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    rows = db.scalars(
        select(Notification.id).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    return {"data": {"unread": len(rows)}}


@router.get("/{notification_id}", response_model=SingleResponse[NotificationOut])
def get_notification(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return SingleResponse[NotificationOut](data=NotificationOut.model_validate(row))


@router.post(
    "",
    response_model=SingleResponse[NotificationOut],
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    payload: NotificationCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not is_privileged(current_user):
        raise HTTPException(
            status_code=403, detail="You do not have permission to send notifications"
        )
    row = Notification(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return SingleResponse[NotificationOut](data=NotificationOut.model_validate(row))


@router.patch("/{notification_id}", response_model=SingleResponse[NotificationOut])
def mark_read(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    read: bool = True,
):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    row.read_at = datetime.now(UTC) if read else None
    db.commit()
    db.refresh(row)
    return SingleResponse[NotificationOut](data=NotificationOut.model_validate(row))


@router.post("/read-all")
def mark_all_read(db: Annotated[Session, Depends(get_db)], current_user: CurrentUser):
    rows = db.scalars(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    db.commit()
    return {"data": {"updated": len(rows)}}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
