from pydantic import BaseModel


class RoleBreakdown(BaseModel):
    student: int = 0
    lecturer: int = 0
    tutor: int = 0
    admin: int = 0
    technical_services: int = 0


class OverviewOut(BaseModel):
    faculties: int
    departments: int
    programmes: int
    subjects: int
    classes: int
    active_classes: int
    users: int
    enrollments: int
    buildings: int
    rooms: int
    schedules_this_week: int
    unread_notifications: int
    users_by_role: RoleBreakdown
