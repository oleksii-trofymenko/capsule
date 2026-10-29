"""deletion ledger: principal id and deletion time of every deleted principal (ADR-022, E1-07b).

Personal data (docs/security.md §6): only the pseudonymous principal id, which links to nothing
once the principal is gone, and the deletion time. No foreign key: the principal row is deleted
in the same transaction. Pruned by the backup job after rotation (E1-23).

Revision ID: 9520e8e4ff72
Revises: 5b1d7e2c9a40
Create Date: 2026-10-29 10:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "9520e8e4ff72"
down_revision: str | Sequence[str] | None = "5b1d7e2c9a40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = """
CREATE TABLE deletion_ledger (
    principal_id uuid PRIMARY KEY,
    deleted_at timestamptz NOT NULL DEFAULT now()
)
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("DROP TABLE deletion_ledger")
