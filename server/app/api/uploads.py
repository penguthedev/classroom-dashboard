from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.storage import (
    StorageError,
    StorageNotConfigured,
    create_presigned_upload,
    upload_fileobj,
)
from app.models import User
from app.schemas.common import SingleResponse
from app.schemas.enums import PRIVILEGED_ROLES, TEACHING_ROLES, to_api_role
from app.schemas.upload import PresignOut, PresignRequest, UploadOut

router = APIRouter()

BANNER_ROLES = TEACHING_ROLES + PRIVILEGED_ROLES


def assert_storage_ready() -> None:
    if not settings.storage_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured on this server",
        )


def assert_kind_allowed(current_user: User, kind: str) -> None:
    if kind == "banner" and to_api_role(current_user.role) not in BANNER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teaching staff and administrators can upload class banners",
        )


@router.post("/presign", response_model=SingleResponse[PresignOut])
def presign(payload: PresignRequest, current_user: CurrentUser):
    assert_kind_allowed(current_user, payload.kind)
    assert_storage_ready()
    try:
        result = create_presigned_upload(
            payload.kind, payload.content_type, payload.filename
        )
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SingleResponse[PresignOut](
        data=PresignOut(
            upload_url=result.upload_url,
            object_key=result.object_key,
            file_url=result.file_url,
            fields=result.fields,
            expires_in=result.expires_in,
        )
    )


@router.post(
    "", response_model=SingleResponse[UploadOut], status_code=status.HTTP_201_CREATED
)
def direct_upload(
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    kind: Annotated[str, Form()] = "document",
):
    assert_kind_allowed(current_user, kind)
    assert_storage_ready()
    if not file.filename:
        raise HTTPException(status_code=422, detail="A file is required")

    try:
        stored = upload_fileobj(
            file.file,
            kind,
            file.content_type or "application/octet-stream",
            filename=file.filename,
            size_bytes=getattr(file, "size", None),
        )
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SingleResponse[UploadOut](
        data=UploadOut(
            object_key=stored.object_key,
            file_url=stored.file_url,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            original_filename=file.filename,
        )
    )
