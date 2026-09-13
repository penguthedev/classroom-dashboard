from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.refs import ORMModel


class FacultyOut(ORMModel):
    id: int
    code: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class FacultyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class FacultyUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
