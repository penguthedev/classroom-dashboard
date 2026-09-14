from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.building import RoomOut
from app.schemas.enums import ScheduleStatus
from app.schemas.refs import ORMModel, SubjectRef, UserRef


class ScheduleClassRef(ORMModel):
    id: int
    name: str
    subject: SubjectRef


class ScheduleOut(ORMModel):
    id: int
    class_id: int
    room_id: int
    lecturer_id: int
    tutor_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    status: ScheduleStatus
    notes: str | None = None
    class_: ScheduleClassRef = Field(serialization_alias="class")
    room: RoomOut
    lecturer: UserRef
    tutor: UserRef | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleCreate(BaseModel):
    class_id: int
    room_id: int
    lecturer_id: int
    tutor_id: int | None = None
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def check_time_order(self) -> "ScheduleCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ScheduleUpdate(BaseModel):
    class_id: int | None = None
    room_id: int | None = None
    lecturer_id: int | None = None
    tutor_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: ScheduleStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_time_order(self) -> "ScheduleUpdate":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class ScheduleConflict(BaseModel):
    resource: str
    schedule_id: int
    starts_at: datetime
    ends_at: datetime
    message: str
