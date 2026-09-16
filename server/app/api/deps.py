from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Department, StaffProfile, StudentProfile, User
from app.schemas.enums import PRIVILEGED_ROLES, to_api_role, to_db_role

bearer_scheme = HTTPBearer(auto_error=False)
optional_bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def user_loader_options() -> list:
    return [
        selectinload(User.student_profile).joinedload(StudentProfile.programme),
        selectinload(User.staff_profile)
        .joinedload(StaffProfile.department)
        .joinedload(Department.faculty),
        selectinload(User.documents),
    ]


def load_user(db: Session, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id).options(*user_loader_options())
    return db.scalars(stmt).unique().one_or_none()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise CREDENTIALS_ERROR

    subject = payload.get("sub")
    if subject is None:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise CREDENTIALS_ERROR from None

    user = load_user(db, user_id)
    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is awaiting admin approval.",
        )
    return user


def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(optional_bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None
    user = load_user(db, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    allowed = {to_db_role(role) for role in roles}

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency


def is_privileged(user: User) -> bool:
    return to_api_role(user.role) in PRIVILEGED_ROLES


def is_staff(user: User) -> bool:
    return user.role != "student"


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_role("admin", "technical_services"))]
