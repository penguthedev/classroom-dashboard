from typing import Any, Literal

from pydantic import BaseModel, Field

UploadKind = Literal["image", "document", "banner"]


class PresignRequest(BaseModel):
    kind: UploadKind
    content_type: str = Field(min_length=3, max_length=150)
    filename: str | None = Field(default=None, max_length=255)


class PresignOut(BaseModel):
    upload_url: str
    object_key: str
    file_url: str
    fields: dict[str, Any]
    expires_in: int


class UploadOut(BaseModel):
    object_key: str
    file_url: str
    content_type: str
    size_bytes: int | None = None
    original_filename: str | None = None
