"""POST /v1/auth/guest (contracts/openapi.yaml)."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.errors import Problem
from modules.auth.activity import record_activity
from modules.auth.dependencies import get_auth_service, unauthorized
from modules.auth.schemas import GuestSession, GuestSignIn, TokenPair
from modules.auth.service import AuthService, InvalidCredentialError, IssuedTokens

router = APIRouter(prefix="/v1/auth", tags=["auth"])

NO_STORE = {"Cache-Control": "no-store"}
_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": TokenPair},
    201: {"model": GuestSession},
    401: {"model": Problem},
}


def _token_response(body: BaseModel, status: int) -> JSONResponse:
    return JSONResponse(body.model_dump(), status_code=status, headers=NO_STORE)


def _pair(tokens: IssuedTokens) -> dict[str, str]:
    return {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token}


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
