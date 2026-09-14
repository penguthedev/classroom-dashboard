from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import RoomType
from app.schemas.refs import BuildingRef, ORMModel


class BuildingOut(ORMModel):
    id: int
    code: str
    name: str
    address: str | None = None
    created_at: datetime
    updated_at: datetime


class BuildingCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None


class BuildingUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None


class RoomOut(ORMModel):
    id: int
    building_id: int
    code: str
    name: str | None = None
    capacity: int
    room_type: RoomType
    building: BuildingRef
    created_at: datetime
    updated_at: datetime


class RoomCreate(BaseModel):
    building_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    capacity: int = Field(default=30, ge=1, le=2000)
    room_type: RoomType = "lecture_hall"


class RoomUpdate(BaseModel):
    building_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, max_length=255)
    capacity: int | None = Field(default=None, ge=1, le=2000)
    room_type: RoomType | None = None
