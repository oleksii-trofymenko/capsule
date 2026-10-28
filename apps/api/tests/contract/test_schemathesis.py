"""Generated requests for every operation in contracts/openapi.yaml (ADR-025).

Schemathesis runs in-process against the app. The auth service, the readiness probes and the
engine used by the last-activity middleware are fakes, so no Postgres or Redis is needed; the
SQL, its locks and the real token rules are covered by tests/integration.
"""

import inspect
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import schemathesis
from fastapi import FastAPI
from hypothesis import HealthCheck, settings
from schemathesis.checks import positive_data_acceptance

from core.health import get_probes
from main import create_app
from modules.auth.dependencies import get_auth_service
from modules.auth.rules import try_normalise_email
from modules.auth.service import (
    AuthService,
    EmailRegisteredError,
    InvalidCredentialError,
    InvalidRefreshTokenError,
    InvalidSignInError,
    IssuedTokens,
    NewGuest,
)
from modules.auth.tokens import Kind, TokenService, hash_secret, new_secret
from tests.support import CONTRACT_PATH, client_for, contract, dummy_settings

schema = schemathesis.openapi.from_path(CONTRACT_PATH)
# Coverage tries every boundary and invalid value the schemas define (refresh_token of length 0,
# 256 and 257, a missing body, a wrong type) on every run; fuzzing adds random cases on top.
# Its cases run as Hypothesis explicit examples, so `--hypothesis-show-statistics` omits them.
schema.config.phases.update(phases=["examples", "coverage", "fuzzing"])


class FakeAuthService:
    """In-memory stand-in for AuthService: same methods, real tokens and hashes.

    Raises the real 401 and 409 exceptions; never a busy error (FamilyBusyError, HasherBusyError),
    so 503 is not generated here. No argon2: accounts keep a SHA-256 of the password, which is
    enough to tell a right password from a wrong one. The request schemas (SignUpRequest with
    the shared NewCredentials rules, SignInRequest) run before the fake, as before the real one.
    """

    def __init__(self, tokens: TokenService) -> None:
        self._tokens = tokens
        self._guests: dict[bytes, uuid.UUID] = {}
        self._refresh: dict[bytes, tuple[uuid.UUID, Kind]] = {}
        self._accounts: dict[str, tuple[uuid.UUID, bytes]] = {}

    async def create_guest(self) -> NewGuest:
        credential = new_secret()
        principal_id = uuid.uuid4()
        self._guests[hash_secret(credential)] = principal_id
        return NewGuest(self._issue(principal_id, "guest"), credential)

    async def sign_in_guest(self, credential: str) -> IssuedTokens:
        principal_id = self._guests.get(hash_secret(credential))
        if principal_id is None:
            raise InvalidCredentialError
        return self._issue(principal_id, "guest")

    async def sign_up(self, email: str, password: str) -> IssuedTokens:
        if email in self._accounts:
            raise EmailRegisteredError
        principal_id = uuid.uuid4()
        self._accounts[email] = (principal_id, hash_secret(password))
        return self._issue(principal_id, "account")

    async def sign_in(self, email: str, password: str) -> IssuedTokens:
        account = self._accounts.get(try_normalise_email(email) or "")
        if account is None or account[1] != hash_secret(password):
            raise InvalidSignInError
        return self._issue(account[0], "account")

    async def refresh(self, refresh_token: str) -> IssuedTokens:
        known = self._refresh.pop(hash_secret(refresh_token), None)
        if known is None:
            raise InvalidRefreshTokenError
        return self._issue(*known)

    async def logout(self, refresh_token: str) -> None:
        self._refresh.pop(hash_secret(refresh_token), None)

    def _issue(self, principal_id: uuid.UUID, kind: Kind) -> IssuedTokens:
        refresh_token = new_secret()
        self._refresh[hash_secret(refresh_token)] = (principal_id, kind)
        access_token = self._tokens.issue_access(principal_id, kind)
        return IssuedTokens(principal_id, access_token, refresh_token)


class _FakeConnection:
    async def execute(self, *_: object, **__: object) -> None:
        return None


class _FakeEngine:
    """What LastActivityMiddleware needs from app.state.engine after a 2xx response."""

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[_FakeConnection]:
        yield _FakeConnection()


async def _ok() -> None:
    return None


@pytest.fixture
def app() -> FastAPI:
    app = create_app(dummy_settings())
    app.state.engine = _FakeEngine()
    fake = FakeAuthService(TokenService(app.state.settings))
    app.dependency_overrides[get_auth_service] = lambda: fake
    app.dependency_overrides[get_probes] = lambda: {"postgres": _ok, "redis": _ok}
    return app


@schema.parametrize()
# derandomize: a fixed seed, the same cases on every run; database=None: no example database
# (Hypothesis still writes its gitignored `.hypothesis/constants` cache).
# One app per operation on purpose: the fake keeps its state across that operation's cases, and
# a function-scoped fixture keeps create_app's logging setup inside the test's own restore.
@settings(
    max_examples=100,
    derandomize=True,
    database=None,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_every_operation_matches_the_contract(case: schemathesis.Case[Any], app: FastAPI) -> None:
    # Every default check: no 5xx, declared status, content type, headers and body schema,
    # invalid input rejected, valid input accepted, unsupported methods refused.
    if case.operation.path != SIGN_UP:
        case.call_and_validate(app=app)
        return
    # Sign-up only: some password and email rules cannot be written as JSON Schema (NFC length,
    # the blocklist, the app name, the email's name, invisible characters), so a schema-valid
    # body can get 422. The default "valid data accepted" check is replaced, for this operation
    # only, by a narrower one: such a 422 must name only those rules. Every other check runs.
    response = case.call_and_validate(app=app, excluded_checks=[positive_data_acceptance])
    if case.meta is not None and case.meta.generation.mode.is_positive:
        if response.status_code == 422:
            types = {error["type"] for error in response.json()["errors"]}
            assert types <= RULES_NOT_IN_SCHEMA, types
        else:
            assert response.status_code in {201, 409}, response.status_code


SIGN_UP = "/v1/auth/sign-up"
RULES_NOT_IN_SCHEMA = {
    "password_length",  # 12 to 128 after NFC; the schema bounds the value as sent
    "password_common",
    "password_product_name",
    "password_email",
    "email_invalid",  # empty labels, control and format characters, length after normalising
}


@pytest.mark.anyio
async def test_the_contracts_sign_up_example_is_accepted(app: FastAPI) -> None:
    # The sign-up check above lets a 422 name `email_invalid`; this keeps that exemption from
    # hiding an email rule stricter than the contract: its own example must get 201.
    operation = contract()["paths"][SIGN_UP]["post"]
    example = operation["requestBody"]["content"]["application/json"]["example"]
    async with client_for(app) as client:
        response = await client.post(SIGN_UP, json=example)

    assert response.status_code == 201, response.text


def _public_methods(cls: type) -> dict[str, tuple[inspect.Signature, bool]]:
    return {
        name: (inspect.signature(member), inspect.iscoroutinefunction(member))
        for name, member in vars(cls).items()
        if callable(member) and not name.startswith("_")
    }


def test_fake_auth_service_has_the_real_methods_and_signatures() -> None:
    assert _public_methods(FakeAuthService) == _public_methods(AuthService)


def test_coverage_phase_stays_on() -> None:
    phases = schema.config.phases

    assert phases.coverage.enabled
    assert phases.fuzzing.enabled
    assert not phases.stateful.enabled  # stateless until the contract has links (ADR-025)
