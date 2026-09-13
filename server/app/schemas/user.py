from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.enums import Role
from app.schemas.refs import DepartmentRef, ORMModel, ProgrammeRef


class StudentProfileOut(ORMModel):
    id: int
    user_id: int
    programme_id: int | None = None
    student_number: str
    year_of_study: int
    programme: ProgrammeRef | None = None


class StaffProfileOut(ORMModel):
    id: int
    user_id: int
    department_id: int | None = None
    staff_number: str
    position: str | None = None
    specialization: str | None = None
    qualification: str | None = None
    department: DepartmentRef | None = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    username: str
    name: str
    role: Role
    phone: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    image_url: str | None = None
    image_object_key: str | None = None
    is_active: bool
    student_profile: StudentProfileOut | None = None
    staff_profile: StaffProfileOut | None = None
    created_at: datetime
    updated_at: datetime


class UserSummaryOut(ORMModel):
    id: int
    name: str
    email: EmailStr
    role: Role
    image_url: str | None = None
    student_profile: StudentProfileOut | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=512)
    image_object_key: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None
    role: Role | None = None
