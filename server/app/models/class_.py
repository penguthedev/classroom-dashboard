from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Class(Base, TimestampMixin):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "archived", name="class_status"),
        nullable=False,
        server_default="active",
    )
    banner_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    banner_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invite_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    subject: Mapped["Subject"] = relationship(back_populates="classes")
    lecturer: Mapped["User"] = relationship(
        back_populates="classes_lecturing", foreign_keys=[lecturer_id]
    )
    tutor: Mapped["User | None"] = relationship(
        back_populates="classes_tutoring", foreign_keys=[tutor_id]
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="class_")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="class_")
