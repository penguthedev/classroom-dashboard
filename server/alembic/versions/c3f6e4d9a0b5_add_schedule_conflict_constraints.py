"""add schedule conflict constraints

Revision ID: c3f6e4d9a0b5
Revises: b2e5d3c8f9a4
Create Date: 2026-09-10 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3f6e4d9a0b5"
down_revision: Union[str, Sequence[str], None] = "b2e5d3c8f9a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTIVE = "status IN ('scheduled', 'rescheduled')"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute(
        f"""
        ALTER TABLE schedules ADD CONSTRAINT ex_schedule_room_overlap
        EXCLUDE USING gist (
            room_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        ) WHERE ({ACTIVE})
        """
    )
    op.execute(
        f"""
        ALTER TABLE schedules ADD CONSTRAINT ex_schedule_lecturer_overlap
        EXCLUDE USING gist (
            lecturer_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        ) WHERE ({ACTIVE})
        """
    )
    op.execute(
        f"""
        ALTER TABLE schedules ADD CONSTRAINT ex_schedule_tutor_overlap
        EXCLUDE USING gist (
            tutor_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        ) WHERE ({ACTIVE} AND tutor_id IS NOT NULL)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE schedules DROP CONSTRAINT ex_schedule_tutor_overlap")
    op.execute("ALTER TABLE schedules DROP CONSTRAINT ex_schedule_lecturer_overlap")
    op.execute("ALTER TABLE schedules DROP CONSTRAINT ex_schedule_room_overlap")
