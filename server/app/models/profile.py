from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    programme_id: Mapped[int | None] = mapped_column(
        ForeignKey("programmes.id", ondelete="RESTRICT"), nullable=True
    )
    student_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    year_of_study: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    user: Mapped["User"] = relationship(back_populates="student_profile")
    programme: Mapped["Programme | None"] = relationship(back_populates="student_profiles")


class StaffProfile(Base, TimestampMixin):
    __tablename__ = "staff_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True
    )
    staff_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specialization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="staff_profile")
    department: Mapped["Department | None"] = relationship(back_populates="staff_profiles")
