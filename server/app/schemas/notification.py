from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import NotificationType
from app.schemas.refs import ORMModel


class NotificationOut(ORMModel):
    id: int
    user_id: int
    schedule_id: int | None = None
    type: NotificationType
    title: str
    body: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    schedule_id: int | None = None
    type: NotificationType = "system"
    title: str = Field(min_length=1, max_length=255)
    body: str | None = None
