from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("student", "lecturer", "tutor", "admin", "technical", name="user_role"),
        nullable=False,
        server_default="student",
    )
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    staff_profile: Mapped["StaffProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
    classes_lecturing: Mapped[list["Class"]] = relationship(
        back_populates="lecturer", foreign_keys="Class.lecturer_id"
    )
    classes_tutoring: Mapped[list["Class"]] = relationship(
        back_populates="tutor", foreign_keys="Class.tutor_id"
    )
    schedules_lecturing: Mapped[list["Schedule"]] = relationship(
        back_populates="lecturer", foreign_keys="Schedule.lecturer_id"
    )
    schedules_tutoring: Mapped[list["Schedule"]] = relationship(
        back_populates="tutor", foreign_keys="Schedule.tutor_id"
    )
