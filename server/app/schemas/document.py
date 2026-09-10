from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import DocumentKind
from app.schemas.refs import ORMModel


class DocumentOut(ORMModel):
    id: int
    user_id: int
    kind: DocumentKind
    file_url: str
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int | None = None
    uploaded_at: datetime


class DocumentCreate(BaseModel):
    kind: DocumentKind
    file_url: str = Field(min_length=1, max_length=512)
    object_key: str = Field(min_length=1, max_length=512)
    original_filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)
