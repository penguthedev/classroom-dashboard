import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from google.genai.errors import ClientError, ServerError
from sqlalchemy.orm import Session

from app.ai.runtime import AssistantUnavailable, available_tools, run_conversation
from app.api.deps import CurrentUser
from app.core.config import settings
from app.db.session import get_db
from app.schemas.assistant import (
    AssistantStatus,
    ChatMutation,
    ChatRequest,
    ChatResponse,
)
from app.schemas.enums import to_api_role

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=AssistantStatus)
def assistant_status(current_user: CurrentUser):
    return AssistantStatus(
        enabled=settings.assistant_enabled,
        model=settings.GEMINI_MODEL,
        name=settings.ASSISTANT_NAME,
        institution=settings.ASSISTANT_INSTITUTION,
        role=to_api_role(current_user.role),
        tools=available_tools(current_user),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    if not settings.assistant_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is not configured on this server",
        )

    history = [
        {"sender": "user" if entry.sender == "user" else "model", "text": entry.text}
        for entry in payload.history
    ]

    try:
        result = run_conversation(
            db=db,
            user=current_user,
            message=payload.message.strip(),
            history=history,
            context=payload.context.model_dump(exclude_none=True) if payload.context else None,
        )
    except AssistantUnavailable as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ClientError as exc:
        db.rollback()
        logger.warning("Assistant upstream rejected the request: %s", exc)
        if exc.code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="The assistant is handling too many requests right now. "
                "Please wait a moment and try again.",
            ) from exc
        if exc.code == 404:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The configured assistant model is unavailable. "
                "Check GEMINI_MODEL on the server.",
            ) from exc
        if exc.code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The assistant could not authenticate. Check GEMINI_API_KEY on the server.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant could not complete that request. Please try again.",
        ) from exc
    except ServerError as exc:
        db.rollback()
        logger.warning("Assistant upstream failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Assistant conversation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant could not complete that request. Please try again.",
        ) from exc

    return ChatResponse(
        reply=result.reply,
        isRefusal=result.is_refusal,
        refusalReason=result.refusal_reason,
        relevantSources=result.sources,
        suggestedFollowUps=result.follow_ups,
        toolCalls=result.tool_calls,
        mutations=[
            ChatMutation(
                action=m["action"], resource=m["resource"], id=m.get("id")
            )
            for m in result.mutations
        ],
        awaitingConfirmation=result.awaiting_confirmation,
    )
