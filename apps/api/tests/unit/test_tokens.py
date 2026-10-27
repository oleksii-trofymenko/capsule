"""Access-token issue and verify (ADR-014, ADR-023), and R5: every bad token fails the same way."""

import base64
import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from pydantic import SecretBytes

from core.config import ConfigError, SigningKey
from modules.auth.tokens import (
    AccessClaims,
    InvalidTokenError,
    TokenService,
    hash_secret,
    new_secret,
)
from tests.support import TEST_SIGNING_KEYS, dummy_settings

KID = TEST_SIGNING_KEYS[0].kid
KEY = TEST_SIGNING_KEYS[0].key.get_secret_value()
OTHER_KEY = bytes(range(32, 64))
# Not a real key: R5 only needs PEM-shaped text used as an HMAC secret.
FAKE_PEM_PUBLIC_KEY = (
    b"-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE\n-----END PUBLIC KEY-----\n"
)
PRINCIPAL = uuid.UUID("0b8e2f4c-3d1a-4f5e-9a7b-6c5d4e3f2a1b")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def forge(
    header: dict[str, Any] | None = None,
    claims: dict[str, Any] | None = None,
    key: bytes = KEY,
    digest: Callable[..., Any] = hashlib.sha256,
) -> str:
    """A token built by hand: any header, any claims, an HMAC signature under any key."""
    header = {"alg": "HS256", "kid": KID, "typ": "at+jwt"} if header is None else header
    signing_input = (
        f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims or valid_claims()).encode())}"
    )
    signature = hmac.new(key, signing_input.encode(), digest).digest()
    return f"{signing_input}.{_b64(signature)}"


def valid_claims(**overrides: object) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": "capsule-api",
        "aud": "capsule-mobile",
        "sub": str(PRINCIPAL),
        "kind": "guest",
        "iat": now,
        "exp": now + 600,
        "jti": uuid.uuid4().hex,
    }
    return {k: v for k, v in (claims | overrides).items() if v is not None}


def without(claims: dict[str, Any], name: str) -> dict[str, Any]:
    return {k: v for k, v in claims.items() if k != name}


def service() -> TokenService:
    return TokenService(dummy_settings())


def test_issued_token_verifies_and_carries_the_adr_014_header_and_claims() -> None:
    token = service().issue_access(PRINCIPAL, "account")

    assert service().verify_access(token) == AccessClaims(PRINCIPAL, "account")
    assert jwt.get_unverified_header(token) == {"alg": "HS256", "kid": KID, "typ": "at+jwt"}
    claims = jwt.decode(token, options={"verify_signature": False})
    assert set(claims) == {"iss", "aud", "sub", "kind", "iat", "exp", "jti"}
    assert claims["exp"] - claims["iat"] == 600


def test_previous_key_still_verifies_and_the_first_key_signs() -> None:
    old = SigningKey("2025-12-01", SecretBytes(OTHER_KEY))
    rotated = TokenService(dummy_settings(signing_keys=(TEST_SIGNING_KEYS[0], old)))
    old_token = forge({"alg": "HS256", "kid": old.kid, "typ": "at+jwt"}, key=OTHER_KEY)

    assert rotated.verify_access(old_token).principal_id == PRINCIPAL
    assert jwt.get_unverified_header(rotated.issue_access(PRINCIPAL, "guest"))["kid"] == KID


def test_issuing_without_a_signing_key_fails_closed() -> None:
    with pytest.raises(ConfigError):
        TokenService(dummy_settings(signing_keys=())).issue_access(PRINCIPAL, "guest")


def test_token_expires_after_ten_minutes_with_no_leeway() -> None:
    issued = datetime.now(UTC) - timedelta(minutes=10, seconds=1)
    token = service().issue_access(PRINCIPAL, "guest", now=issued)

    with pytest.raises(InvalidTokenError):
        service().verify_access(token)


def test_secrets_are_256_bits_base64url_and_stored_as_sha256() -> None:
    raw = new_secret()

    assert len(raw) == 43
    assert base64.urlsafe_b64decode(raw + "=") != b""
    assert hash_secret(raw) == hashlib.sha256(raw.encode()).digest()
    assert new_secret() != raw


def _r5_tokens() -> dict[str, str]:
    good = forge()
    head, body, signature = good.split(".")
    tampered = signature[:-2] + ("AA" if not signature.endswith("AA") else "BB")
    return {
        "alg none": f"{_b64(json.dumps({'alg': 'none', 'kid': KID, 'typ': 'at+jwt'}).encode())}"
        f".{body}.",
        "RS256 header, HMAC signature": forge({"alg": "RS256", "kid": KID, "typ": "at+jwt"}),
        "ES256 header, random signature": ".".join(
            [_b64(json.dumps({"alg": "ES256", "kid": KID, "typ": "at+jwt"}).encode()), body]
        )
        + "."
        + _b64(bytes(64)),
        "HS256 signed with a PEM public key, unknown kid": forge(
            {"alg": "HS256", "kid": "public", "typ": "at+jwt"}, key=FAKE_PEM_PUBLIC_KEY
        ),
        "HS256 signed with a PEM public key, known kid": forge(key=FAKE_PEM_PUBLIC_KEY),
        "HS512": forge({"alg": "HS512", "kid": KID, "typ": "at+jwt"}, digest=hashlib.sha512),
        "unknown kid": forge({"alg": "HS256", "kid": "2020-01-01", "typ": "at+jwt"}),
        "missing kid": forge({"alg": "HS256", "typ": "at+jwt"}),
        "integer kid": forge({"alg": "HS256", "kid": 1, "typ": "at+jwt"}),
        "list kid": forge({"alg": "HS256", "kid": [KID], "typ": "at+jwt"}),
        "missing typ": forge({"alg": "HS256", "kid": KID}),
        "typ JWT": forge({"alg": "HS256", "kid": KID, "typ": "JWT"}),
        # RFC 7515 4.1.11: an extension the verifier does not understand must be refused.
        "unknown crit": forge(
            {"alg": "HS256", "kid": KID, "typ": "at+jwt", "crit": ["x-capsule"], "x-capsule": 1}
        ),
        "wrong key": forge(key=OTHER_KEY),
        "expired": forge(claims=valid_claims(exp=int(time.time()) - 1)),
        "exp missing": forge(claims=without(valid_claims(), "exp")),
        "jti missing": forge(claims=without(valid_claims(), "jti")),
        "kind missing": forge(claims=without(valid_claims(), "kind")),
        "iat missing": forge(claims=without(valid_claims(), "iat")),
        "iss missing": forge(claims=without(valid_claims(), "iss")),
        "aud missing": forge(claims=without(valid_claims(), "aud")),
        "sub missing": forge(claims=without(valid_claims(), "sub")),
        "wrong aud": forge(claims=valid_claims(aud="someone-else")),
        "wrong iss": forge(claims=valid_claims(iss="someone-else")),
        "tampered signature": f"{head}.{body}.{tampered}",
        "non-UUID sub": forge(claims=valid_claims(sub="admin")),
        "integer sub": forge(claims=valid_claims(sub=7)),
        "bad kind": forge(claims=valid_claims(kind="admin")),
        "garbage": "not a token",
        "empty": "",
        "two parts": f"{head}.{body}",
        "four parts": f"{good}.{signature}",
        "non-ASCII": "é.é.é",
    }


@pytest.mark.parametrize("token", _r5_tokens().values(), ids=_r5_tokens().keys())
def test_r5_every_bad_token_raises_the_same_error(token: str) -> None:
    with pytest.raises(InvalidTokenError) as caught:
        service().verify_access(token)

    assert caught.value.args == ()
