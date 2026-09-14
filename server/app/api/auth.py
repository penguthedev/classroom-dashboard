import hashlib
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from math import ceil
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, load_user
from app.core.config import settings
from app.core.mail import MailError, send_password_reset
from app.core.security import create_access_token, hash_password, verify_password
from app.core.storage import StorageError, upload_fileobj
from app.db.session import get_db
from app.models import (
    Department,
    Document,
    Faculty,
    PasswordResetToken,
    Programme,
    StaffProfile,
    StudentProfile,
    User,
)
from app.schemas.auth import (
    AdminRegisterRequest,
    AuthPayload,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LecturerRegisterRequest,
    LockoutDetail,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    StudentRegisterRequest,
    TechnicalRegisterRequest,
    TutorRegisterRequest,
)
from app.schemas.enums import to_db_role
from app.schemas.user import UserOut
from app.services.serializers import serialize_user

logger = logging.getLogger(__name__)

router = APIRouter()

DOCUMENT_KINDS: dict[str, str] = {
    "proof_of_enrollment": "enrollment_proof",
    "transcript": "transcript",
    "qualification_document": "qualification",
    "staff_verification_document": "staff_verification",
    "certification_document": "qualification",
}


def initials_from_name(name: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z]+", name) if p]
    if not parts:
        return "STU"
    letters = "".join(p[0] for p in parts).upper()
    return letters[:4] if len(letters) > 1 else (letters + "X")[:2]


def next_student_number(db: Session, full_name: str) -> str:
    prefix = initials_from_name(full_name)
    pattern = f"{prefix}%"
    existing = db.scalars(
        select(StudentProfile.student_number).where(
            StudentProfile.student_number.like(pattern)
        )
    ).all()

    highest = 0
    for number in existing:
        tail = number[len(prefix):]
        if tail.isdigit():
            highest = max(highest, int(tail))

    return f"{prefix}{highest + 1:05d}"


def ensure_unique_account(db: Session, email: str, username: str) -> None:
    clash = db.scalars(
        select(User).where(or_(User.email == email, User.username == username)).limit(1)
    ).one_or_none()
    if clash is None:
        return
    if clash.email == email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="This username is already taken",
    )


def ensure_unique_student_number(db: Session, student_number: str) -> None:
    taken = db.scalar(
        select(func.count())
        .select_from(StudentProfile)
        .where(StudentProfile.student_number == student_number)
    )
    if taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student ID is already registered",
        )


def resolve_student_number(db: Session, payload: StudentRegisterRequest) -> str:
    supplied = (payload.id_code or "").strip()
    if not supplied:
        return next_student_number(db, payload.full_name)
    ensure_unique_student_number(db, supplied)
    return supplied


def ensure_unique_id_code(db: Session, id_code: str) -> None:
    taken = db.scalar(
        select(func.count())
        .select_from(StaffProfile)
        .where(StaffProfile.staff_number == id_code)
    )
    if taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This staff ID is already registered",
        )


def get_department_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return department


def get_faculty_or_404(db: Session, faculty_id: int | None) -> Faculty | None:
    if faculty_id is None:
        return None
    faculty = db.get(Faculty, faculty_id)
    if faculty is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return faculty


def resolve_student_programme(db: Session, payload: Any) -> int | None:
    if payload.programme_id is not None:
        programme = db.get(Programme, payload.programme_id)
        if programme is None:
            raise HTTPException(status_code=404, detail="Programme not found")
        return programme.id
    return resolve_programme_id(db, payload.programme)


def resolve_programme_id(db: Session, label: str | None) -> int | None:
    if not label:
        return None
    cleaned = label.strip()
    if not cleaned:
        return None
    row = db.scalars(
        select(Programme)
        .where(or_(Programme.name.ilike(cleaned), Programme.code.ilike(cleaned)))
        .limit(1)
    ).one_or_none()
    if row is not None:
        return row.id
    row = db.scalars(
        select(Programme).where(Programme.name.ilike(f"%{cleaned}%")).limit(1)
    ).one_or_none()
    return row.id if row is not None else None


def store_upload(upload: UploadFile | None, kind: str) -> dict[str, Any] | None:
    if upload is None or not upload.filename:
        return None
    if not settings.storage_enabled:
        return None
    content_type = upload.content_type or "application/octet-stream"
    try:
        stored = upload_fileobj(
            upload.file,
            kind,
            content_type,
            filename=upload.filename,
            size_bytes=getattr(upload, "size", None),
        )
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "object_key": stored.object_key,
        "file_url": stored.file_url,
        "content_type": stored.content_type,
        "size_bytes": stored.size_bytes,
        "original_filename": upload.filename,
    }


