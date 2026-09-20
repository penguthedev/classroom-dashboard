from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.schemas.enums import ClassStatus
from app.schemas.refs import DepartmentRef, ORMModel, UserRef
from app.schemas.subject import SubjectOut


class ClassOut(ORMModel):
    id: int
    subject_id: int
    lecturer_id: int
    tutor_id: int | None = None
    name: str
    description: str | None = None
    capacity: int
    status: ClassStatus
    banner_url: str | None = None
    banner_object_key: str | None = None
    invite_code: str
    subject: SubjectOut
    lecturer: UserRef
    tutor: UserRef | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def department(self) -> DepartmentRef:
        return self.subject.department


class ClassCreate(BaseModel):
    subject_id: int
    lecturer_id: int
    tutor_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    capacity: int = Field(ge=1, le=2000)
    status: ClassStatus = "active"
    banner_url: str | None = Field(default=None, max_length=512)
    banner_object_key: str | None = Field(default=None, max_length=512)


class ClassUpdate(BaseModel):
    subject_id: int | None = None
    lecturer_id: int | None = None
    tutor_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    capacity: int | None = Field(default=None, ge=1, le=2000)
    status: ClassStatus | None = None
    banner_url: str | None = Field(default=None, max_length=512)
    banner_object_key: str | None = Field(default=None, max_length=512)
