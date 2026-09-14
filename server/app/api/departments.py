from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Department, Faculty
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate

router = APIRouter()

LOAD = [joinedload(Department.faculty)]


@router.get("", response_model=ListResponse[DepartmentOut])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    faculty: str | None = None,
):
    stmt = select(Department)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Department.name.ilike(pattern), Department.code.ilike(pattern))
        )
    if faculty:
        stmt = stmt.join(Department.faculty).where(
            or_(Faculty.name.ilike(faculty), Faculty.code.ilike(faculty))
        )

    rows, pagination = paginate(db, stmt.order_by(Department.id), page, limit, LOAD)
    return envelope([DepartmentOut.model_validate(r) for r in rows], pagination)


@router.get("/{department_id}", response_model=SingleResponse[DepartmentOut])
def get_department(department_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Department, department_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return SingleResponse[DepartmentOut](data=DepartmentOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[DepartmentOut], status_code=status.HTTP_201_CREATED
)
def create_department(
    payload: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    if db.get(Faculty, payload.faculty_id) is None:
        raise HTTPException(status_code=404, detail="Faculty not found")

    row = Department(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A department with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[DepartmentOut](data=DepartmentOut.model_validate(row))


@router.patch("/{department_id}", response_model=SingleResponse[DepartmentOut])
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Department, department_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Department not found")

    data = payload.model_dump(exclude_unset=True)
    if "faculty_id" in data and db.get(Faculty, data["faculty_id"]) is None:
        raise HTTPException(status_code=404, detail="Faculty not found")

    for key, value in data.items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A department with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[DepartmentOut](data=DepartmentOut.model_validate(row))


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Department, department_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Department not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This department still has subjects, programmes or staff attached",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
