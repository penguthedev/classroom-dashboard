from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: Pagination


class SingleResponse(BaseModel, Generic[T]):
    data: T
