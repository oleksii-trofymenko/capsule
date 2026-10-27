"""Opaque secrets and HS256 access tokens (ADR-014, ADR-023).

Every verification failure raises the same `InvalidTokenError`, with no reason attached (R5).
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, get_args

import jwt

from core.config import Settings

Kind = Literal["guest", "account"]

ACCESS_TOKEN_TTL = timedelta(minutes=10)
ISSUER = "capsule-api"
AUDIENCE = "capsule-mobile"
TOKEN_TYPE = "at+jwt"  # noqa: S105 - the JWT `typ` header, not a secret
ALGORITHM = "HS256"  # the only one, fixed in code (ADR-014)
REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub", "kind", "jti"]


class InvalidTokenError(Exception):
    """Any reason an access token is not accepted. Deliberately carries no detail."""


def new_secret() -> str:
    """256 random bits, base64url: a guest credential or a refresh token."""
    return secrets.token_urlsafe(32)


def hash_secret(raw: str) -> bytes:
    """The only form in which a secret is stored (A4)."""
    return hashlib.sha256(raw.encode()).digest()


@dataclass(frozen=True)
class AccessClaims:
    principal_id: uuid.UUID
    kind: Kind


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_access(self, principal_id: uuid.UUID, kind: Kind, now: datetime | None = None) -> str:
        signing = self._settings.signing_key  # ConfigError when there is no key
        issued = now or datetime.now(UTC)
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": str(principal_id),
            "kind": kind,
            "iat": issued,
            "exp": issued + ACCESS_TOKEN_TTL,
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(
            claims,
            signing.key.get_secret_value(),
            algorithm=ALGORITHM,
            headers={"kid": signing.kid, "typ": TOKEN_TYPE},
        )

    def verify_access(self, token: str) -> AccessClaims:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            raise InvalidTokenError from None
        kid = header.get("kid")
        if header.get("typ") != TOKEN_TYPE or not isinstance(kid, str):
            raise InvalidTokenError
        key = self._settings.verification_key(kid)
        if key is None:
            raise InvalidTokenError
        try:
            claims = jwt.decode(
                token,
                key.get_secret_value(),
                algorithms=[ALGORITHM],
                audience=AUDIENCE,
                issuer=ISSUER,
                leeway=0,
                options={"require": REQUIRED_CLAIMS},
            )
            principal_id = uuid.UUID(claims["sub"])
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
            raise InvalidTokenError from None
        kind = claims["kind"]
        if kind not in get_args(Kind):
            raise InvalidTokenError
        return AccessClaims(principal_id, kind)
