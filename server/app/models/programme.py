from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Programme(Base, TimestampMixin):
    __tablename__ = "programmes"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")

    department: Mapped["Department"] = relationship(back_populates="programmes")
    student_profiles: Mapped[list["StudentProfile"]] = relationship(back_populates="programme")
