from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.refs import ORMModel, SubjectRef, UserRef


class EnrollmentClassRef(ORMModel):
    id: int
    name: str
    invite_code: str
    subject: SubjectRef


class EnrollmentOut(ORMModel):
    id: int
    student_id: int
    class_id: int
    enrolled_at: datetime
    student: UserRef
    class_: EnrollmentClassRef = Field(serialization_alias="class")


class EnrollmentCreate(BaseModel):
    student_id: int
    class_id: int


class EnrollmentJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=50)
