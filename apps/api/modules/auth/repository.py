"""SQL for the auth tables. Bound parameters only; callers own the transaction."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from modules.auth.tokens import Kind

_INSERT_PRINCIPAL = text("INSERT INTO principals (kind) VALUES (:kind) RETURNING id")
_INSERT_CREDENTIAL = text(
    "INSERT INTO guest_credentials (principal_id, credential_hash) VALUES (:principal_id, :hash)"
)
_INSERT_FAMILY = text(
    "INSERT INTO refresh_families (principal_id) VALUES (:principal_id) RETURNING id"
)
_INSERT_TOKEN = text(
    "INSERT INTO refresh_tokens (token_hash, family_id, state)"
    " VALUES (:hash, :family_id, 'current')"
)
# ADR-014: an expired guest gets the same answer as an unknown credential, even before the purge.
_FIND_ACTIVE_GUEST = text(
    """
    SELECT p.id FROM guest_credentials c JOIN principals p ON p.id = c.principal_id
    WHERE c.credential_hash = :hash AND p.kind = 'guest'
      AND p.last_activity_at >= now() - make_interval(days => :retention_days)
    """
)
_PRINCIPAL_KIND = text("SELECT kind FROM principals WHERE id = :id")
# ADR-022: at most one write per principal per hour.
_TOUCH = text(
    """
    UPDATE principals SET last_activity_at = now()
    WHERE id = :id AND last_activity_at < now() - interval '1 hour'
    """
)


async def insert_principal(session: AsyncSession, kind: Kind) -> uuid.UUID:
    principal_id: uuid.UUID = (
        await session.execute(_INSERT_PRINCIPAL, {"kind": kind})
    ).scalar_one()
    return principal_id


async def insert_guest_credential(
    session: AsyncSession, principal_id: uuid.UUID, credential_hash: bytes
) -> None:
    await session.execute(
        _INSERT_CREDENTIAL, {"principal_id": principal_id, "hash": credential_hash}
    )


async def insert_family_with_token(
    session: AsyncSession, principal_id: uuid.UUID, token_hash: bytes
) -> None:
    family_id = (await session.execute(_INSERT_FAMILY, {"principal_id": principal_id})).scalar_one()
    await session.execute(_INSERT_TOKEN, {"hash": token_hash, "family_id": family_id})


async def find_active_guest(
    session: AsyncSession, credential_hash: bytes, retention_days: int
) -> uuid.UUID | None:
    params = {"hash": credential_hash, "retention_days": retention_days}
    principal_id: uuid.UUID | None = (
        await session.execute(_FIND_ACTIVE_GUEST, params)
    ).scalar_one_or_none()
    return principal_id


async def principal_kind(session: AsyncSession, principal_id: uuid.UUID) -> Kind | None:
    kind: Kind | None = (
        await session.execute(_PRINCIPAL_KIND, {"id": principal_id})
    ).scalar_one_or_none()
    return kind


async def touch_last_activity(conn: AsyncConnection, principal_id: uuid.UUID) -> None:
    await conn.execute(_TOUCH, {"id": principal_id})
