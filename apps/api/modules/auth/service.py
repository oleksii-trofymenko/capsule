"""Guest credentials and token pairs (ADR-014). Owns its transactions; no FastAPI imports."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth import repository
from modules.auth.tokens import TokenService, hash_secret, new_secret

# A15: security events under the pseudonymous principal id, never a credential, token or IP.
security_log = logging.getLogger("capsule.security")


class InvalidCredentialError(Exception):
    """Unknown guest credential, or one whose guest is past the retention. No detail on purpose."""


@dataclass(frozen=True)
class IssuedTokens:
    principal_id: uuid.UUID
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class NewGuest:
    tokens: IssuedTokens
    guest_credential: str


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


def _log_event(event: str, principal_id: uuid.UUID) -> None:
    security_log.info(event, extra={"event": event, "principal_id": str(principal_id)})
