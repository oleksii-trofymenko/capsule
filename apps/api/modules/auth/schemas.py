"""Request and response bodies, matching contracts/openapi.yaml."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from modules.auth.rules import check_new_password, normalise_email, normalise_password
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


Email = Annotated[str, AfterValidator(normalise_email)]
Password = Annotated[str, AfterValidator(normalise_password)]


class NewCredentials(BaseModel):
    """Email and a new password under the ADR-014 rules. The sign-up request (E1-07) extends it,
    so the app and the Schemathesis fake apply the same rules. Values are never echoed (422),
    nor shown in a ValidationError that escapes (`hide_input_in_errors`); keep it on subclasses."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: Email  # declared first: the password rule below reads the normalised email
    password: Password

    @field_validator("password")
    @classmethod
    def _password_rules(cls, password: str, info: ValidationInfo) -> str:
        # An invalid email has its own error; the other rules still run without it.
        return check_new_password(password, info.data.get("email", ""))