def attach_documents(
    db: Session, user: User, uploads: dict[str, UploadFile | None]
) -> None:
    for field_name, upload in uploads.items():
        stored = store_upload(upload, "document")
        if stored is None:
            continue
        db.add(
            Document(
                user_id=user.id,
                kind=DOCUMENT_KINDS.get(field_name, "other"),
                file_url=stored["file_url"],
                object_key=stored["object_key"],
                original_filename=stored["original_filename"],
                content_type=stored["content_type"],
                size_bytes=stored["size_bytes"],
            )
        )


def build_user(payload: Any, role: str, picture: UploadFile | None) -> User:
    stored = store_upload(picture, "image")
    return User(
        email=str(payload.email).lower(),
        username=payload.username,
        name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=to_db_role(role),
        phone=payload.phone_number,
        date_of_birth=getattr(payload, "date_of_birth", None),
        address=payload.address,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        image_url=stored["file_url"] if stored else None,
        image_object_key=stored["object_key"] if stored else None,
        is_active=True,
    )


def finalize(db: Session, user: User) -> AuthPayload:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with these details already exists",
        ) from exc

    fresh = load_user(db, user.id)
    token = create_access_token(user.id, user.role)
    return AuthPayload(user=serialize_user(fresh), access_token=token)


@router.post(
    "/register/student",
    response_model=AuthPayload,
    status_code=status.HTTP_201_CREATED,
)
def register_student(
    payload: Annotated[StudentRegisterRequest, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_unique_account(db, str(payload.email).lower(), payload.username)
    student_number = resolve_student_number(db, payload)

    user = build_user(payload, "student", payload.profile_picture)
    db.add(user)
    db.flush()

    db.add(
        StudentProfile(
            user_id=user.id,
            programme_id=resolve_student_programme(db, payload),
            student_number=student_number,
            year_of_study=payload.year_of_study,
        )
    )
    attach_documents(
        db,
        user,
        {
            "proof_of_enrollment": payload.proof_of_enrollment,
            "transcript": payload.transcript,
        },
    )
    return finalize(db, user)


@router.post(
    "/register/lecturer",
    response_model=AuthPayload,
    status_code=status.HTTP_201_CREATED,
)
def register_lecturer(
    payload: Annotated[LecturerRegisterRequest, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_unique_account(db, str(payload.email).lower(), payload.username)
    ensure_unique_id_code(db, payload.id_code)
    get_department_or_404(db, payload.department_id)
    get_faculty_or_404(db, payload.faculty_id)

    user = build_user(payload, "lecturer", payload.profile_picture)
    db.add(user)
    db.flush()

    db.add(
        StaffProfile(
            user_id=user.id,
            department_id=payload.department_id,
            staff_number=payload.id_code,
            position=payload.academic_position,
            specialization=payload.specialization,
            qualification=payload.qualification,
        )
    )
    attach_documents(db, user, {"qualification_document": payload.qualification_document})
    return finalize(db, user)


@router.post(
    "/register/tutor",
    response_model=AuthPayload,
    status_code=status.HTTP_201_CREATED,
)
def register_tutor(
    payload: Annotated[TutorRegisterRequest, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_unique_account(db, str(payload.email).lower(), payload.username)
    ensure_unique_id_code(db, payload.id_code)
    get_department_or_404(db, payload.department_id)
    get_faculty_or_404(db, payload.faculty_id)

    user = build_user(payload, "tutor", payload.profile_picture)
    db.add(user)
    db.flush()

    db.add(
        StaffProfile(
            user_id=user.id,
            department_id=payload.department_id,
            staff_number=payload.id_code,
            position="tutor",
            specialization=payload.subject_specialization,
            qualification=payload.qualification,
        )
    )
    attach_documents(db, user, {"qualification_document": payload.qualification_document})
    return finalize(db, user)


@router.post(
    "/register/admin",
    response_model=AuthPayload,
    status_code=status.HTTP_201_CREATED,
)
def register_admin(
    payload: Annotated[AdminRegisterRequest, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    staff_verification_document = payload.staff_verification_document
    if settings.storage_enabled and (
        staff_verification_document is None or not staff_verification_document.filename
    ):
        raise HTTPException(
            status_code=422,
            detail="Staff verification document is required for admin accounts",
        )

    ensure_unique_account(db, str(payload.email).lower(), payload.username)
    ensure_unique_id_code(db, payload.id_code)
    get_department_or_404(db, payload.department_id)

    user = build_user(payload, "admin", payload.profile_picture)
    db.add(user)
    db.flush()

    db.add(
        StaffProfile(
            user_id=user.id,
            department_id=payload.department_id,
            staff_number=payload.id_code,
            position=payload.position,
        )
    )
    attach_documents(
        db, user, {"staff_verification_document": staff_verification_document}
    )
    return finalize(db, user)


@router.post(
    "/register/technical-services",
    response_model=AuthPayload,
    status_code=status.HTTP_201_CREATED,
)
def register_technical_services(
    payload: Annotated[TechnicalRegisterRequest, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    ensure_unique_account(db, str(payload.email).lower(), payload.username)
    ensure_unique_id_code(db, payload.id_code)
    get_department_or_404(db, payload.department_id)

    user = build_user(payload, "technical_services", payload.profile_picture)
    db.add(user)
    db.flush()

    db.add(
        StaffProfile(
            user_id=user.id,
            department_id=payload.department_id,
            staff_number=payload.id_code,
            position=payload.technical_position,
            specialization=payload.technical_specialization,
            qualification=payload.qualification,
        )
    )
    attach_documents(db, user, {"certification_document": payload.certification_document})
    return finalize(db, user)


@router.post("/login", response_model=AuthPayload)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    identifier = payload.identifier.strip()
    user = db.scalars(
        select(User)
        .where(
            or_(
                func.lower(User.email) == identifier.lower(),
                User.username == identifier,
            )
        )
        .limit(1)
    ).one_or_none()

    now = datetime.now(UTC)

    if user is not None and user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > now:
            remaining = (locked_until - now).total_seconds()
            raise lockout_error(max(1, ceil(remaining)))
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()

    if user is None or not verify_password(payload.password, user.password_hash):
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
                user.locked_until = now + timedelta(
                    seconds=settings.LOGIN_LOCKOUT_SECONDS
                )
                user.failed_login_attempts = 0
                db.commit()
                raise lockout_error(settings.LOGIN_LOCKOUT_SECONDS)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or username, or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    fresh = load_user(db, user.id)
    token = create_access_token(user.id, user.role)
    return AuthPayload(user=serialize_user(fresh), access_token=token)


def lockout_error(retry_after_seconds: int) -> HTTPException:
    seconds = max(retry_after_seconds, 1)
    detail = LockoutDetail(
        message=(
            f"Too many failed login attempts. Please wait {seconds} second"
            f"{'s' if seconds != 1 else ''} before trying again."
        ),
        retry_after=seconds,
        retry_after_seconds=seconds,
    )
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail.model_dump(),
        headers={"Retry-After": str(seconds)},
    )


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser):
    return serialize_user(current_user)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_reset_token(db: Session, user: User) -> str:
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).update({"used": True})

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(token),
            expires_at=expires_at,
        )
    )
    return token


def consume_reset_token(db: Session, token: str) -> User:
    row = db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(token)
        )
    ).one_or_none()

    if row is None or row.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That reset link is not valid. Request a new one.",
        )

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That reset link has expired. Request a new one.",
        )

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That reset link is not valid. Request a new one.",
        )

    row.used = True
    return user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    confirmation = MessageResponse(
        message=(
            "If an account exists for that address, a reset link is on its way. "
            "Check your inbox and your spam folder."
        )
    )

    user = db.scalars(
        select(User).where(func.lower(User.email) == str(payload.email).lower())
    ).one_or_none()

    if user is None or not user.is_active:
        return confirmation

    token = issue_reset_token(db, user)
    db.commit()

    reset_url = f"{settings.frontend_origin}/reset-password?token={token}"
    try:
        send_password_reset(
            user.email,
            user.name,
            reset_url,
            settings.PASSWORD_RESET_EXPIRE_MINUTES,
        )
    except MailError:
        logger.error("Password reset mail failed for user %s", user.id)

    return confirmation


@router.post("/reset-password", response_model=AuthPayload)
def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
):
    user = consume_reset_token(db, payload.token)

    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    fresh = load_user(db, user.id)
    token = create_access_token(fresh.id, fresh.role)
    return AuthPayload(user=serialize_user(fresh), access_token=token)


@router.post("/change-password", response_model=AuthPayload)
def change_password(
    payload: ChangePasswordRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.failed_login_attempts = 0
    current_user.locked_until = None
    db.commit()

    fresh = load_user(db, current_user.id)
    token = create_access_token(fresh.id, fresh.role)
    return AuthPayload(user=serialize_user(fresh), access_token=token)
