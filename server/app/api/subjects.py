from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import AdminUser
from app.db.session import get_db
from app.models import Department, Subject
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.subject import SubjectCreate, SubjectOut, SubjectUpdate

router = APIRouter()

LOAD = [joinedload(Subject.department)]


@router.get("", response_model=ListResponse[SubjectOut])
def list_subjects(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
):
    stmt = select(Subject)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Subject.name.ilike(pattern), Subject.code.ilike(pattern)))
    if department:
        stmt = stmt.join(Subject.department).where(
            or_(Department.name.ilike(department), Department.code.ilike(department))
        )

    rows, pagination = paginate(db, stmt.order_by(Subject.id), page, limit, LOAD)
    return envelope([SubjectOut.model_validate(r) for r in rows], pagination)


@router.get("/{subject_id}", response_model=SingleResponse[SubjectOut])
def get_subject(subject_id: int, db: Annotated[Session, Depends(get_db)]):
    row = db.get(Subject, subject_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return SingleResponse[SubjectOut](data=SubjectOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[SubjectOut], status_code=status.HTTP_201_CREATED
)
def create_subject(
    payload: SubjectCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found")

    row = Subject(**payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="A subject with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[SubjectOut](data=SubjectOut.model_validate(row))


@router.patch("/{subject_id}", response_model=SingleResponse[SubjectOut])
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Subject, subject_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subject not found")

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
            status_code=409, detail="A subject with this code already exists"
        ) from exc
    db.refresh(row)
    return SingleResponse[SubjectOut](data=SubjectOut.model_validate(row))


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: AdminUser,
):
    row = db.get(Subject, subject_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This subject still has classes attached"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
