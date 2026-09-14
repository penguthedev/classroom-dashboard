import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import IO, Any
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

IMAGE_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

DOCUMENT_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    **IMAGE_CONTENT_TYPES,
    **DOCUMENT_CONTENT_TYPES,
}

PREFIXES: dict[str, str] = {
    "image": "avatars",
    "document": "documents",
    "banner": "banners",
}


class StorageError(RuntimeError):
    pass


class StorageNotConfigured(StorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    file_url: str
    content_type: str
    size_bytes: int | None


@dataclass(frozen=True)
class PresignedUpload:
    upload_url: str
    object_key: str
    file_url: str
    fields: dict[str, Any]
    expires_in: int


@lru_cache
def get_client():
    if not settings.storage_enabled:
        raise StorageNotConfigured("Object storage is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def extension_for(content_type: str, filename: str | None) -> str:
    known = ALLOWED_CONTENT_TYPES.get(content_type)
    if known:
        return known
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return mimetypes.guess_extension(content_type) or ""


def build_object_key(kind: str, content_type: str, filename: str | None) -> str:
    prefix = PREFIXES.get(kind, "uploads")
    stamp = datetime.now(UTC).strftime("%Y/%m")
    return f"{prefix}/{stamp}/{uuid4().hex}{extension_for(content_type, filename)}"


def public_url_for(object_key: str) -> str:
    base = settings.S3_PUBLIC_URL or f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}"
    return f"{base.rstrip('/')}/{object_key}"


def assert_allowed(content_type: str, allowed: dict[str, str]) -> None:
    if content_type not in allowed:
        raise StorageError(f"Unsupported file type: {content_type}")


def upload_fileobj(
    fileobj: IO[bytes],
    kind: str,
    content_type: str,
    filename: str | None = None,
    size_bytes: int | None = None,
) -> StoredObject:
    allowed = IMAGE_CONTENT_TYPES if kind in ("image", "banner") else DOCUMENT_CONTENT_TYPES
    assert_allowed(content_type, allowed)

    if size_bytes is not None and size_bytes > settings.UPLOAD_MAX_BYTES:
        raise StorageError("File exceeds the maximum allowed size")

    object_key = build_object_key(kind, content_type, filename)
    client = get_client()
    try:
        client.upload_fileobj(
            fileobj,
            settings.S3_BUCKET,
            object_key,
            ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Could not upload the file to storage") from exc

    return StoredObject(
        object_key=object_key,
        file_url=public_url_for(object_key),
        content_type=content_type,
        size_bytes=size_bytes,
    )


def create_presigned_upload(
    kind: str,
    content_type: str,
    filename: str | None = None,
    max_bytes: int | None = None,
) -> PresignedUpload:
    allowed = IMAGE_CONTENT_TYPES if kind in ("image", "banner") else DOCUMENT_CONTENT_TYPES
    assert_allowed(content_type, allowed)

    limit = max_bytes or settings.UPLOAD_MAX_BYTES
    object_key = build_object_key(kind, content_type, filename)
    client = get_client()

    try:
        presigned = client.generate_presigned_post(
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Fields={"Content-Type": content_type, "acl": "public-read"},
            Conditions=[
                {"Content-Type": content_type},
                {"acl": "public-read"},
                ["content-length-range", 1, limit],
            ],
            ExpiresIn=settings.UPLOAD_URL_EXPIRY_SECONDS,
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageError("Could not create an upload URL") from exc

    return PresignedUpload(
        upload_url=presigned["url"],
        object_key=object_key,
        file_url=public_url_for(object_key),
        fields=presigned["fields"],
        expires_in=settings.UPLOAD_URL_EXPIRY_SECONDS,
    )


def delete_object(object_key: str) -> None:
    if not settings.storage_enabled or not object_key:
        return
    try:
        get_client().delete_object(Bucket=settings.S3_BUCKET, Key=object_key)
    except (BotoCoreError, ClientError):
        return
