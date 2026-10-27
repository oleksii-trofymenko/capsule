"""auth: principals, guest credentials, refresh families and tokens (ADR-014, ADR-022).

Personal data (docs/security.md §6): `principals.id` is pseudonymous; kind and timestamps are
linked to a person. Credential and token columns hold SHA-256 hashes only, never raw values (A4).
No IP, device id, email or analytics id is stored.

Revision ID: 0760be3a898f
Revises: 483e20606fa1
Create Date: 2026-10-27 18:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0760be3a898f"
down_revision: str | Sequence[str] | None = "483e20606fa1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = (
    """
    CREATE TABLE principals (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        kind text NOT NULL CONSTRAINT principals_kind_check CHECK (kind IN ('guest', 'account')),
        created_at timestamptz NOT NULL DEFAULT now(),
        last_activity_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE guest_credentials (
        principal_id uuid PRIMARY KEY REFERENCES principals (id) ON DELETE CASCADE,
        credential_hash bytea NOT NULL CONSTRAINT guest_credentials_hash_key UNIQUE
            CONSTRAINT guest_credentials_hash_check CHECK (octet_length(credential_hash) = 32),
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE refresh_families (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        principal_id uuid NOT NULL REFERENCES principals (id) ON DELETE CASCADE,
        created_at timestamptz NOT NULL DEFAULT now(),
        last_refreshed_at timestamptz NOT NULL DEFAULT now(),
        revoked_at timestamptz
    )
    """,
    "CREATE INDEX refresh_families_principal_id_idx ON refresh_families (principal_id)",
    """
    CREATE TABLE refresh_tokens (
        token_hash bytea PRIMARY KEY
            CONSTRAINT refresh_tokens_hash_check CHECK (octet_length(token_hash) = 32),
        family_id uuid NOT NULL REFERENCES refresh_families (id) ON DELETE CASCADE,
        state text NOT NULL
            CONSTRAINT refresh_tokens_state_check
            CHECK (state IN ('current', 'rotated', 'superseded')),
        created_at timestamptz NOT NULL DEFAULT now(),
        rotated_at timestamptz,
        grace_used_at timestamptz,
        successor_hash bytea
            CONSTRAINT refresh_tokens_successor_hash_check
            CHECK (successor_hash IS NULL OR octet_length(successor_hash) = 32),
        CONSTRAINT refresh_tokens_rotated_check
            CHECK (state <> 'rotated' OR (rotated_at IS NOT NULL AND successor_hash IS NOT NULL))
    )
    """,
    "CREATE INDEX refresh_tokens_family_id_idx ON refresh_tokens (family_id)",
    """
    CREATE UNIQUE INDEX refresh_tokens_one_current_idx
        ON refresh_tokens (family_id) WHERE state = 'current'
    """,
)


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for table in ("refresh_tokens", "refresh_families", "guest_credentials", "principals"):
        op.execute(f"DROP TABLE {table}")
