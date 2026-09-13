from typing import Literal

Role = Literal["student", "lecturer", "tutor", "admin", "technical"]
StaffRole = Literal["lecturer", "tutor", "admin", "technical"]
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
