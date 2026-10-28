"""Email normalisation and the ADR-014 password rules, through the shared schema."""

import re
import unicodedata

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from core.errors import install_problem_handlers
from modules.auth import rules
from modules.auth.schemas import NewCredentials
from tests.support import client_for

pytestmark = pytest.mark.anyio

EMAIL = "Ada.Lovelace+Capsule@Example.com"
GOOD = "violet hedgehog 42"
EMAIL_SHAPE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")  # the filter in the blocklist header


def _errors(**body: str) -> list[tuple[str, str]]:
    with pytest.raises(ValidationError) as caught:
        NewCredentials.model_validate({"email": EMAIL, "password": GOOD} | body)
    return [(str(e["loc"][0]), e["type"]) for e in caught.value.errors()]


@pytest.mark.parametrize(
    ("raw", "normalised"),
    [
        (EMAIL, "ada.lovelace+capsule@example.com"),  # case folded; dots and +tag kept
        ("  ada@example.com\t\n", "ada@example.com"),  # trimmed
        ("José@example.com", "josé@example.com"),  # NFC: e + combining acute
        ("ADA@EXAMPLE.CO.UK", "ada@example.co.uk"),
    ],
)
def test_email_is_normalised(raw: str, normalised: str) -> None:
    assert NewCredentials(email=raw, password=GOOD).email == normalised


def test_case_variants_normalise_to_one_email() -> None:
    variants = {"ADA@example.com", "ada@EXAMPLE.com", " Ada@Example.Com "}
    assert {rules.normalise_email(v) for v in variants} == {"ada@example.com"}


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "ada",
        "ada@",
        "@example.com",
        "a@b@example.com",
        "ada@example",
        "ada@.com",
        "ada@ex..com",
    ],
)
def test_email_syntax_is_checked(bad: str) -> None:
    assert _errors(email=bad) == [("email", "email_invalid")]


def test_email_length_is_checked_after_normalising() -> None:
    at_limit = "a" * 242 + "@example.com"  # 254 characters
    assert rules.normalise_email(f"  {at_limit.upper()}  ") == at_limit
    assert _errors(email="a" + at_limit) == [("email", "email_invalid")]


@pytest.mark.parametrize(("length", "ok"), [(11, False), (12, True), (128, True), (129, False)])
def test_password_length_bounds(length: int, ok: bool) -> None:
    password = "".join(chr(0x4E00 + i) for i in range(length))  # never on the blocklist
    if ok:
        assert NewCredentials(email=EMAIL, password=password).password == password
    else:
        assert _errors(password=password) == [("password", "password_length")]


def test_password_length_counts_code_points_after_nfc() -> None:
    # 12 code points as typed, 6 after NFC: each "e" + U+0301 becomes one "é".
    decomposed = "é" * 6
    assert len(decomposed) == 12
    assert _errors(password=decomposed) == [("password", "password_length")]
    # 128 code points after NFC, typed as 256.
    long_nfc = NewCredentials(email=EMAIL, password="é" * 128).password
    assert long_nfc == "é" * 128


def test_password_is_stored_in_nfc_and_spaces_are_kept() -> None:
    typed = "  café au lait  "
    assert NewCredentials(email=EMAIL, password=typed).password == unicodedata.normalize(
        "NFC", typed
    )


@pytest.mark.parametrize("common", ["1234567890ab", "ILOVEYOU1234", "Qwertyuiop123"])
def test_blocklisted_passwords_are_refused_in_any_case(common: str) -> None:
    assert common.casefold() in rules.blocklist()
    assert _errors(password=common) == [("password", "password_common")]


def test_blocklist_is_loaded_without_its_header() -> None:
    entries = rules.blocklist()
    assert len(entries) == 29931
    assert not any(e.startswith("#") for e in entries)
    assert all(len(e) >= 12 for e in entries)
    # Filtered out: email addresses, `$hex[...]` encodings and control characters.
    assert not any(EMAIL_SHAPE.search(e) or e.startswith("$hex[") for e in entries)
    assert not any(unicodedata.category(c) == "Cc" for e in entries for c in e)


