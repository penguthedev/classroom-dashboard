import secrets
import string
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged
from app.db.session import get_db
from app.models import Class, Department, Enrollment, Subject, User
from app.schemas.class_ import ClassCreate, ClassOut, ClassUpdate
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.enums import to_api_role

router = APIRouter()

INVITE_ALPHABET = string.ascii_uppercase + string.digits

LOAD = [
    joinedload(Class.subject).joinedload(Subject.department),
    joinedload(Class.lecturer),
    joinedload(Class.tutor),
]


def generate_invite_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))
        exists = db.scalars(
            select(Class.id).where(Class.invite_code == code).limit(1)
        ).one_or_none()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate an invite code")


def get_class_or_404(db: Session, class_id: int) -> Class:
    row = db.scalars(
        select(Class).where(Class.id == class_id).options(*LOAD)
    ).unique().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return row


def assert_role(db: Session, user_id: int, allowed: tuple[str, ...], label: str) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    if to_api_role(user.role) not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"User {user.name} is not a {label.lower()}",
        )


def can_manage(current_user: User, row: Class | None = None) -> bool:
    if is_privileged(current_user):
        return True
    if row is None:
        return to_api_role(current_user.role) == "lecturer"
    return current_user.id in (row.lecturer_id, row.tutor_id)


@router.get("", response_model=ListResponse[ClassOut])
def list_classes(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = None,
    subject: str | None = None,
    teacher: str | None = None,
    department: str | None = None,
    class_status: str | None = Query(None, alias="status"),
    mine: bool = False,
):
    stmt = select(Class)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Class.name.ilike(pattern),
                Class.description.ilike(pattern),
                Class.invite_code.ilike(pattern),
            )
        )
    if subject:
        stmt = stmt.join(Class.subject).where(
            or_(Subject.name.ilike(subject), Subject.code.ilike(subject))
        )
    if department:
        stmt = (
            stmt.join(Class.subject)
            .join(Subject.department)
            .where(
                or_(
                    Department.name.ilike(department),
                    Department.code.ilike(department),
                )
            )
        )
    if teacher:
        stmt = stmt.join(Class.lecturer).where(
            or_(User.name.ilike(f"%{teacher}%"), User.email.ilike(f"%{teacher}%"))
        )
    if class_status:
        stmt = stmt.where(Class.status == class_status)

    if mine:
        role = to_api_role(current_user.role)
        if role == "student":
            stmt = stmt.join(Class.enrollments).where(
                Enrollment.student_id == current_user.id
            )
        else:
            stmt = stmt.where(
                or_(
                    Class.lecturer_id == current_user.id,
                    Class.tutor_id == current_user.id,
                )
            )

    rows, pagination = paginate(db, stmt.order_by(Class.id), page, limit, LOAD)
    return envelope([ClassOut.model_validate(r) for r in rows], pagination)


@router.get("/{class_id}", response_model=SingleResponse[ClassOut])
def get_class(
    class_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    return SingleResponse[ClassOut](
        data=ClassOut.model_validate(get_class_or_404(db, class_id))
    )


@router.post(
    "", response_model=SingleResponse[ClassOut], status_code=status.HTTP_201_CREATED
)
def create_class(
    payload: ClassCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not can_manage(current_user):
        raise HTTPException(
            status_code=403, detail="You do not have permission to create classes"
        )

    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    assert_role(db, payload.lecturer_id, ("lecturer",), "Lecturer")
    if payload.tutor_id is not None:
        assert_role(db, payload.tutor_id, ("tutor", "lecturer"), "Tutor")
        if payload.tutor_id == payload.lecturer_id:
            raise HTTPException(
                status_code=422,
                detail="The tutor and the lecturer must be different people",
            )

    if not is_privileged(current_user) and payload.lecturer_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Lecturers can only create their own classes"
        )

    row = Class(**payload.model_dump(), invite_code=generate_invite_code(db))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="That class could not be created"
        ) from exc

    return SingleResponse[ClassOut](
        data=ClassOut.model_validate(get_class_or_404(db, row.id))
    )


@router.patch("/{class_id}", response_model=SingleResponse[ClassOut])
def update_class(
    class_id: int,
    payload: ClassUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = get_class_or_404(db, class_id)
    if not can_manage(current_user, row):
        raise HTTPException(
            status_code=403, detail="You do not have permission to edit this class"
        )

    data = payload.model_dump(exclude_unset=True)

    if "subject_id" in data and db.get(Subject, data["subject_id"]) is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    if "lecturer_id" in data:
        assert_role(db, data["lecturer_id"], ("lecturer",), "Lecturer")
    if data.get("tutor_id") is not None:
        assert_role(db, data["tutor_id"], ("tutor", "lecturer"), "Tutor")

    lecturer_id = data.get("lecturer_id", row.lecturer_id)
    tutor_id = data.get("tutor_id", row.tutor_id)
    if tutor_id is not None and tutor_id == lecturer_id:
        raise HTTPException(
            status_code=422,
            detail="The tutor and the lecturer must be different people",
        )

    if "capacity" in data:
        enrolled = db.scalar(
            select(Enrollment.id).where(Enrollment.class_id == row.id).limit(1)
        )
        if enrolled is not None:
            current_count = len(row.enrollments)
            if data["capacity"] < current_count:
                raise HTTPException(
                    status_code=422,
                    detail=f"Capacity cannot be lower than the {current_count} students already enrolled",
                )

    for key, value in data.items():
        setattr(row, key, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="That class could not be updated"
        ) from exc

    return SingleResponse[ClassOut](
        data=ClassOut.model_validate(get_class_or_404(db, row.id))
    )


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = get_class_or_404(db, class_id)
    if not can_manage(current_user, row):
        raise HTTPException(
            status_code=403, detail="You do not have permission to remove this class"
        )
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
