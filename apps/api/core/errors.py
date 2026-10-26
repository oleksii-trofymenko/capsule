"""RFC 9457 problem details: one error format for every response (contracts/openapi.yaml)."""

from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logging import request_id_var

PROBLEM_MEDIA_TYPE = "application/problem+json"


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    request_id: str | None = None


class FieldError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationProblem(Problem):
    errors: list[FieldError]


def problem_response(problem: Problem, headers: Mapping[str, str] | None = None) -> JSONResponse:
    if problem.request_id is None:
        problem = problem.model_copy(update={"request_id": request_id_var.get()})
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=problem.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def title_for(status: int) -> str:
    return HTTPStatus(status).phrase


def internal_error() -> JSONResponse:
    return problem_response(Problem(title=title_for(500), status=500))


async def _http_exception(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    # Keep a specific client-error message; drop the default phrase, any 5xx detail and any
    # non-string detail (a dict or list could expose internals and would not fit the schema).
    detail = exc.detail if isinstance(exc.detail, str) and exc.status_code < 500 else None
    if detail == title_for(exc.status_code):
        detail = None
    return problem_response(
        Problem(title=title_for(exc.status_code), status=exc.status_code, detail=detail),
        headers=exc.headers,
    )


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    # Only location, message and type: rejected input values are never echoed back or logged.
    errors = [FieldError(loc=list(e["loc"]), msg=e["msg"], type=e["type"]) for e in exc.errors()]
    return problem_response(
        ValidationProblem(
            title=title_for(422), status=422, detail="Request validation failed", errors=errors
        )
    )


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_error)
