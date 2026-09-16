from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.enums import to_api_role


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
    description: str | None = None


class ProgrammeRef(ORMModel):
    id: int
    code: str
    name: str


class SubjectRef(ORMModel):
    id: int
    code: str
    name: str
    description: str | None = None


class BuildingRef(ORMModel):
    id: int
    code: str
    name: str


class UserRef(ORMModel):
    id: int
    name: str = Field(serialization_alias="full_name")
    email: str
    role: str
    image_url: str | None = Field(default=None, serialization_alias="profile_picture_url")

    @field_serializer("role")
    def serialize_role(self, value: str) -> str:
        return to_api_role(value)
