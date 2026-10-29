"""FastAPI dependencies: the token service, the auth service and the current principal."""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from core.db import get_session
from core.deletion_ledger import DeletionLedger
from modules.auth import repository
from modules.auth.activity import record_activity
from modules.auth.hashing import PasswordHashing
from modules.auth.service import AuthService
from modules.auth.tokens import MAX_ACCESS_TOKEN_LENGTH, InvalidTokenError, Kind, TokenService


@dataclass(frozen=True)
class Principal:
    id: uuid.UUID
    kind: Kind


def unauthorized() -> HTTPException:
    """The one 401 for every credential or token failure (R5): no detail."""
    return HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


def get_token_service(request: Request) -> TokenService:
    tokens: TokenService = request.app.state.tokens
    return tokens


def get_auth_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> AuthService:
    settings: Settings = request.app.state.settings
    passwords: PasswordHashing = request.app.state.password_hashing
    ledger: DeletionLedger = request.app.state.deletion_ledger
    return AuthService(session, tokens, settings.guest_retention_days, passwords, ledger)


async def current_principal(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> Principal:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > MAX_ACCESS_TOKEN_LENGTH:
        raise unauthorized()  # an oversized token is refused before any parsing
    try:
        claims = tokens.verify_access(token)
    except InvalidTokenError:
        raise unauthorized() from None
    # ADR-014: the row decides; the `kind` claim is never trusted, and no row means 401.
    kind = await repository.principal_kind(session, claims.principal_id)
    await session.rollback()  # end the read; the request holds no transaction open
    if kind is None:
        raise unauthorized()
    record_activity(request, claims.principal_id)
    return Principal(claims.principal_id, kind)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]
