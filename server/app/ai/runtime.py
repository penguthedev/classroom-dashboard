import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from app.ai.declarations import declarations_for, write_tools_for
from app.ai.prompt import build_system_instruction
from app.ai.tools import READ_TOOLS, WRITE_TOOLS, ToolContext, run_tool
from app.core.config import settings
from app.models import User
from app.schemas.enums import to_api_role

logger = logging.getLogger(__name__)

SOURCE_LABELS: dict[str, str] = {
    "get_my_profile": "Your account",
    "get_dashboard_overview": "Dashboard overview",
    "list_my_classes": "Dashboard > Classes",
    "list_my_schedule": "Dashboard > Timetable",
    "get_class": "Dashboard > Classes",
    "list_class_roster": "Dashboard > Class roster",
    "search_classes": "Dashboard > Classes",
    "search_subjects": "Dashboard > Subjects",
    "list_departments": "Dashboard > Departments",
    "list_programmes": "Dashboard > Programmes",
    "search_people": "Dashboard > Directory",
    "list_rooms": "Dashboard > Rooms",
    "find_free_rooms": "Dashboard > Room availability",
    "list_my_notifications": "Dashboard > Notifications",
}


class AssistantUnavailable(RuntimeError):
    pass


@dataclass
class AssistantReply:
    reply: str
    is_refusal: bool = False
    refusal_reason: str = ""
    sources: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    mutations: list[dict[str, Any]] = field(default_factory=list)
    awaiting_confirmation: bool = False


@lru_cache
def get_client() -> genai.Client:
    if not settings.assistant_enabled:
        raise AssistantUnavailable(
            "The assistant is not configured. Set GEMINI_API_KEY on the server."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def permitted_writes(user: User) -> set[str]:
    return write_tools_for(to_api_role(user.role))


def history_to_contents(history: list[dict[str, Any]]) -> list[types.Content]:
    contents: list[types.Content] = []
    for entry in history[-settings.ASSISTANT_HISTORY_LIMIT :]:
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        role = "user" if entry.get("sender") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=text)])
        )
    return contents


def build_config(user: User, context: dict[str, Any] | None) -> types.GenerateContentConfig:
    role = to_api_role(user.role)
    allow_writes = bool(write_tools_for(role))
    return types.GenerateContentConfig(
        system_instruction=build_system_instruction(user, context, allow_writes),
        tools=[types.Tool(function_declarations=declarations_for(role, allow_writes))],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
        max_output_tokens=2048,
    )


def jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def extract_text(response: Any) -> str:
    chunks: list[str] = []
    for candidate in response.candidates or []:
        for part in (candidate.content.parts if candidate.content else []) or []:
            if getattr(part, "text", None):
                chunks.append(part.text)
    return "\n".join(chunks).strip()


def derive_sources(tool_names: list[str], model_sources: list[str]) -> list[str]:
    derived = []
    for name in tool_names:
        label = SOURCE_LABELS.get(name)
        if label and label not in derived:
            derived.append(label)
    for source in model_sources:
        if source and source not in derived:
            derived.append(source)
    return derived[:6]


def run_conversation(
    db: Session,
    user: User,
    message: str,
    history: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
) -> AssistantReply:
    client = get_client()
    ctx = ToolContext(db=db, user=user)

    contents = history_to_contents(history or [])
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    )

    config = build_config(user, context)
    called: list[str] = []
    awaiting = False

    for _ in range(settings.ASSISTANT_MAX_TOOL_TURNS):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        calls = list(response.function_calls or [])
        if not calls:
            text = extract_text(response)
            if not text:
                raise AssistantUnavailable("The assistant returned an empty response")
            db.rollback()
            return AssistantReply(
                reply=text,
                sources=derive_sources(called, []),
                tool_calls=called,
            )

        finals = [c for c in calls if c.name == "final_answer"]
        if finals:
            args = dict(finals[0].args or {})
            if ctx.mutations:
                db.commit()
            else:
                db.rollback()
            return AssistantReply(
                reply=str(args.get("reply") or "").strip()
                or "I could not put an answer together for that one.",
                is_refusal=bool(args.get("is_refusal")),
                refusal_reason=str(args.get("refusal_reason") or ""),
                sources=derive_sources(
                    called, [str(s) for s in (args.get("sources") or [])]
                ),
                follow_ups=[str(f) for f in (args.get("follow_ups") or [])][:3],
                tool_calls=called,
                mutations=ctx.mutations,
                awaiting_confirmation=awaiting,
            )

        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        response_parts: list[types.Part] = []
        for call in calls:
            name = call.name or ""
            args = dict(call.args or {})
            called.append(name)

            if name in WRITE_TOOLS and name not in permitted_writes(user):
                result: dict[str, Any] = {
                    "error": "Your role cannot make that change through the assistant"
                }
            else:
                result = run_tool(name, args, ctx)

            if result.get("status") == "confirmation_required":
                awaiting = True

            response_parts.append(
                types.Part.from_function_response(
                    name=name, response={"result": jsonable(result)}
                )
            )

        contents.append(types.Content(role="user", parts=response_parts))

    db.rollback()
    return AssistantReply(
        reply=(
            "I looked through several records but could not settle on an answer. "
            "Try narrowing the question to one class, person or date."
        ),
        sources=derive_sources(called, []),
        tool_calls=called,
    )


def available_tools(user: User) -> dict[str, list[str]]:
    return {
        "read": sorted(READ_TOOLS),
        "write": sorted(permitted_writes(user) & set(WRITE_TOOLS)),
    }
