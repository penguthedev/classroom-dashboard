from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.department import DepartmentOut


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    department_id: int
    department: DepartmentOut
    created_at: datetime
    updated_at: datetime
