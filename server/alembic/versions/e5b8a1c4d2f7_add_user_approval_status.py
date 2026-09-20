"""add is_approved to users

Revision ID: e5b8a1c4d2f7
Revises: d4a7f5e0b1c6
Create Date: 2026-09-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b8a1c4d2f7"
down_revision: Union[str, Sequence[str], None] = "d4a7f5e0b1c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_approved", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )
    # Accounts created before this feature existed were already usable —
    # keep them that way. Only new registrations for non-admin roles start
    # out unapproved (see app/api/auth.py::build_user).
    op.execute("UPDATE users SET is_approved = true")
    # Newly registered student/lecturer/tutor/technical accounts should
    # default to pending until an admin approves them, going forward the
    # application always sets this explicitly on insert, so the column
    # default just protects any row inserted outside that code path.


def downgrade() -> None:
    op.drop_column("users", "is_approved")
