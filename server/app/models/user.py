from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("student", "teacher", "admin", name="user_role"),
        nullable=False,
        server_default="student",
    )
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    classes_taught: Mapped[list["Class"]] = relationship(back_populates="teacher")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")