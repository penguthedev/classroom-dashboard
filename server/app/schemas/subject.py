from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.refs import DepartmentRef, ORMModel


class SubjectOut(ORMModel):
    id: int
    department_id: int
    code: str
    name: str
    description: str | None = None
    department: DepartmentRef
    created_at: datetime
    updated_at: datetime


class SubjectCreate(BaseModel):
    department_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class SubjectUpdate(BaseModel):
    department_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
