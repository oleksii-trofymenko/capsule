"""`last_activity_at` (ADR-022): written only after a 2xx response, at most hourly.

Handlers record the principal with `record_activity`. The middleware runs the capped update in
its own statement once the response has been sent, and only for a 2xx status. A failed update is
logged by type only and never changes the response.
"""

import logging
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from modules.auth import repository

_STATE_KEY = "activity_principal_id"

logger = logging.getLogger(__name__)


def record_activity(request: Request, principal_id: uuid.UUID) -> None:
    setattr(request.state, _STATE_KEY, principal_id)


class LastActivityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Created here so every Request built from this scope (or a copy) shares the dict.
        state: dict[str, object] = scope.setdefault("state", {})
        status = 0

        async def send_with_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        await self.app(scope, receive, send_with_status)
        principal_id = state.get(_STATE_KEY)
        if isinstance(principal_id, uuid.UUID) and 200 <= status < 300:
            await _touch(scope["app"].state.engine, principal_id)


async def _touch(engine: AsyncEngine, principal_id: uuid.UUID) -> None:
    try:
        async with engine.begin() as conn:
            await repository.touch_last_activity(conn, principal_id)
    except Exception as exc:
        logger.warning("last activity update failed", extra={"error": type(exc).__name__})
