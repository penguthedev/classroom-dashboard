from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Faculty
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.faculty import FacultyCreate, FacultyOut, FacultyUpdate

router = APIRouter()


@router.get("", response_model=ListResponse[FacultyOut])
def list_faculties(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
):
    stmt = select(Faculty)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Faculty.name.ilike(pattern), Faculty.code.ilike(pattern)))

    rows, pagination = paginate(db, stmt.order_by(Faculty.id), page, limit)
    return envelope([FacultyOut.model_validate(r) for r in rows], pagination)


@router.get("/{faculty_id}", response_model=SingleResponse[FacultyOut])
def get_faculty(faculty_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Faculty, faculty_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return SingleResponse[FacultyOut](data=FacultyOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[FacultyOut], status_code=status.HTTP_201_CREATED
)
def create_faculty(
    payload: FacultyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = Faculty(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A faculty with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[FacultyOut](data=FacultyOut.model_validate(row))


@router.patch("/{faculty_id}", response_model=SingleResponse[FacultyOut])
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Faculty, faculty_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Faculty not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A faculty with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[FacultyOut](data=FacultyOut.model_validate(row))


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Faculty, faculty_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This faculty still has departments attached"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
