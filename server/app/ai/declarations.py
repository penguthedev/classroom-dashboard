from typing import Any

STRING = {"type": "STRING"}
INTEGER = {"type": "INTEGER"}
BOOLEAN = {"type": "BOOLEAN"}


def described(base: dict[str, Any], description: str) -> dict[str, Any]:
    return {**base, "description": description}


def declaration(
    name: str,
    description: str,
    properties: dict[str, Any] | None = None,
    required: list[str] | None = None,
) -> dict[str, Any]:
    if not properties:
        return {"name": name, "description": description}
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "OBJECT",
            "properties": properties,
            "required": required or [],
        },
    }


LIMIT = described(INTEGER, "Maximum rows to return, 1 to 50.")
CONFIRMED = described(
    BOOLEAN,
    "Set to true only after the user has explicitly agreed to this exact change.",
)

READ_DECLARATIONS: list[dict[str, Any]] = [
    declaration(
        "get_my_profile",
        "Get the signed-in user's own account, role, department or programme, and their headline counts. Call this first when the question depends on who is asking.",
    ),
    declaration(
        "get_dashboard_overview",
        "Get counts across the whole system: faculties, departments, programmes, subjects, classes, rooms, unread notifications and upcoming sessions. Use for 'how many' and summary questions.",
    ),
    declaration(
        "list_my_classes",
        "List the classes the signed-in user is enrolled in as a student, or teaches as lecturer or tutor.",
        {"limit": LIMIT},
    ),
    declaration(
        "list_my_schedule",
        "List timetabled sessions for the signed-in user in a date window. Defaults to the next 14 days.",
        {
            "from_date": described(STRING, "ISO 8601 start of the window, e.g. 2026-09-14T00:00:00Z."),
            "to_date": described(STRING, "ISO 8601 end of the window."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "get_class",
        "Get one class in detail with its subject, lecturer, tutor, seats left and next sessions. Identify it by class_id or invite_code.",
        {
            "class_id": described(INTEGER, "Numeric class id."),
            "invite_code": described(STRING, "The class invite code."),
        },
    ),
    declaration(
        "list_class_roster",
        "List the students enrolled in a class. Only available for classes the user teaches or administers.",
        {"class_id": described(INTEGER, "Numeric class id."), "limit": LIMIT},
        ["class_id"],
    ),
    declaration(
        "search_classes",
        "Search classes across the institution by name, subject, department or status.",
        {
            "query": described(STRING, "Free text matched against class name and description."),
            "subject": described(STRING, "Subject name or code."),
            "department": described(STRING, "Department name or code."),
            "status": described(STRING, "Either active or archived."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "search_subjects",
        "Search subjects by name or code, optionally scoped to a department.",
        {
            "query": described(STRING, "Free text matched against subject name and code."),
            "department": described(STRING, "Department name or code."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "list_departments",
        "List academic departments, optionally filtered by name, code or faculty.",
        {
            "query": described(STRING, "Free text matched against department name and code."),
            "faculty": described(STRING, "Faculty name or code."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "list_programmes",
        "List degree programmes, optionally filtered by name, code or department.",
        {
            "query": described(STRING, "Free text matched against programme name and code."),
            "department": described(STRING, "Department name or code."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "search_people",
        "Look up staff and, for admin accounts, students. Students and teaching staff only ever see teaching staff.",
        {
            "query": described(STRING, "Name or email fragment."),
            "role": described(STRING, "One of student, lecturer, tutor, admin, technical_services."),
            "department": described(STRING, "Department name or code."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "list_rooms",
        "List teaching rooms with their capacity, type and building.",
        {
            "query": described(STRING, "Room code or name fragment."),
            "building": described(STRING, "Building name or code."),
            "room_type": described(STRING, "One of lecture_hall, laboratory, tutorial_room, computer_lab, seminar_room."),
            "min_capacity": described(INTEGER, "Only rooms with at least this capacity."),
            "limit": LIMIT,
        },
    ),
    declaration(
        "find_free_rooms",
        "Find rooms with no active booking overlapping a given time window. Use this before proposing a new session.",
        {
            "starts_at": described(STRING, "ISO 8601 start of the slot."),
            "ends_at": described(STRING, "ISO 8601 end of the slot."),
            "min_capacity": described(INTEGER, "Only rooms with at least this capacity."),
            "room_type": described(STRING, "Restrict to a room type."),
            "building": described(STRING, "Building name or code."),
            "limit": LIMIT,
        },
        ["starts_at", "ends_at"],
    ),
    declaration(
        "list_my_notifications",
        "List the signed-in user's notifications, newest first.",
        {
            "unread_only": described(BOOLEAN, "Only return notifications that are still unread."),
            "limit": LIMIT,
        },
    ),
]

WRITE_DECLARATIONS: list[dict[str, Any]] = [
    declaration(
        "join_class_by_invite_code",
        "Enroll the signed-in student in a class using its invite code.",
        {
            "invite_code": described(STRING, "The invite code the student was given."),
            "confirmed": CONFIRMED,
        },
        ["invite_code"],
    ),
    declaration(
        "enroll_student",
        "Enroll a named student into a class the user teaches or administers.",
        {
            "student_id": described(INTEGER, "Numeric user id of the student."),
            "class_id": described(INTEGER, "Numeric class id."),
            "confirmed": CONFIRMED,
        },
        ["student_id", "class_id"],
    ),
    declaration(
        "remove_enrollment",
        "Remove an enrollment. Always confirm with the user first.",
        {
            "enrollment_id": described(INTEGER, "Numeric enrollment id from list_class_roster."),
            "confirmed": CONFIRMED,
        },
        ["enrollment_id"],
    ),
    declaration(
        "create_class",
        "Create a new class section for a subject.",
        {
            "subject_id": described(INTEGER, "Numeric subject id."),
            "name": described(STRING, "Name of the class section."),
            "description": described(STRING, "Optional description."),
            "capacity": described(INTEGER, "Number of seats, defaults to 30."),
            "lecturer_id": described(INTEGER, "Lecturer user id. Defaults to the signed-in lecturer."),
            "tutor_id": described(INTEGER, "Optional tutor user id."),
            "confirmed": CONFIRMED,
        },
        ["subject_id", "name"],
    ),
    declaration(
        "update_class",
        "Update the name, description, capacity or status of a class.",
        {
            "class_id": described(INTEGER, "Numeric class id."),
            "name": STRING,
            "description": STRING,
            "capacity": INTEGER,
            "status": described(STRING, "Either active or archived."),
            "confirmed": CONFIRMED,
        },
        ["class_id"],
    ),
    declaration(
        "create_schedule",
        "Book a new timetabled session for a class. Check find_free_rooms first if the room is not already decided.",
        {
            "class_id": described(INTEGER, "Numeric class id."),
            "room_id": described(INTEGER, "Numeric room id."),
            "starts_at": described(STRING, "ISO 8601 start time."),
            "ends_at": described(STRING, "ISO 8601 end time."),
            "lecturer_id": described(INTEGER, "Defaults to the class lecturer."),
            "tutor_id": described(INTEGER, "Defaults to the class tutor."),
            "notes": STRING,
            "confirmed": CONFIRMED,
        },
        ["class_id", "room_id", "starts_at", "ends_at"],
    ),
    declaration(
        "update_schedule",
        "Move or edit an existing session. Returns the clashing bookings instead of saving if the new slot conflicts.",
        {
            "schedule_id": described(INTEGER, "Numeric schedule id."),
            "starts_at": described(STRING, "New ISO 8601 start time."),
            "ends_at": described(STRING, "New ISO 8601 end time."),
            "room_id": described(INTEGER, "New room id."),
            "status": described(STRING, "One of scheduled, rescheduled, cancelled, completed."),
            "notes": STRING,
            "confirmed": CONFIRMED,
        },
        ["schedule_id"],
    ),
    declaration(
        "cancel_schedule",
        "Cancel a session and notify everyone enrolled.",
        {
            "schedule_id": described(INTEGER, "Numeric schedule id."),
            "reason": described(STRING, "Short reason shown in the notification."),
            "confirmed": CONFIRMED,
        },
        ["schedule_id"],
    ),
    declaration(
        "mark_notifications_read",
        "Mark the signed-in user's notifications as read.",
        {
            "notification_ids": {
                "type": "ARRAY",
                "items": INTEGER,
                "description": "Specific notification ids to mark read.",
            },
            "all": described(BOOLEAN, "Mark every unread notification as read."),
        },
    ),
    declaration(
        "create_subject",
        "Create a new subject inside a department. Admin and technical services only.",
        {
            "department_id": described(INTEGER, "Numeric department id."),
            "code": described(STRING, "Short subject code."),
            "name": described(STRING, "Subject name."),
            "description": STRING,
            "confirmed": CONFIRMED,
        },
        ["department_id", "code", "name"],
    ),
    declaration(
        "update_my_profile",
        "Update the signed-in user's own contact details.",
        {
            "full_name": STRING,
            "phone_number": STRING,
            "address": STRING,
            "emergency_contact_name": STRING,
            "emergency_contact_phone": STRING,
            "confirmed": CONFIRMED,
        },
    ),
]

FINAL_ANSWER = declaration(
    "final_answer",
    "Deliver the finished answer to the user. Call this exactly once, as the last step, after any data gathering is done.",
    {
        "reply": described(
            STRING,
            "The answer in markdown. Bold key figures, use short bullet lists, and never invent data that no tool returned.",
        ),
        "is_refusal": described(
            BOOLEAN,
            "True only when the request falls outside this dashboard and student wellbeing support.",
        ),
        "refusal_reason": described(STRING, "Short reason when is_refusal is true, otherwise empty."),
        "sources": {
            "type": "ARRAY",
            "items": STRING,
            "description": "Where the answer came from, e.g. 'Dashboard > Classes' or 'Timetable'.",
        },
        "follow_ups": {
            "type": "ARRAY",
            "items": STRING,
            "description": "Two or three short follow-up questions the user is likely to ask next.",
        },
    },
    ["reply", "is_refusal"],
)


WRITE_TOOLS_BY_ROLE: dict[str, set[str]] = {
    "student": {
        "join_class_by_invite_code",
        "remove_enrollment",
        "mark_notifications_read",
        "update_my_profile",
    },
    "tutor": {
        "enroll_student",
        "remove_enrollment",
        "update_class",
        "create_schedule",
        "update_schedule",
        "cancel_schedule",
        "mark_notifications_read",
        "update_my_profile",
    },
    "lecturer": {
        "enroll_student",
        "remove_enrollment",
        "create_class",
        "update_class",
        "create_schedule",
        "update_schedule",
        "cancel_schedule",
        "mark_notifications_read",
        "update_my_profile",
    },
}

ALL_WRITE_TOOL_NAMES = {d["name"] for d in WRITE_DECLARATIONS}


def write_tools_for(role: str) -> set[str]:
    if role in ("admin", "technical_services"):
        return set(ALL_WRITE_TOOL_NAMES)
    return WRITE_TOOLS_BY_ROLE.get(role, set())


def declarations_for(role: str, allow_writes: bool = True) -> list[dict[str, Any]]:
    tools = list(READ_DECLARATIONS)
    if allow_writes:
        permitted = write_tools_for(role)
        tools.extend(d for d in WRITE_DECLARATIONS if d["name"] in permitted)
    tools.append(FINAL_ANSWER)
    return tools
