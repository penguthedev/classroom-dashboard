from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Department, Programme
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.programme import ProgrammeCreate, ProgrammeOut, ProgrammeUpdate

router = APIRouter()

LOAD = [joinedload(Programme.department)]


@router.get("", response_model=ListResponse[ProgrammeOut])
def list_programmes(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
):
    stmt = select(Programme)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Programme.name.ilike(pattern), Programme.code.ilike(pattern))
        )
    if department:
        stmt = stmt.join(Programme.department).where(
            or_(Department.name.ilike(department), Department.code.ilike(department))
        )

    rows, pagination = paginate(db, stmt.order_by(Programme.id), page, limit, LOAD)
    return envelope([ProgrammeOut.model_validate(r) for r in rows], pagination)


@router.get("/{programme_id}", response_model=SingleResponse[ProgrammeOut])
def get_programme(programme_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Programme, programme_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    return SingleResponse[ProgrammeOut](data=ProgrammeOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[ProgrammeOut], status_code=status.HTTP_201_CREATED
)
def create_programme(
    payload: ProgrammeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found")

    row = Programme(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A programme with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[ProgrammeOut](data=ProgrammeOut.model_validate(row))


@router.patch("/{programme_id}", response_model=SingleResponse[ProgrammeOut])
def update_programme(
    programme_id: int,
    payload: ProgrammeUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Programme, programme_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Programme not found")

    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data and db.get(Department, data["department_id"]) is None:
        raise HTTPException(status_code=404, detail="Department not found")

    for key, value in data.items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A programme with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[ProgrammeOut](data=ProgrammeOut.model_validate(row))


@router.delete("/{programme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_programme(
    programme_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Programme, programme_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Programme not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This programme still has students enrolled"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
