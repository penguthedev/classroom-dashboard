from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import envelope, paginate
from app.api.deps import CurrentUser, is_privileged
from app.core.storage import delete_object
from app.db.session import get_db
from app.models import Document, User
from app.schemas.common import ListResponse, SingleResponse
from app.schemas.document import DocumentCreate, DocumentOut

router = APIRouter()


@router.get("", response_model=ListResponse[DocumentOut])
def list_documents(
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: int | None = None,
    kind: str | None = None,
):
    stmt = select(Document)

    if is_privileged(current_user):
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
    else:
        stmt = stmt.where(Document.user_id == current_user.id)

    if kind:
        stmt = stmt.where(Document.kind == kind)

    rows, pagination = paginate(db, stmt.order_by(Document.id.desc()), page, limit)
    return envelope([DocumentOut.model_validate(r) for r in rows], pagination)


@router.get("/{document_id}", response_model=SingleResponse[DocumentOut])
def get_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = db.get(Document, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if row.user_id != current_user.id and not is_privileged(current_user):
        raise HTTPException(status_code=404, detail="Document not found")
    return SingleResponse[DocumentOut](data=DocumentOut.model_validate(row))


@router.post(
    "", response_model=SingleResponse[DocumentOut], status_code=status.HTTP_201_CREATED
)
def create_document(
    payload: DocumentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
    user_id: int | None = None,
):
    owner_id = current_user.id
    if user_id is not None and user_id != current_user.id:
        if not is_privileged(current_user):
            raise HTTPException(
                status_code=403,
                detail="You can only attach documents to your own account",
            )
        if db.get(User, user_id) is None:
            raise HTTPException(status_code=404, detail="User not found")
        owner_id = user_id

    row = Document(user_id=owner_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return SingleResponse[DocumentOut](data=DocumentOut.model_validate(row))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: CurrentUser,
):
    row = db.get(Document, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if row.user_id != current_user.id and not is_privileged(current_user):
        raise HTTPException(status_code=404, detail="Document not found")

    object_key = row.object_key
    db.delete(row)
    db.commit()
    delete_object(object_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
