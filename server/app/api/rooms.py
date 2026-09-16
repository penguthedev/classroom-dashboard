from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Building, Room
from app.schemas.building import RoomCreate, RoomOut, RoomUpdate
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter()

LOAD = [joinedload(Room.building)]


@router.get("", response_model=ListResponse[RoomOut])
def list_rooms(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    building: str | None = None,
    room_type: str | None = None,
    min_capacity: int | None = Query(None, ge=1),
):
    stmt = select(Room)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Room.code.ilike(pattern), Room.name.ilike(pattern)))
    if building:
        stmt = stmt.join(Room.building).where(
            or_(Building.name.ilike(building), Building.code.ilike(building))
        )
    if room_type:
        stmt = stmt.where(Room.room_type == room_type)
    if min_capacity:
        stmt = stmt.where(Room.capacity >= min_capacity)

    rows, pagination = paginate(db, stmt.order_by(Room.id), page, limit, LOAD)
    return envelope([RoomOut.model_validate(r) for r in rows], pagination)


@router.get("/{room_id}", response_model=SingleResponse[RoomOut])
def get_room(room_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Room, room_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return SingleResponse[RoomOut](data=RoomOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[RoomOut], status_code=status.HTTP_201_CREATED
)
def create_room(
    payload: RoomCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    if db.get(Building, payload.building_id) is None:
        raise HTTPException(status_code=404, detail="Building not found")

    row = Room(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A room with this code already exists in that building",
        ) from exc
    db.refresh(row)
    return SingleResponse[RoomOut](data=RoomOut.model_validate(row))


@router.patch("/{room_id}", response_model=SingleResponse[RoomOut])
def update_room(
    room_id: int,
    payload: RoomUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Room, room_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Room not found")

    data = payload.model_dump(exclude_unset=True)
    if "building_id" in data and db.get(Building, data["building_id"]) is None:
        raise HTTPException(status_code=404, detail="Building not found")

    for key, value in data.items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A room with this code already exists in that building",
        ) from exc
    db.refresh(row)
    return SingleResponse[RoomOut](data=RoomOut.model_validate(row))


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Room, room_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Room not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This room still has schedules attached"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
