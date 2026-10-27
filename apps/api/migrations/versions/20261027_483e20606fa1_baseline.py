"""baseline: empty starting point; the first tables arrive in E1-05.

Revision ID: 483e20606fa1
Revises:
Create Date: 2026-10-27 15:51:38.277895
"""

from collections.abc import Sequence

revision: str = "483e20606fa1"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
