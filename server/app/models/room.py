from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("building_id", "code", name="uq_room_building_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    room_type: Mapped[str] = mapped_column(
        Enum(
            "lecture_hall",
            "laboratory",
            "tutorial_room",
            "computer_lab",
            "seminar_room",
            name="room_type",
        ),
        nullable=False,
        server_default="lecture_hall",
    )

    building: Mapped["Building"] = relationship(back_populates="rooms")
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="room")
