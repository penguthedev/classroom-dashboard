from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Building
from app.schemas.building import BuildingCreate, BuildingOut, BuildingUpdate
from app.schemas.common import ListResponse, SingleResponse

router = APIRouter()


@router.get("", response_model=ListResponse[BuildingOut])
def list_buildings(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
):
    stmt = select(Building)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Building.name.ilike(pattern), Building.code.ilike(pattern))
        )

    rows, pagination = paginate(db, stmt.order_by(Building.id), page, limit)
    return envelope([BuildingOut.model_validate(r) for r in rows], pagination)


@router.get("/{building_id}", response_model=SingleResponse[BuildingOut])
def get_building(building_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Building, building_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return SingleResponse[BuildingOut](data=BuildingOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[BuildingOut], status_code=status.HTTP_201_CREATED
)
def create_building(
    payload: BuildingCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = Building(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A building with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[BuildingOut](data=BuildingOut.model_validate(row))


@router.patch("/{building_id}", response_model=SingleResponse[BuildingOut])
def update_building(
    building_id: int,
    payload: BuildingUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Building, building_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Building not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A building with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[BuildingOut](data=BuildingOut.model_validate(row))


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_building(
    building_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Building, building_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Building not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This building still has rooms attached"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
