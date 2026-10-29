"""POST /v1/auth/guest, /refresh, /logout, /sign-up and /sign-in (contracts/openapi.yaml).

A busy refresh family or password hasher raises a `ServiceBusyError`, which the app answers
with 503 and `Retry-After` (core/errors.py).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.errors import Problem, problem_response
from modules.auth.activity import record_activity
from modules.auth.dependencies import get_auth_service, unauthorized
from modules.auth.schemas import (
    AccountSession,
    GuestSession,
    GuestSignIn,
    RefreshRequest,
    SignInRequest,
    SignUpRequest,
    TokenPair,
)
from modules.auth.service import (
    AuthService,
    EmailRegisteredError,
    InvalidCredentialError,
    InvalidRefreshTokenError,
    InvalidSignInError,
    IssuedTokens,
    SignedIn,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

NO_STORE = {"Cache-Control": "no-store"}
# 400 is FastAPI's own answer to a body it cannot read (BadRequest in the contract).
_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": TokenPair},
    201: {"model": GuestSession},
    400: {"model": Problem},
    401: {"model": Problem},
}
_REFRESH_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": TokenPair},
    400: {"model": Problem},
    401: {"model": Problem},
    503: {"model": Problem},
}
_LOGOUT_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": Problem},
    503: {"model": Problem},
}
_SIGN_UP_RESPONSES: dict[int | str, dict[str, Any]] = {
    201: {"model": AccountSession},
    400: {"model": Problem},
    409: {"model": Problem},
    503: {"model": Problem},
}
_SIGN_IN_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": AccountSession},
    400: {"model": Problem},
    401: {"model": Problem},
    503: {"model": Problem},
}
# A7: a fixed type the app keys on to offer sign-in, and nothing about the account.
EMAIL_REGISTERED = Problem(
    type="urn:capsule:problem:email-registered",
    title="Conflict",
    status=409,
    detail="An account with this email exists. Sign in instead.",
)


def _token_response(body: BaseModel, status: int) -> JSONResponse:
    return JSONResponse(body.model_dump(), status_code=status, headers=NO_STORE)


def _pair(tokens: IssuedTokens) -> dict[str, str]:
    return {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token}


def _account_session(signed_in: SignedIn) -> AccountSession:
    moved = signed_in.guest_guides_moved
    return AccountSession(**_pair(signed_in.tokens), guest_guides_moved=moved)


@router.post("/guest", status_code=201, response_model=None, responses=_RESPONSES)
async def guest(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    body: Annotated[GuestSignIn | None, Body()] = None,
) -> JSONResponse:
    if body is None:
        # FastAPI maps both an empty body and JSON `null` to None. Only an empty body is absent;
        # `null` is a present body that is not a GuestSignIn object (contracts/openapi.yaml).
        if await request.body():  # read once by FastAPI already; this returns the cached bytes
            raise RequestValidationError(
                [{"loc": ("body",), "msg": "Input should be an object", "type": "model_type"}]
            )
        new = await service.create_guest()
        session = GuestSession(**_pair(new.tokens), guest_credential=new.guest_credential)
        return _token_response(session, 201)
    try:
        tokens = await service.sign_in_guest(body.guest_credential)
    except InvalidCredentialError:
        raise unauthorized() from None
    record_activity(request, tokens.principal_id)  # ADR-022: sign-in counts as activity
    return _token_response(TokenPair(**_pair(tokens)), 200)


@router.post("/refresh", response_model=None, responses=_REFRESH_RESPONSES)
async def refresh(
    request: Request,
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    try:
        tokens = await service.refresh(body.refresh_token)
    except InvalidRefreshTokenError:
        raise unauthorized() from None
    record_activity(request, tokens.principal_id)  # ADR-022: a 2xx refresh counts as activity
    return _token_response(TokenPair(**_pair(tokens)), 200)


@router.post("/logout", status_code=204, response_model=None, responses=_LOGOUT_RESPONSES)
async def logout(
    body: RefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.logout(body.refresh_token)  # not activity (ADR-022)
    return Response(status_code=204)


@router.post("/sign-up", status_code=201, response_model=None, responses=_SIGN_UP_RESPONSES)
async def sign_up(
    body: SignUpRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    # Rate limits (E1-08) go in front of this handler, before any hash (R8).
    try:
        signed_in = await service.sign_up(body.email, body.password, body.guest_credential)
    except EmailRegisteredError:
        return problem_response(EMAIL_REGISTERED)
    return _token_response(_account_session(signed_in), 201)


@router.post("/sign-in", response_model=None, responses=_SIGN_IN_RESPONSES)
async def sign_in(
    request: Request,
    body: SignInRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    # Rate limits (E1-08) go in front of this handler, before any verify (R8).
    try:
        signed_in = await service.sign_in(body.email, body.password, body.guest_credential)
    except InvalidSignInError:
        raise unauthorized() from None
    record_activity(request, signed_in.tokens.principal_id)  # ADR-022: sign-in is activity
    return _token_response(_account_session(signed_in), 200)
