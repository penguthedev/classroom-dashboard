from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.refs import DepartmentRef, ORMModel


class ProgrammeOut(ORMModel):
    id: int
    department_id: int
    code: str
    name: str
    description: str | None = None
    duration_years: int
    department: DepartmentRef
    created_at: datetime
    updated_at: datetime


class ProgrammeCreate(BaseModel):
    department_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    duration_years: int = Field(default=3, ge=1, le=10)


class ProgrammeUpdate(BaseModel):
    department_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration_years: int | None = Field(default=None, ge=1, le=10)
