from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_schedule_time_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False
    )
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("scheduled", "rescheduled", "cancelled", "completed", name="schedule_status"),
        nullable=False,
        server_default="scheduled",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    class_: Mapped["Class"] = relationship(back_populates="schedules")
    room: Mapped["Room"] = relationship(back_populates="schedules")
    lecturer: Mapped["User"] = relationship(
        back_populates="schedules_lecturing", foreign_keys=[lecturer_id]
    )
    tutor: Mapped["User | None"] = relationship(
        back_populates="schedules_tutoring", foreign_keys=[tutor_id]
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="schedule")
