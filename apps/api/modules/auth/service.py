"""Guest credentials, accounts, token pairs, refresh rotation and logout (ADR-014).

Owns its transactions; no FastAPI imports. A password hash or verify never runs inside a
transaction: read, commit, hash, then write in a short transaction of its own.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_errors import is_lock_timeout, is_unique_violation
from core.deletion_ledger import DeletionLedger, LedgerEntry
from core.errors import ServiceBusyError
from modules.auth import repository
from modules.auth.hashing import PasswordHashing
from modules.auth.rules import MAX_PASSWORD_LENGTH, try_normalise_email
from modules.auth.tokens import Kind, TokenService, hash_secret, new_secret

# A15: security events under the pseudonymous principal id, never a credential, token or IP.
security_log = logging.getLogger("capsule.security")
logger = logging.getLogger(__name__)

Outcome = Literal["rotate", "grace", "reuse"]


class InvalidCredentialError(Exception):
    """Unknown guest credential, or one whose guest is past the retention. No detail on purpose."""


class InvalidRefreshTokenError(Exception):
    """Unknown, expired, revoked or reused refresh token. No detail on purpose (one 401)."""


class FamilyBusyError(ServiceBusyError):
    """The family stayed locked past `lock_timeout`. Nothing changed; the token is still valid.
    The app answers 503 with `Retry-After`; the client must never treat it as a logout."""

    def __init__(self) -> None:
        super().__init__(retry_after_s=1)


class GuestBusyError(ServiceBusyError):
    """The guest credential stayed locked past `lock_timeout` (another move of the same guest).
    Nothing changed: no account, no move; the app answers 503 with `Retry-After`."""

    def __init__(self) -> None:
        super().__init__(retry_after_s=1)


class EmailRegisteredError(Exception):
    """Sign-up with an email that has an account (A7). Carries nothing about the account."""


class InvalidSignInError(Exception):
    """Unknown email or wrong password. No detail on purpose (one 401, A6)."""


@dataclass(frozen=True)
class IssuedTokens:
    principal_id: uuid.UUID
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class SignedIn:
    tokens: IssuedTokens
    guest_guides_moved: int


@dataclass(frozen=True)
class _Moved:
    entry: LedgerEntry
    guides: int


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
    def __init__(
        self,
        session: AsyncSession,
        tokens: TokenService,
        retention_days: int,
        passwords: PasswordHashing,
        ledger: DeletionLedger,
    ) -> None:
        self._session = session
        self._tokens = tokens
        self._retention_days = retention_days
        self._passwords = passwords
        self._ledger = ledger

    async def create_guest(self) -> NewGuest:
        credential = new_secret()
        async with self._session.begin():
            principal_id = await repository.insert_principal(self._session, "guest")
            await repository.insert_guest_credential(
                self._session, principal_id, hash_secret(credential)
            )
            tokens = await self._new_family(principal_id, "guest")
        _log_event("guest_created", principal_id)
        return NewGuest(tokens, credential)

    async def sign_in_guest(self, credential: str) -> IssuedTokens:
        async with self._session.begin():
            principal_id = await repository.find_active_guest(
                self._session, hash_secret(credential), self._retention_days
            )
            if principal_id is None:
                raise InvalidCredentialError
            tokens = await self._new_family(principal_id, "guest")
        _log_event("guest_signed_in", principal_id)
        return tokens

    async def sign_up(
        self, email: str, password: str, guest_credential: str | None = None
    ) -> SignedIn:
        """`email` and `password` come normalised and checked (`SignUpRequest`). The A7 conflict
        comes from the check before the insert; the unique constraint is only the backstop.
        A guest credential moves its guest in the transaction that creates the account."""
        async with self._session.begin():
            registered = await repository.find_account(self._session, email) is not None
        if registered:
            raise EmailRegisteredError
        password_hash = await self._passwords.hash(password)  # no transaction open
        try:
            async with self._session.begin():
                guest_id = await self._lock_guest(guest_credential)
                principal_id = await repository.insert_principal(self._session, "account")
                await repository.insert_account(self._session, principal_id, email, password_hash)
                tokens = await self._new_family(principal_id, "account")
                moved = await self._move_guest(guest_id, principal_id)
        except IntegrityError as exc:
            # Matched by constraint name; the error text quotes the email and is never used.
            if is_unique_violation(exc, repository.ACCOUNTS_EMAIL_KEY):
                raise EmailRegisteredError from None
            raise
        except DBAPIError as exc:
            _raise_if_guest_busy(exc)
            raise
        _log_event("account_created", principal_id)
        return await self._after_move(tokens, moved)

    async def sign_in(
        self, email: str, password: str, guest_credential: str | None = None
    ) -> SignedIn:
        """`password` comes in NFC (`SignInRequest`). An unknown or invalid email runs the same
        lookup and a verify against the dummy hash, so it costs what a wrong password costs.
        A guest credential moves its guest only after the password is verified."""
        if len(password) > MAX_PASSWORD_LENGTH:  # no account can have it: refused before a hash
            _log_event("sign_in_failed", None)
            raise InvalidSignInError
        # An invalid address looks up "", which no account has: the same query either way.
        lookup = try_normalise_email(email) or ""
        async with self._session.begin():
            account = await repository.find_account(self._session, lookup)
        stored = None if account is None else account.password_hash
        verified = await self._passwords.verify(stored, password)  # no transaction open
        if account is None or not verified.ok:
            _log_event("sign_in_failed", None if account is None else account.principal_id)
            raise InvalidSignInError
        rehashed = False
        try:
            async with self._session.begin():
                guest_id = await self._lock_guest(guest_credential)
                if verified.rehashed is not None:
                    rehashed = await repository.replace_password_hash(
                        self._session,
                        account.principal_id,
                        account.password_hash,
                        verified.rehashed,
                    )
                tokens = await self._new_family(account.principal_id, "account")
                moved = await self._move_guest(guest_id, account.principal_id)
        except DBAPIError as exc:
            _raise_if_guest_busy(exc)
            raise
        _log_event("signed_in", account.principal_id)
        if rehashed:
            _log_event("password_rehashed", account.principal_id)
        return await self._after_move(tokens, moved)

    async def _lock_guest(self, credential: str | None) -> uuid.UUID | None:
        """First in the transaction (lock order: credential, then principals). `lock_timeout`
        bounds the credential lock only; every later wait (the email's unique index, a rehash)
        is as without a credential."""
        if credential is None:
            return None
        await repository.set_lock_timeout(self._session)
        guest_id = await repository.lock_active_guest(
            self._session, hash_secret(credential), self._retention_days
        )
        await repository.default_lock_timeout(self._session)
        return guest_id

    async def _move_guest(self, guest_id: uuid.UUID | None, account_id: uuid.UUID) -> _Moved | None:
        """ADR-014: move the rows, delete the guest, write the ledger row, all in the caller's
        transaction. Found only by the locked credential, never by email, device or analytics id.
        """
        if guest_id is None:
            return None
        guides = await repository.move_guest_data(self._session, guest_id, account_id)
        await repository.delete_guest(self._session, guest_id)
        entry = await self._ledger.record(self._session, guest_id)
        return _Moved(entry, guides)

    async def _after_move(self, tokens: IssuedTokens, moved: _Moved | None) -> SignedIn:
        """After commit: the A15 event under the account's id, then the ledger file. The event
        goes first, so a cancelled append cannot drop it."""
        if moved is None:
            return SignedIn(tokens, 0)
        _log_event("guest_data_moved", tokens.principal_id, count=moved.guides)
        await self._ledger.append(moved.entry)  # raises only when cancelled
        return SignedIn(tokens, moved.guides)

    async def _new_family(self, principal_id: uuid.UUID, kind: Kind) -> IssuedTokens:
        refresh_token = new_secret()
        await repository.insert_family_with_token(
            self._session, principal_id, hash_secret(refresh_token)
        )
        access_token = self._tokens.issue_access(principal_id, kind)
        return IssuedTokens(principal_id, access_token, refresh_token)

    async def refresh(self, refresh_token: str) -> IssuedTokens:
        """Rotate under the family lock (ADR-014). A reuse commits the revocation, then raises."""
        try:
            async with self._session.begin():
                result = await self._refresh_locked(hash_secret(refresh_token))
        except DBAPIError as exc:
            if is_lock_timeout(exc):
                logger.warning("refresh: refresh family busy")
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
                logger.warning("logout: refresh family busy")
                raise FamilyBusyError from None
            raise
        if revoked is None:
            return
        if revoked.presented_state == "current":
            _log_event("family_revoked", revoked.principal_id, reason="logout")
        else:
            _log_reuse(revoked.principal_id)


def _raise_if_guest_busy(exc: DBAPIError) -> None:
    if is_lock_timeout(exc):
        logger.warning("guest move: guest credential busy")
        raise GuestBusyError from None


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


def _log_event(
    event: str,
    principal_id: uuid.UUID | None,
    reason: str | None = None,
    count: int | None = None,
) -> None:
    """A15. A failed sign-in with an unknown email has no principal id to log."""
    extra: dict[str, str | int] = {"event": event}
    if principal_id is not None:
        extra["principal_id"] = str(principal_id)
    if reason is not None:
        extra["reason"] = reason
    if count is not None:
        extra["count"] = count
    security_log.info(event, extra=extra)
