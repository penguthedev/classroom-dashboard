"""add university tables

Revision ID: b2e5d3c8f9a4
Revises: a1f4c2d7e8b3
Create Date: 2026-09-10 09:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2e5d3c8f9a4"
down_revision: Union[str, Sequence[str], None] = "a1f4c2d7e8b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

room_type = postgresql.ENUM(
    "lecture_hall",
    "laboratory",
    "tutorial_room",
    "computer_lab",
    "seminar_room",
    name="room_type",
    create_type=False,
)
schedule_status = postgresql.ENUM(
    "scheduled",
    "rescheduled",
    "cancelled",
    "completed",
    name="schedule_status",
    create_type=False,
)
notification_type = postgresql.ENUM(
    "schedule_created",
    "schedule_updated",
    "schedule_cancelled",
    "enrollment",
    "system",
    name="notification_type",
    create_type=False,
)
document_kind = postgresql.ENUM(
    "enrollment_proof",
    "transcript",
    "qualification",
    "staff_verification",
    "other",
    name="document_kind",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (room_type, schedule_status, notification_type, document_kind):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "faculties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.execute(
        "INSERT INTO faculties (code, name, description) "
        "VALUES ('GEN', 'General Studies', 'Default faculty created during migration.')"
    )

    op.add_column("departments", sa.Column("faculty_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE departments SET faculty_id = (SELECT id FROM faculties WHERE code = 'GEN')"
    )
    op.alter_column("departments", "faculty_id", nullable=False)
    op.create_foreign_key(
        "fk_departments_faculty_id",
        "departments",
        "faculties",
        ["faculty_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "programmes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "duration_years", sa.Integer(), server_default=sa.text("3"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("programme_id", sa.Integer(), nullable=True),
        sa.Column("student_number", sa.String(length=50), nullable=False),
        sa.Column(
            "year_of_study", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_number"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("staff_number", sa.String(length=50), nullable=False),
        sa.Column("position", sa.String(length=100), nullable=True),
        sa.Column("specialization", sa.String(length=255), nullable=True),
        sa.Column("qualification", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("staff_number"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("capacity", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column(
            "room_type", room_type, server_default="lecture_hall", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("building_id", "code", name="uq_room_building_code"),
    )

    op.alter_column("classes", "teacher_id", new_column_name="lecturer_id")
    op.add_column("classes", sa.Column("tutor_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_classes_tutor_id", "classes", "users", ["tutor_id"], ["id"]
    )

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("lecturer_id", sa.Integer(), nullable=False),
        sa.Column("tutor_id", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", schedule_status, server_default="scheduled", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_schedule_time_order"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lecturer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_starts_at", "schedules", ["starts_at"])
    op.create_index("ix_schedules_class_id", "schedules", ["class_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=True),
        sa.Column("type", notification_type, server_default="system", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", document_kind, server_default="other", nullable=False),
        sa.Column("file_url", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.execute(
        "ALTER TABLE enrollments ALTER COLUMN enrolled_at "
        "TYPE timestamptz USING enrolled_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE enrollments ALTER COLUMN enrolled_at "
        "TYPE timestamp USING enrolled_at AT TIME ZONE 'UTC'"
    )

    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_schedules_class_id", table_name="schedules")
    op.drop_index("ix_schedules_starts_at", table_name="schedules")
    op.drop_table("schedules")

    op.drop_constraint("fk_classes_tutor_id", "classes", type_="foreignkey")
    op.drop_column("classes", "tutor_id")
    op.alter_column("classes", "lecturer_id", new_column_name="teacher_id")

    op.drop_table("rooms")
    op.drop_table("buildings")
    op.drop_table("staff_profiles")
    op.drop_table("student_profiles")
    op.drop_table("programmes")

    op.drop_constraint("fk_departments_faculty_id", "departments", type_="foreignkey")
    op.drop_column("departments", "faculty_id")
    op.drop_table("faculties")

    bind = op.get_bind()
    for enum in (document_kind, notification_type, schedule_status, room_type):
        enum.drop(bind, checkfirst=True)
