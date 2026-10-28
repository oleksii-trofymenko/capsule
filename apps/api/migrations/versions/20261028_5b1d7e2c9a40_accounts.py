"""auth: accounts with an email and a password hash (ADR-014, ADR-022, E1-07).

Personal data (docs/security.md §6): `email` (normalised) and `age_confirmed_at` are personal
and never logged; `password_hash` is credential material (argon2id, never logged or returned).
No birth date is stored, only the time the user confirmed they are 18 or older. The row is
deleted with its principal (E1-09 delete handler).

Revision ID: 5b1d7e2c9a40
Revises: 0760be3a898f
Create Date: 2026-10-28 15:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5b1d7e2c9a40"
down_revision: str | Sequence[str] | None = "0760be3a898f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The email is stored already normalised (modules/auth/rules.py), so a plain unique index serves
# the check before insert and the sign-in lookup. The constraint is the backstop for two
# concurrent sign-ups; its name is what the service matches, never the error text (ADR-022).
UPGRADE = """
CREATE TABLE accounts (
    principal_id uuid PRIMARY KEY REFERENCES principals (id) ON DELETE CASCADE,
    email text NOT NULL CONSTRAINT accounts_email_key UNIQUE
        CONSTRAINT accounts_email_length_check CHECK (char_length(email) <= 254),
    password_hash text NOT NULL,
    age_confirmed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
)
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("DROP TABLE accounts")
