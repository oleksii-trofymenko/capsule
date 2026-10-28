"""Email normalisation and password rules (ADR-014).

Error messages and types are fixed text: a rejected email or password is never echoed.
"""

import unicodedata
from functools import cache
from pathlib import Path

from pydantic_core import PydanticCustomError

MAX_EMAIL_LENGTH = 254
MIN_PASSWORD_LENGTH = 12  # code points after NFC; a signed-off deviation from NIST (ADR-014)
MAX_PASSWORD_LENGTH = 128
PRODUCT_NAME = "capsule"

_BLOCKLIST_PATH = Path(__file__).parent / "data" / "password-blocklist.txt"


def normalise_email(raw: str) -> str:
    """Trim, NFC, lower-case the whole address; `+tag` and dots stay. Then the minimal syntax
    check: one `@`, a non-empty local part and a dotted domain, at most 254 characters."""
    email = unicodedata.normalize("NFC", raw.strip()).lower()
    local, at, domain = email.partition("@")
    labels = domain.split(".")
    if (
        len(email) > MAX_EMAIL_LENGTH
        or not at
        or not local
        or "@" in domain
        or len(labels) < 2
        or not all(labels)
    ):
        raise PydanticCustomError("email_invalid", "Enter a valid email address")
    return email


def normalise_password(raw: str) -> str:
    """NFC, the form that is hashed and verified. Length is counted in code points of this form."""
    return unicodedata.normalize("NFC", raw)


@cache
def blocklist() -> frozenset[str]:
    """Casefolded NFC entries from the data file; its header lines start with `#`."""
    with _BLOCKLIST_PATH.open(encoding="utf-8") as lines:
        return frozenset(line.rstrip("\n") for line in lines if not line.startswith("#"))


def check_new_password(password: str, email: str) -> str:
    """The ADR-014 rules for a new password. `password` and `email` are already normalised."""
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise PydanticCustomError(
            "password_length",
            "Password must be {min} to {max} characters",
            {"min": MIN_PASSWORD_LENGTH, "max": MAX_PASSWORD_LENGTH},
        )
    folded = password.casefold()
    if folded in blocklist():
        raise PydanticCustomError("password_common", "Password is too common")
    # An equal match could never pass the length rule, so the product name is a substring rule.
    if PRODUCT_NAME in folded:
        raise PydanticCustomError("password_product_name", "Password must not contain the app name")
    if folded == email.partition("@")[0].casefold():
        raise PydanticCustomError("password_email", "Password must not be your email name")
    return password
