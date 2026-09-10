from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Department, Faculty
from app.schemas.common import ListResponse, Pagination, SingleResponse
from app.schemas.department import DepartmentOut

router = APIRouter()


@router.get("", response_model=ListResponse[DepartmentOut])
def list_departments(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    faculty: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Department)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Department.name.ilike(pattern), Department.code.ilike(pattern))
        )
    if faculty:
        stmt = stmt.join(Department.faculty).where(Faculty.name.ilike(faculty))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(joinedload(Department.faculty))
        .order_by(Department.id)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return ListResponse[DepartmentOut](
        data=[DepartmentOut.model_validate(r) for r in rows],
        pagination=Pagination(
            page=page,
            limit=limit,
            total=total,
            totalPages=(total + limit - 1) // limit,
        ),
    )


@router.get("/{department_id}", response_model=SingleResponse[DepartmentOut])
def get_department(department_id: int, db: Session = Depends(get_db)):
    row = db.get(Department, department_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return SingleResponse[DepartmentOut](data=DepartmentOut.model_validate(row))
