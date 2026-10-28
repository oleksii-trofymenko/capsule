"""Guest credentials, token pairs, refresh rotation and logout (ADR-014).

Owns its transactions; no FastAPI imports.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_errors import is_lock_timeout
from modules.auth import repository
from modules.auth.tokens import TokenService, hash_secret, new_secret

# A15: security events under the pseudonymous principal id, never a credential, token or IP.
security_log = logging.getLogger("capsule.security")

Outcome = Literal["rotate", "grace", "reuse"]


class InvalidCredentialError(Exception):
    """Unknown guest credential, or one whose guest is past the retention. No detail on purpose."""


class InvalidRefreshTokenError(Exception):
    """Unknown, expired, revoked or reused refresh token. No detail on purpose (one 401)."""


class FamilyBusyError(Exception):
    """The family stayed locked past `lock_timeout`. Nothing changed; the token is still valid."""


@dataclass(frozen=True)
class IssuedTokens:
    principal_id: uuid.UUID
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class NewGuest:
    tokens: IssuedTokens
    guest_credential: str


@dataclass(frozen=True)
class _Rotated:
    tokens: IssuedTokens
    grace: bool


@dataclass(frozen=True)
class _Reused:
    principal_id: uuid.UUID


class AuthService:
    def __init__(self, session: AsyncSession, tokens: TokenService, retention_days: int) -> None:
        self._session = session
        self._tokens = tokens
        self._retention_days = retention_days

    async def create_guest(self) -> NewGuest:
        credential = new_secret()
        async with self._session.begin():
            principal_id = await repository.insert_principal(self._session, "guest")
            await repository.insert_guest_credential(
                self._session, principal_id, hash_secret(credential)
            )
            tokens = await self._new_family(principal_id)
        _log_event("guest_created", principal_id)
        return NewGuest(tokens, credential)

    async def sign_in_guest(self, credential: str) -> IssuedTokens:
        async with self._session.begin():
            principal_id = await repository.find_active_guest(
                self._session, hash_secret(credential), self._retention_days
            )
            if principal_id is None:
                raise InvalidCredentialError
            tokens = await self._new_family(principal_id)
        _log_event("guest_signed_in", principal_id)
        return tokens

    async def _new_family(self, principal_id: uuid.UUID) -> IssuedTokens:
        refresh_token = new_secret()
        await repository.insert_family_with_token(
            self._session, principal_id, hash_secret(refresh_token)
        )
        access_token = self._tokens.issue_access(principal_id, "guest")
        return IssuedTokens(principal_id, access_token, refresh_token)

    async def refresh(self, refresh_token: str) -> IssuedTokens:
        """Rotate under the family lock (ADR-014). A reuse commits the revocation, then raises."""
        try:
            async with self._session.begin():
                result = await self._refresh_locked(hash_secret(refresh_token))
        except DBAPIError as exc:
            if is_lock_timeout(exc):
                raise FamilyBusyError from None
            raise
        # Logged after commit: the revocation holds before the 401 is sent.
        if isinstance(result, _Reused):
            _log_reuse(result.principal_id)
            raise InvalidRefreshTokenError
        if result.grace:
            _log_event("grace_used", result.tokens.principal_id)
        return result.tokens

    async def _refresh_locked(self, presented: bytes) -> _Rotated | _Reused:
        await repository.set_lock_timeout(self._session)
        family = await repository.lock_live_family(self._session, presented, self._retention_days)
        if family is None:  # unknown, revoked, expired or past retention: nothing changes
            raise InvalidRefreshTokenError
        token = await repository.token_state(self._session, presented)
        if token is None:
            raise InvalidRefreshTokenError
        outcome = decide(token)
        if outcome == "reuse":
            await repository.revoke_family(self._session, family.id)
            return _Reused(family.principal_id)
        successor = new_secret()
        if outcome == "rotate":
            await repository.rotate_token(self._session, presented, hash_secret(successor))
        else:
            await repository.use_grace(self._session, presented, family.id, hash_secret(successor))
        await repository.insert_current_token(self._session, family.id, hash_secret(successor))
        # Inside the transaction: if signing fails, the rotation rolls back.
        access_token = self._tokens.issue_access(family.principal_id, family.kind)
        tokens = IssuedTokens(family.principal_id, access_token, successor)
        return _Rotated(tokens, grace=outcome == "grace")

    async def logout(self, refresh_token: str) -> None:
        """Revoke the family of any known token of a live family. A used (rotated or superseded)
        token still revokes, but is logged as reuse (A15). Unknown tokens and revoked families
        change nothing and log nothing."""
        try:
            async with self._session.begin():
                await repository.set_lock_timeout(self._session)
                revoked = await repository.revoke_family_of(
                    self._session, hash_secret(refresh_token)
                )
        except DBAPIError as exc:
            if is_lock_timeout(exc):
                raise FamilyBusyError from None
            raise
        if revoked is None:
            return
        if revoked.presented_state == "current":
            _log_event("family_revoked", revoked.principal_id, reason="logout")
        else:
            _log_reuse(revoked.principal_id)


def _log_reuse(principal_id: uuid.UUID) -> None:
    _log_event("reuse_detected", principal_id)
    _log_event("family_revoked", principal_id, reason="reuse")


def decide(token: repository.TokenState) -> Outcome:
    """The ADR-014 state machine for a known token of a live family, read under its lock."""
    if token.state == "current":
        return "rotate"
    if (
        token.state == "rotated"
        and token.in_grace_window
        and not token.grace_used
        and token.successor_state == "current"
    ):
        return "grace"
    return "reuse"


def _log_event(event: str, principal_id: uuid.UUID, reason: str | None = None) -> None:
    extra = {"event": event, "principal_id": str(principal_id)}
    if reason is not None:
        extra["reason"] = reason
    security_log.info(event, extra=extra)
