from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FacultyRef(ORMModel):
    id: int
    code: str
    name: str


class DepartmentRef(ORMModel):
    id: int
    code: str
    name: str


class ProgrammeRef(ORMModel):
    id: int
    code: str
    name: str


class SubjectRef(ORMModel):
    id: int
    code: str
    name: str
    description: str | None = None


class UserRef(ORMModel):
    id: int
    name: str
    email: str
    role: str
    image_url: str | None = None


class BuildingRef(ORMModel):
    id: int
    code: str
    name: str
