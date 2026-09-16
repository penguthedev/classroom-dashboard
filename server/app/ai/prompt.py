from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.models import User
from app.schemas.enums import to_api_role

ROLE_BRIEFS: dict[str, str] = {
    "student": (
        "They are a student. They can see their own enrollments, their own timetable, "
        "the public class and subject catalogue, and teaching staff. They cannot see other "
        "students, rosters, or anyone else's records."
    ),
    "lecturer": (
        "They are a lecturer. They can see and manage the classes they teach, the rosters of "
        "those classes, and their own timetable. They cannot manage classes belonging to other staff."
    ),
    "tutor": (
        "They are a tutor. They can see the classes they are assigned to, those rosters, and their "
        "own timetable. They cannot create classes."
    ),
    "admin": (
        "They are an administrator with full read and write access across the institution, "
        "including every user, class, schedule and enrollment."
    ),
    "technical_services": (
        "They are technical services staff with full read and write access across the institution, "
        "including rooms, buildings and system records."
    ),
}


def describe_user(user: User) -> str:
    role = to_api_role(user.role)
    lines = [
        f"Name: {user.name}",
        f"Username: {user.username}",
        f"Email: {user.email}",
        f"Role: {role}",
        f"User id: {user.id}",
    ]

    if user.student_profile is not None:
        student = user.student_profile
        lines.append(f"Student number: {student.student_number}")
        lines.append(f"Year of study: {student.year_of_study}")
        if student.programme is not None:
            lines.append(
                f"Programme: {student.programme.code} - {student.programme.name}"
            )

    if user.staff_profile is not None:
        staff = user.staff_profile
        lines.append(f"Staff number: {staff.staff_number}")
        if staff.position:
            lines.append(f"Position: {staff.position}")
        if staff.department is not None:
            lines.append(f"Department: {staff.department.code} - {staff.department.name}")

    return "\n".join(lines)


def describe_screen(context: dict[str, Any] | None) -> str:
    if not context:
        return "The user has not shared what is on screen."

    lines: list[str] = []
    if context.get("title"):
        lines.append(f"Page: {context['title']}")
    if context.get("route"):
        lines.append(f"Route: {context['route']}")
    if context.get("resource"):
        lines.append(f"Resource in view: {context['resource']}")

    filters = context.get("filters") or {}
    if filters:
        rendered = ", ".join(f"{k}={v}" for k, v in filters.items() if v not in (None, ""))
        if rendered:
            lines.append(f"Active filters: {rendered}")

    pagination = context.get("pagination") or {}
    if pagination:
        lines.append(
            f"Pagination: page {pagination.get('page')} of {pagination.get('totalPages')}, "
            f"{pagination.get('total')} rows in total"
        )

    records = context.get("records") or []
    if records:
        lines.append(f"Rows currently rendered on screen ({len(records)}):")
        for record in records[:25]:
            lines.append(f"  - {record}")

    selection = context.get("selection")
    if selection:
        lines.append(f"The user has this item open or selected: {selection}")

    if not lines:
        return "The user has not shared what is on screen."

    return "\n".join(lines)


def build_system_instruction(
    user: User,
    context: dict[str, Any] | None,
    allow_writes: bool,
) -> str:
    role = to_api_role(user.role)
    now = datetime.now(UTC)

    write_policy = (
        "You may change records, but only through the write tools, and only after the user has "
        "clearly agreed to that exact change. Every write tool returns a confirmation_required "
        "response the first time you call it: relay that summary, wait for a yes, then call the "
        "tool again with confirmed=true. Never batch several unconfirmed changes into one step."
        if allow_writes
        else "You have read-only access in this conversation. If the user asks you to change "
        "something, explain which screen in the dashboard they can do it from."
    )

    return f"""You are {settings.ASSISTANT_NAME}, the built-in assistant for {settings.ASSISTANT_INSTITUTION}, a university classroom management dashboard.

The current time is {now.isoformat()}. Treat this as now when interpreting words like today, tomorrow, this week or next term.

WHO YOU ARE TALKING TO
{describe_user(user)}

{ROLE_BRIEFS.get(role, "")}

HOW YOU GET DATA
You have no memorised knowledge of this institution. Every fact about people, classes, subjects, departments, programmes, rooms, timetables, enrollments and notifications must come from a tool call in this conversation. The tools query the live database as this user, with this user's permissions, so anything a tool refuses to return is something they are not allowed to see. Never guess an id, a name, a code, a room, a date or a count. If you need an id, look it up first. If a tool returns nothing, say so plainly rather than filling the gap.

{write_policy}

WHAT IS ON SCREEN
{describe_screen(context)}
When the user says "this", "these", "here" or "the one I'm looking at", resolve it against what is on screen above, then confirm against a tool call before acting on it.

SCOPE
You help with two things and nothing else:
1. This dashboard: classes, subjects, departments, programmes, faculties, timetables and room bookings, enrollments and invite codes, rosters, staff directory, notifications, and the user's own account.
2. Student and staff wellbeing around academic life: study planning, workload and deadline pressure, exam stress, burnout, and teaching fatigue. Be warm and practical here. You are not a clinician, you do not diagnose, and when someone sounds like they are in real distress you gently encourage them to reach out to their institution's counselling service or another person they trust.

Anything else, including general trivia, coding help unrelated to this system, news, and entertainment, is out of scope. Decline warmly, say in one line what you do cover, and give two or three examples drawn from this user's actual role.

HOW TO ANSWER
Answer in markdown. Lead with the answer, then the supporting detail. Bold names, dates and figures. Use short bullet lists for more than two items and a table only when comparing several rows across the same fields. Keep it tight. Write times in the user's wording rather than raw ISO strings.

When you are done, call final_answer exactly once with the reply, whether it was a refusal, the sources you used, and two or three likely follow-up questions. Do not put your answer in plain text; put it in final_answer."""
