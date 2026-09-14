from typing import Any, TypeVar

from sqlalchemy import Select, func
from sqlalchemy.orm import Session

from app.schemas.common import ListResponse, Pagination

T = TypeVar("T")


def count_for(db: Session, stmt: Select) -> int:
    return db.scalar(select_count(stmt)) or 0


def select_count(stmt: Select):
    from sqlalchemy import select

    return select(func.count()).select_from(stmt.order_by(None).subquery())


def paginate(
    db: Session,
    stmt: Select,
    page: int,
    limit: int,
    options: list[Any] | None = None,
) -> tuple[list[Any], Pagination]:
    total = count_for(db, stmt)
    query = stmt
    if options:
        query = query.options(*options)
    rows = db.scalars(query.offset((page - 1) * limit).limit(limit)).unique().all()
    return list(rows), Pagination(
        page=page,
        limit=limit,
        total=total,
        totalPages=(total + limit - 1) // limit if limit else 0,
    )


def envelope(items: list[T], pagination: Pagination) -> ListResponse[T]:
    return ListResponse(data=items, pagination=pagination)