@pytest.mark.parametrize("password", ["my capsule wardrobe", "CAPSULE-2026-ok!", "xxCapsulexxxx"])
def test_product_name_is_refused(password: str) -> None:
    assert _errors(password=password) == [("password", "password_product_name")]


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("Margaret.Hamilton@example.com", "MARGARET.HAMILTON"),  # equal
        ("margaret.hamilton@example.com", "margaret.hamilton!"),  # contained
        ("margaret.hamilton+shop@example.com", "margaret.hamilton!"),  # +tag removed first
        ("Ada.Lovelace@example.com", "my name is ada.lovelace"),
        ("grace@example.com", "123 GRACE 456 x"),  # 5 code points: a substring rule
        ("ab+averylongshoptag@example.com", "AB+averylongshoptag"),  # short base: equal match
    ],
)
def test_email_local_part_is_refused(email: str, password: str) -> None:
    assert _errors(email=email, password=password) == [("password", "password_email")]


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ada@example.com", "ada is my cat name"),  # 3 code points: only an equal match counts
        ("ab+averylongshoptag@example.com", "ab+averylongshoptag!"),
        ("margaret.hamilton+shop@example.com", "a very long shop tag"),  # the tag alone is fine
    ],
)
def test_email_local_part_allows(email: str, password: str) -> None:
    assert NewCredentials(email=email, password=password).password == password


def test_a_lone_surrogate_password_is_refused_before_any_hash() -> None:
    surrogate = "violet hedgehog \ud800 42"
    assert _errors(password=surrogate) == [("password", "password_invalid")]


@pytest.mark.parametrize(
    "bad",
    [
        "ada\ud800@example.com",  # lone surrogate
        "ada lovelace@example.com",  # space
        "ada@exam\u00a0ple.com",  # no-break space
        "ada\t@example.com",  # tab inside, not at the ends
        "ada\x00@example.com",  # C0 control
        "ada\x85x@example.com",  # C1 control (NEL)
        "ada\u009f@example.com",  # C1 control
        "ad\u200ba@example.com",  # Cf: zero-width space
        "ad\u202ea@example.com",  # Cf: right-to-left override
        "ad\u00ada@example.com",  # Cf: soft hyphen
    ],
)
def test_email_with_space_control_format_or_surrogate_is_refused(bad: str) -> None:
    assert _errors(email=bad) == [("email", "email_invalid")]


def test_validation_errors_hide_the_input() -> None:
    common = "qwertyuiop123"  # on the blocklist
    with pytest.raises(ValidationError) as caught:
        NewCredentials.model_validate({"email": "nope@nowhere", "password": common})
    text = str(caught.value) + repr(caught.value)
    assert common not in text
    assert "nope@nowhere" not in text
    assert NewCredentials.model_config.get("hide_input_in_errors") is True


def test_bad_email_still_checks_the_password() -> None:
    short = "short"
    assert _errors(email="nope", password=short) == [
        ("email", "email_invalid"),
        ("password", "password_length"),
    ]


async def test_a_broken_rule_is_a_422_that_never_echoes_the_value() -> None:
    app = FastAPI()
    install_problem_handlers(app)

    @app.post("/probe")
    async def probe(body: NewCredentials) -> dict[str, str]:
        return {"email": body.email}

    common = "qwertyuiop123"  # on the blocklist
    async with client_for(app) as client:
        refused = await client.post("/probe", json={"email": "Ada@Example.com", "password": common})
        accepted = await client.post("/probe", json={"email": "Ada@Example.com", "password": GOOD})
        # JSON may escape a lone surrogate; it must be a 422, never a 500 from the hash.
        surrogate = await client.post(
            "/probe",
            content=b'{"email": "ada@example.com", "password": "violet hedgehog \\ud800 42"}',
            headers={"Content-Type": "application/json"},
        )

    assert surrogate.status_code == 422
    assert [e["type"] for e in surrogate.json()["errors"]] == ["password_invalid"]

    assert refused.status_code == 422
    assert refused.headers["content-type"] == "application/problem+json"
    assert refused.json()["errors"] == [
        {"loc": ["body", "password"], "msg": "Password is too common", "type": "password_common"}
    ]
    assert common not in refused.text.casefold()
    assert "ada@example.com" not in refused.text.casefold()
    assert accepted.json() == {"email": "ada@example.com"}
