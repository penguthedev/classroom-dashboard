from typing import Any

from app.models import User
from app.schemas.enums import to_api_role
from app.schemas.refs import DepartmentRef, ProgrammeRef
from app.schemas.user import UserOut, UserSummaryOut


def document_urls(user: User) -> dict[str, str]:
    urls: dict[str, str] = {}
    for doc in user.documents or []:
        urls.setdefault(doc.kind, doc.file_url)
    return urls


def id_code_of(user: User) -> str | None:
    if user.student_profile is not None:
        return user.student_profile.student_number
    if user.staff_profile is not None:
        return user.staff_profile.staff_number
    return None


def faculty_name_of(user: User) -> str | None:
    staff = user.staff_profile
    if staff is None or staff.department is None:
        return None
    faculty = staff.department.faculty
    return faculty.name if faculty is not None else None


def build_profile(user: User) -> dict[str, Any] | None:
    role = to_api_role(user.role)
    docs = document_urls(user)

    if role == "student":
        student = user.student_profile
        if student is None:
            return None
        return {
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "programme": student.programme.name if student.programme else None,
            "programme_id": student.programme_id,
            "year_of_study": student.year_of_study,
            "proof_of_enrollment_url": docs.get("enrollment_proof"),
            "transcript_url": docs.get("transcript"),
        }

    staff = user.staff_profile
    if staff is None:
        return None

    base = {
        "department_id": staff.department_id,
        "department": staff.department.name if staff.department else None,
        "faculty": faculty_name_of(user),
    }

    if role == "lecturer":
        return {
            **base,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "academic_position": staff.position,
            "specialization": staff.specialization,
            "qualification": staff.qualification,
            "qualification_document_url": docs.get("qualification"),
        }

    if role == "tutor":
        return {
            **base,
            "date_of_birth": user.date_of_birth.isoformat() if user.date_of_birth else None,
            "subject_specialization": staff.specialization,
            "qualification": staff.qualification,
            "qualification_document_url": docs.get("qualification"),
        }

    if role == "admin":
        return {
            **base,
            "position": staff.position,
            "verification_document_url": docs.get("staff_verification"),
        }

    return {
        **base,
        "technical_position": staff.position,
        "technical_specialization": staff.specialization,
        "qualification": staff.qualification,
        "certification_document_url": docs.get("qualification"),
    }


def serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        id_code=id_code_of(user),
        role=to_api_role(user.role),
        full_name=user.name,
        username=user.username,
        email=user.email,
        phone_number=user.phone,
        profile_picture_url=user.image_url,
        address=user.address,
        emergency_contact_name=user.emergency_contact_name,
        emergency_contact_phone=user.emergency_contact_phone,
        date_of_birth=user.date_of_birth,
        is_active=user.is_active,
        created_at=user.created_at,
        profile=build_profile(user),
    )


def serialize_user_summary(user: User) -> UserSummaryOut:
    staff = user.staff_profile
    student = user.student_profile
    return UserSummaryOut(
        id=user.id,
        id_code=id_code_of(user),
        role=to_api_role(user.role),
        full_name=user.name,
        email=user.email,
        profile_picture_url=user.image_url,
        department=(
            DepartmentRef.model_validate(staff.department)
            if staff is not None and staff.department is not None
            else None
        ),
        programme=(
            ProgrammeRef.model_validate(student.programme)
            if student is not None and student.programme is not None
            else None
        ),
        year_of_study=student.year_of_study if student is not None else None,
    )
