from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculties.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    faculty: Mapped["Faculty"] = relationship(back_populates="departments")
    subjects: Mapped[list["Subject"]] = relationship(back_populates="department")
    programmes: Mapped[list["Programme"]] = relationship(back_populates="department")
    staff_profiles: Mapped[list["StaffProfile"]] = relationship(back_populates="department")
