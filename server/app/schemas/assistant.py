from typing import Any

from pydantic import BaseModel, Field


class ChatHistoryEntry(BaseModel):
    sender: str = Field(pattern=r"^(user|assistant|ai|model)$")
    text: str = Field(max_length=8000)


class ScreenContext(BaseModel):
    route: str | None = Field(default=None, max_length=300)
    title: str | None = Field(default=None, max_length=300)
    resource: str | None = Field(default=None, max_length=100)
    filters: dict[str, Any] | None = None
    pagination: dict[str, Any] | None = None
    records: list[str] | None = Field(default=None, max_length=40)
    selection: str | None = Field(default=None, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatHistoryEntry] = Field(default_factory=list, max_length=40)
    context: ScreenContext | None = None


class ChatMutation(BaseModel):
    action: str
    resource: str
    id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    isRefusal: bool = False
    refusalReason: str = ""
    relevantSources: list[str] = Field(default_factory=list)
    suggestedFollowUps: list[str] = Field(default_factory=list)
    toolCalls: list[str] = Field(default_factory=list)
    mutations: list[ChatMutation] = Field(default_factory=list)
    awaitingConfirmation: bool = False


class AssistantStatus(BaseModel):
    enabled: bool
    model: str
    name: str
    institution: str
    role: str
    tools: dict[str, list[str]]
