"""Request and response bodies, matching contracts/openapi.yaml."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from modules.auth.tokens import ACCESS_TOKEN_TTL

# No pattern: a malformed value gets the same 401 as an unknown one.
Secret = Annotated[str, Field(min_length=1, max_length=256)]


class GuestSignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guest_credential: Secret


class RefreshRequest(BaseModel):
    """Body of both refresh and logout."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: Secret


class TokenPair(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - a scheme name, not a secret
    expires_in: int = int(ACCESS_TOKEN_TTL.total_seconds())
    refresh_token: str


class GuestSession(TokenPair):
    guest_credential: str
