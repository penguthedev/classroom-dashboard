from app.models.faculty import Faculty
from app.models.department import Department
from app.models.programme import Programme
from app.models.subject import Subject
from app.models.user import User
from app.models.profile import StaffProfile, StudentProfile
from app.models.building import Building
from app.models.room import Room
from app.models.class_ import Class
from app.models.schedule import Schedule
from app.models.enrollment import Enrollment
from app.models.notification import Notification
from app.models.document import Document

__all__ = [
    "Faculty",
    "Department",
    "Programme",
    "Subject",
    "User",
    "StudentProfile",
    "StaffProfile",
    "Building",
    "Room",
    "Class",
    "Schedule",
    "Enrollment",
    "Notification",
    "Document",
]
