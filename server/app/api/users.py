from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged, load_user, user_loader_options
from app.db.session import get_db
from app.models import Department, Programme, StaffProfile, StudentProfile, User
from app.schemas.common import SingleResponse
from app.schemas.enums import TEACHING_ROLES, to_api_role, to_db_role
from app.schemas.user import UserUpdate
from app.services.serializers import serialize_user, serialize_user_summary

router = APIRouter()

SELF_EDITABLE = {
    "full_name",
    "phone_number",
    "date_of_birth",
    "address",
    "emergency_contact_name",
    "emergency_contact_phone",
    "profile_picture_url",
}

USER_COLUMN_MAP = {
    "full_name": "name",
    "phone_number": "phone",
    "profile_picture_url": "image_url",
    "date_of_birth": "date_of_birth",
    "address": "address",
    "emergency_contact_name": "emergency_contact_name",
    "emergency_contact_phone": "emergency_contact_phone",
    "is_active": "is_active",
    "is_approved": "is_approved",
}


def visible_scope(viewer: User):
    if is_privileged(viewer):
        return None
    if to_api_role(viewer.role) in TEACHING_ROLES:
        return None
    return [to_db_role(r) for r in TEACHING_ROLES]


@router.get("")
def list_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    department: str | None = None,
    programme: str | None = None,
    is_active: bool | None = None,
    is_approved: bool | None = None,
):
    stmt = select(User)

    allowed_roles = visible_scope(current_user)
    if allowed_roles is not None:
        stmt = stmt.where(User.role.in_(allowed_roles))

    if role:
        stmt = stmt.where(User.role == to_db_role(role))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    if department:
        stmt = (
            stmt.join(User.staff_profile)
            .join(StaffProfile.department)
            .where(
                or_(
                    Department.name.ilike(department),
                    Department.code.ilike(department),
                )
            )
        )
    if programme:
        stmt = (
            stmt.join(User.student_profile)
            .join(StudentProfile.programme)
            .where(
                or_(Programme.name.ilike(programme), Programme.code.ilike(programme))
            )
        )
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if is_approved is not None:
        stmt = stmt.where(User.is_approved.is_(is_approved))

    rows, pagination = paginate(
        db, stmt.order_by(User.id), page, limit, user_loader_options()
    )

    if is_privileged(current_user):
        data = [serialize_user(row) for row in rows]
    else:
        data = [serialize_user_summary(row) for row in rows]

    return envelope(data, pagination)


@router.get("/me")
def get_me(current_user: CurrentUser):
    return SingleResponse(data=serialize_user(current_user))


@router.patch("/me")
def update_me(
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    return update_user(current_user.id, payload, db, current_user)


@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = load_user(db, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.id == row.id or is_privileged(current_user):
        return SingleResponse(data=serialize_user(row))

    allowed_roles = visible_scope(current_user)
    if allowed_roles is not None and row.role not in allowed_roles:
        raise HTTPException(status_code=404, detail="User not found")

    return SingleResponse(data=serialize_user_summary(row))


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = load_user(db, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")

    privileged = is_privileged(current_user)
    if not privileged and current_user.id != row.id:
        raise HTTPException(
            status_code=403, detail="You can only update your own account"
        )

    data = payload.model_dump(exclude_unset=True)
    if not privileged:
        rejected = set(data) - SELF_EDITABLE
        if rejected:
            raise HTTPException(
                status_code=403,
                detail=f"You cannot change: {', '.join(sorted(rejected))}",
            )

    for key, column in USER_COLUMN_MAP.items():
        if key in data:
            setattr(row, column, data[key])

    if privileged and "role" in data:
        row.role = to_db_role(data["role"])

    if privileged:
        apply_profile_updates(db, row, data)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Those details conflict with an existing account"
        ) from exc

    return SingleResponse(data=serialize_user(load_user(db, row.id)))


def apply_profile_updates(db: Session, row: User, data: dict) -> None:
    student = row.student_profile
    staff = row.staff_profile

    if student is not None:
        if "programme_id" in data:
            if data["programme_id"] is not None and db.get(Programme, data["programme_id"]) is None:
                raise HTTPException(status_code=404, detail="Programme not found")
            student.programme_id = data["programme_id"]
        if "year_of_study" in data:
            student.year_of_study = data["year_of_study"]

    if staff is not None:
        if "department_id" in data:
            if data["department_id"] is not None and db.get(Department, data["department_id"]) is None:
                raise HTTPException(status_code=404, detail="Department not found")
            staff.department_id = data["department_id"]
        for key in ("position", "specialization", "qualification"):
            if key in data:
                setattr(staff, key, data[key])


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not is_privileged(current_user):
        raise HTTPException(
            status_code=403, detail="You do not have permission to remove accounts"
        )

    row = db.get(User, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    if row.id == current_user.id:
        raise HTTPException(status_code=409, detail="You cannot remove your own account")

    try:
        db.delete(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        row.is_active = False
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
