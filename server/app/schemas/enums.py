from typing import Literal

Role = Literal["student", "lecturer", "tutor", "admin", "technical_services"]
StaffRole = Literal["lecturer", "tutor", "admin", "technical_services"]
DbRole = Literal["student", "lecturer", "tutor", "admin", "technical"]

ClassStatus = Literal["active", "archived"]
RoomType = Literal[
    "lecture_hall", "laboratory", "tutorial_room", "computer_lab", "seminar_room"
]
ScheduleStatus = Literal["scheduled", "rescheduled", "cancelled", "completed"]
NotificationType = Literal[
    "schedule_created",
    "schedule_updated",
    "schedule_cancelled",
    "enrollment",
    "system",
]
DocumentKind = Literal[
    "enrollment_proof", "transcript", "qualification", "staff_verification", "other"
]
AcademicPosition = Literal[
    "professor",
    "associate_professor",
    "senior_lecturer",
    "lecturer",
    "assistant_lecturer",
]
TechnicalSpecialization = Literal[
    "network_administration",
    "system_administration",
    "cybersecurity",
    "hardware_support",
    "software_support",
    "database_administration",
]

ACADEMIC_POSITIONS: tuple[str, ...] = (
    "professor",
    "associate_professor",
    "senior_lecturer",
    "lecturer",
    "assistant_lecturer",
)
TECHNICAL_SPECIALIZATIONS: tuple[str, ...] = (
    "network_administration",
    "system_administration",
    "cybersecurity",
    "hardware_support",
    "software_support",
    "database_administration",
)
YEARS_OF_STUDY: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)


def humanize(value: str) -> str:
    return value.replace("_", " ").title()

STAFF_ROLES: tuple[str, ...] = ("lecturer", "tutor", "admin", "technical_services")
TEACHING_ROLES: tuple[str, ...] = ("lecturer", "tutor")
PRIVILEGED_ROLES: tuple[str, ...] = ("admin", "technical_services")

_API_TO_DB = {
    "student": "student",
    "lecturer": "lecturer",
    "tutor": "tutor",
    "admin": "admin",
    "technical_services": "technical",
}

_DB_TO_API = {v: k for k, v in _API_TO_DB.items()}


def to_db_role(role: str) -> str:
    return _API_TO_DB.get(role, role)


def to_api_role(role: str) -> str:
    return _DB_TO_API.get(role, role)
