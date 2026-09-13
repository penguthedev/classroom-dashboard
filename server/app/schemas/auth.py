from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.enums import Role
from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    role: Role
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=512)
    image_object_key: str | None = Field(default=None, max_length=512)

    student_number: str | None = Field(default=None, max_length=50)
    programme_id: int | None = None
    year_of_study: int | None = Field(default=None, ge=1, le=10)

    staff_number: str | None = Field(default=None, max_length=50)
    department_id: int | None = None
    position: str | None = Field(default=None, max_length=100)
    specialization: str | None = Field(default=None, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def check_role_fields(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match")
        if self.role == "student":
            if not self.student_number:
                raise ValueError("student_number is required for role student")
            if self.programme_id is None:
                raise ValueError("programme_id is required for role student")
        else:
            if not self.staff_number:
                raise ValueError(f"staff_number is required for role {self.role}")
        return self


class AuthPayload(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


class LockoutDetail(BaseModel):
    message: str
    retry_after: int
