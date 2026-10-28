"""Sign-up and sign-in request bodies (E1-07): the bounds as sent, then the E1-07a rules."""

import pytest
from pydantic import ValidationError

from modules.auth.rules import try_normalise_email
from modules.auth.schemas import SignInRequest, SignUpRequest

COMMON = "123456789012"
DECOMPOSED = "cafe\u0301"  # e + combining acute
COMPOSED = "caf\u00e9"
GOOD: dict[str, object] = {
    "email": "Ada@Example.com",
    "password": "violet hedgehog 42",
    "age_confirmed": True,
}


def _error_types(model: type[SignUpRequest | SignInRequest], body: dict[str, object]) -> list[str]:
    with pytest.raises(ValidationError) as caught:
        model.model_validate(body)
    return [e["type"] for e in caught.value.errors()]


def test_sign_up_normalises_and_keeps_the_rules() -> None:
    request = SignUpRequest.model_validate(GOOD)

    assert request.email == "ada@example.com"
    assert _error_types(SignUpRequest, GOOD | {"password": "123456789012"}) == ["password_common"]


@pytest.mark.parametrize(
    ("value", "error"),
    [(False, "age_not_confirmed"), (1, "bool_type"), ("true", "bool_type"), (None, "bool_type")],
)
def test_sign_up_needs_age_confirmed_true(value: object, error: str) -> None:
    assert _error_types(SignUpRequest, GOOD | {"age_confirmed": value}) == [error]


def test_sign_up_without_age_confirmed_is_refused() -> None:
    body = {k: v for k, v in GOOD.items() if k != "age_confirmed"}
    assert _error_types(SignUpRequest, body) == ["missing"]


@pytest.mark.parametrize(
    ("password", "ok"),
    [
        ("x" * 11 + "\u0958", True),  # 12 as sent; NFC keeps it 12 or more
        ("e\u0301" * 64, True),  # 128 as sent, 64 after NFC
        ("e\u0301" * 128, True),  # 256 as sent, 128 after NFC
        ("e\u0301" * 256, False),  # 512 as sent, 256 after NFC
        ("e" * 513, False),  # over the 512 bound as sent
    ],
)
def test_sign_up_password_bounds_as_sent_and_after_nfc(password: str, ok: bool) -> None:
    body = GOOD | {"password": password}
    if ok:
        SignUpRequest.model_validate(body)
    else:
        assert _error_types(SignUpRequest, body) == ["password_length"]


def test_sign_up_email_over_254_as_sent_is_refused_even_if_trimming_would_fit() -> None:
    email = " " + "a" * 241 + "@example.com" + " "  # 254 after the trim, 256 as sent
    assert _error_types(SignUpRequest, GOOD | {"email": email}) == ["email_invalid"]


def test_sign_in_bounds_the_password_without_the_new_password_rules() -> None:
    request = SignInRequest(email="Not An Email", password=COMMON)  # an old password still works
    assert request.password == COMMON
    assert request.email == "Not An Email"  # normalised by the service; invalid means unknown
    assert SignInRequest(email="a@b.co", password=DECOMPOSED).password == COMPOSED
    empty: dict[str, object] = {"email": "a@b.co", "password": ""}
    assert _error_types(SignInRequest, empty) == ["string_too_short"]
    too_long: dict[str, object] = {"email": "a@b.co", "password": "x" * 513}
    assert _error_types(SignInRequest, too_long) == ["string_too_long"]
    surrogate: dict[str, object] = {"email": "a@b.co", "password": "violet \ud800 hedgehog"}
    # Refused before any verify; with length bounds Pydantic's own string check catches it first.
    assert _error_types(SignInRequest, surrogate) in (["string_unicode"], ["password_invalid"])


def test_sign_in_hides_input_in_errors() -> None:
    with pytest.raises(ValidationError) as caught:
        SignInRequest.model_validate({"email": "ada@example.com", "password": "x" * 513})
    assert "ada@example.com" not in str(caught.value)


@pytest.mark.parametrize(
    ("raw", "normalised"),
    [(" Ada@Example.COM ", "ada@example.com"), ("not an email", None), ("a@b", None)],
)
def test_try_normalise_email(raw: str, normalised: str | None) -> None:
    assert try_normalise_email(raw) == normalised
