import mimetypes
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO, Any
from uuid import uuid4

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

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

IMAGE_FORMATS = "jpg,png,webp"

CLOUDINARY_SIGNATURE_TTL_SECONDS = 3600


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


_configured = False


def configure() -> None:
    global _configured
    if not settings.storage_enabled:
        raise StorageNotConfigured("Cloudinary is not configured")
    if not _configured:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        _configured = True


def is_image_kind(kind: str) -> bool:
    return kind in ("image", "banner")


def resource_type_for(kind: str) -> str:
    return "image" if is_image_kind(kind) else "raw"


def resource_type_for_key(object_key: str) -> str:
    lowered = object_key.lower()
    if any(lowered.endswith(ext) for ext in DOCUMENT_CONTENT_TYPES.values()):
        return "raw"
    return "image"


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
    key = f"{prefix}/{stamp}/{uuid4().hex}"
    folder = settings.CLOUDINARY_FOLDER.strip("/")
    if folder:
        key = f"{folder}/{key}"
    if resource_type_for(kind) == "raw":
        key += extension_for(content_type, filename)
    return key


def public_url_for(object_key: str, resource_type: str | None = None) -> str:
    configure()
    resource_type = resource_type or resource_type_for_key(object_key)
    options: dict[str, Any] = {
        "resource_type": resource_type,
        "type": "upload",
        "secure": True,
    }
    if resource_type == "image":
        options["fetch_format"] = "auto"
        options["quality"] = "auto"
    url, _ = cloudinary.utils.cloudinary_url(object_key, **options)
    return url


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
    allowed = IMAGE_CONTENT_TYPES if is_image_kind(kind) else DOCUMENT_CONTENT_TYPES
    assert_allowed(content_type, allowed)

    if size_bytes is not None and size_bytes > settings.UPLOAD_MAX_BYTES:
        raise StorageError("File exceeds the maximum allowed size")

    configure()
    object_key = build_object_key(kind, content_type, filename)
    resource_type = resource_type_for(kind)

    options: dict[str, Any] = {
        "public_id": object_key,
        "resource_type": resource_type,
        "overwrite": False,
    }
    if resource_type == "image":
        options["allowed_formats"] = IMAGE_FORMATS.split(",")

    try:
        result = cloudinary.uploader.upload(fileobj, **options)
    except Exception as exc:
        raise StorageError("Could not upload the file to storage") from exc

    stored_key = result.get("public_id", object_key)
    return StoredObject(
        object_key=stored_key,
        file_url=public_url_for(stored_key, resource_type),
        content_type=content_type,
        size_bytes=result.get("bytes", size_bytes),
    )


def create_presigned_upload(
    kind: str,
    content_type: str,
    filename: str | None = None,
    max_bytes: int | None = None,
) -> PresignedUpload:
    allowed = IMAGE_CONTENT_TYPES if is_image_kind(kind) else DOCUMENT_CONTENT_TYPES
    assert_allowed(content_type, allowed)

    configure()
    object_key = build_object_key(kind, content_type, filename)
    resource_type = resource_type_for(kind)

    params: dict[str, Any] = {
        "public_id": object_key,
        "overwrite": "false",
        "timestamp": int(time.time()),
    }
    if resource_type == "image":
        params["allowed_formats"] = IMAGE_FORMATS

    try:
        signature = cloudinary.utils.api_sign_request(
            params, settings.CLOUDINARY_API_SECRET
        )
        upload_url = cloudinary.utils.cloudinary_api_url(
            "upload", resource_type=resource_type
        )
    except Exception as exc:
        raise StorageError("Could not create an upload URL") from exc

    fields: dict[str, Any] = {
        **params,
        "api_key": settings.CLOUDINARY_API_KEY,
        "signature": signature,
    }

    return PresignedUpload(
        upload_url=upload_url,
        object_key=object_key,
        file_url=public_url_for(object_key, resource_type),
        fields=fields,
        expires_in=min(
            settings.UPLOAD_URL_EXPIRY_SECONDS, CLOUDINARY_SIGNATURE_TTL_SECONDS
        ),
    )


def delete_object(object_key: str) -> None:
    if not settings.storage_enabled or not object_key:
        return
    try:
        configure()
        cloudinary.uploader.destroy(
            object_key,
            resource_type=resource_type_for_key(object_key),
            invalidate=True,
        )
    except Exception:
        return


def ping() -> None:
    configure()
    try:
        cloudinary.api.ping()
    except Exception as exc:
        raise StorageError("Cloudinary is unreachable") from exc
