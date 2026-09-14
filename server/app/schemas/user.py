from datetime import date, datetime
from typing import Any

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


class UserOut(BaseModel):
    id: int
    id_code: str | None = None
    role: Role
    full_name: str
    username: str
    email: EmailStr
    phone_number: str | None = None
    profile_picture_url: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    date_of_birth: date | None = None
    is_active: bool
    created_at: datetime
    profile: dict[str, Any] | None = None


class UserSummaryOut(BaseModel):
    id: int
    id_code: str | None = None
    role: Role
    full_name: str
    email: EmailStr
    profile_picture_url: str | None = None
    department: DepartmentRef | None = None
    programme: ProgrammeRef | None = None
    year_of_study: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    profile_picture_url: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None
    role: Role | None = None
    department_id: int | None = None
    programme_id: int | None = None
    year_of_study: int | None = Field(default=None, ge=1, le=10)
    position: str | None = Field(default=None, max_length=100)
    specialization: str | None = Field(default=None, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
