"""expand user roles and account fields

Revision ID: a1f4c2d7e8b3
Revises: 7a446b08281e
Create Date: 2026-09-10 09:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1f4c2d7e8b3"
down_revision: Union[str, Sequence[str], None] = "7a446b08281e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_ROLES = ("student", "lecturer", "tutor", "admin", "technical")
OLD_ROLES = ("student", "teacher", "admin")


def upgrade() -> None:
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    postgresql.ENUM(*NEW_ROLES, name="user_role").create(op.get_bind())
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        "USING (CASE WHEN role::text = 'teacher' THEN 'lecturer' "
        "ELSE role::text END)::user_role"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'student'")
    op.execute("DROP TYPE user_role_old")

    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.execute("UPDATE users SET username = split_part(email, '@', 1)")
    op.execute(
        "UPDATE users u SET username = u.username || '_' || u.id::text "
        "WHERE EXISTS (SELECT 1 FROM users x WHERE x.username = u.username AND x.id < u.id)"
    )
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("address", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("emergency_contact_name", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users", sa.Column("emergency_contact_phone", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "is_active")
    op.drop_column("users", "emergency_contact_phone")
    op.drop_column("users", "emergency_contact_name")
    op.drop_column("users", "address")
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "phone")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "username")

    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    postgresql.ENUM(*OLD_ROLES, name="user_role").create(op.get_bind())
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        "USING (CASE WHEN role::text IN ('lecturer', 'tutor') THEN 'teacher' "
        "WHEN role::text = 'technical' THEN 'admin' "
        "ELSE role::text END)::user_role"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'student'")
    op.execute("DROP TYPE user_role_new")
