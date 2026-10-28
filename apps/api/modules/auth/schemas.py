"""Request and response bodies, matching contracts/openapi.yaml."""

from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

from modules.auth.rules import (
    MAX_EMAIL_LENGTH,
    MAX_PASSWORD_INPUT_LENGTH,
    check_input_lengths,
    check_new_password,
    normalise_email,
    normalise_password,
)
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

    @field_validator("email", "password", mode="before")
    @classmethod
    def _input_lengths(cls, value: object, info: ValidationInfo) -> object:
        # The contract's maxLength (and minLength) as sent, before any normalising.
        return check_input_lengths(info.field_name or "", value)

    @field_validator("password")
    @classmethod
    def _password_rules(cls, password: str, info: ValidationInfo) -> str:
        # An invalid email has its own error; the other rules still run without it.
        return check_new_password(password, info.data.get("email", ""))


def _confirmed(value: bool) -> bool:
    if not value:
        raise PydanticCustomError("age_not_confirmed", "Confirm that you are 18 or older")
    return value


class SignUpRequest(NewCredentials):
    # StrictBool: JSON `1` is not `true` (the contract's `const: true`).
    age_confirmed: Annotated[StrictBool, AfterValidator(_confirmed)]


class SignInRequest(BaseModel):
    """Bounded before any verify, without the new-password rules: an old password still signs
    in. The email is normalised by the service; an invalid one counts as unknown (one 401)."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    email: Annotated[str, Field(max_length=MAX_EMAIL_LENGTH)]
    password: Annotated[
        str,
        Field(min_length=1, max_length=MAX_PASSWORD_INPUT_LENGTH),
        AfterValidator(normalise_password),
    ]
