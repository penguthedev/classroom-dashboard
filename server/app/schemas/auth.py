import re
from datetime import date

from fastapi import UploadFile
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.enums import AcademicPosition, TechnicalSpecialization
from app.schemas.user import UserOut

PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RegisterCommon(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    email: EmailStr
    phone_number: str = Field(min_length=6, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    address: str | None = Field(default=None, max_length=2000)
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    profile_picture: UploadFile | None = None

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("Password must be at least 8 characters and contain a letter and a number")
        return value

    @model_validator(mode="after")
    def check_password_match(self) -> "RegisterCommon":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class StudentRegisterRequest(RegisterCommon):
    date_of_birth: date
    id_code: str | None = Field(default=None, min_length=2, max_length=50)
    programme: str | None = Field(default=None, max_length=255)
    programme_id: int | None = Field(default=None, gt=0)
    year_of_study: int = Field(ge=1, le=8)

    @model_validator(mode="after")
    def check_programme(self) -> "StudentRegisterRequest":
        if self.programme_id is None and not (self.programme or "").strip():
            raise ValueError("Select a programme")
        return self
    proof_of_enrollment: UploadFile | None = None
    transcript: UploadFile | None = None


class LecturerRegisterRequest(RegisterCommon):
    id_code: str | None = Field(default=None, min_length=2, max_length=50)
    date_of_birth: date
    faculty: str | None = Field(default=None, max_length=255)
    faculty_id: int | None = Field(default=None, gt=0)
    department_id: int = Field(gt=0)
    academic_position: AcademicPosition
    specialization: str = Field(min_length=1, max_length=255)
    qualification: str = Field(min_length=1, max_length=255)
    qualification_document: UploadFile | None = None


class TutorRegisterRequest(RegisterCommon):
    id_code: str | None = Field(default=None, min_length=2, max_length=50)
    date_of_birth: date
    faculty: str | None = Field(default=None, max_length=255)
    faculty_id: int | None = Field(default=None, gt=0)
    department_id: int = Field(gt=0)
    subject_specialization: str = Field(min_length=1, max_length=255)
    qualification: str = Field(min_length=1, max_length=255)
    qualification_document: UploadFile | None = None


class AdminRegisterRequest(RegisterCommon):
    id_code: str | None = Field(default=None, min_length=2, max_length=50)
    department_id: int = Field(gt=0)
    position: str = Field(min_length=1, max_length=100)
    staff_verification_document: UploadFile | None = None


class TechnicalRegisterRequest(RegisterCommon):
    id_code: str | None = Field(default=None, min_length=2, max_length=50)
    department_id: int = Field(gt=0)
    technical_position: str = Field(min_length=1, max_length=100)
    technical_specialization: TechnicalSpecialization
    qualification: str = Field(min_length=1, max_length=255)
    certification_document: UploadFile | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("Password must be at least 8 characters and contain a letter and a number")
        return value

    @model_validator(mode="after")
    def check_password_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class MessageResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("Password must be at least 8 characters and contain a letter and a number")
        return value

    @model_validator(mode="after")
    def check_password_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if self.new_password == self.current_password:
            raise ValueError("The new password must be different from the current one")
        return self


class AuthPayload(BaseModel):
    user: UserOut
    access_token: str | None = None
    token_type: str = "bearer"
    # True when the account was just created but still needs an admin to
    # approve it before it can sign in (see app/api/auth.py::finalize).
    pending_approval: bool = False


class LockoutDetail(BaseModel):
    message: str
    retry_after: int
    retry_after_seconds: int
