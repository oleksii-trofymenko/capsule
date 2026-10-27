"""JWT signing-key file (ADR-014, ADR-015): accepted shapes and refusals that echo no value."""

from pathlib import Path

import pytest
from pydantic import SecretBytes, ValidationError

from core.config import ConfigError, SigningKey
from core.signing_keys import SIGNING_KEYS_PATH, load_signing_keys, parse_signing_keys
from main import create_app
from tests.support import dummy_settings

CURRENT = "c0" * 32  # 32 bytes, as env-init.sh writes them
PREVIOUS = "9e" * 32


def _write(tmp_path: Path, content: str | bytes) -> Path:
    path = tmp_path / "jwt_signing_keys"
    if isinstance(content, str):
        content = content.encode()
    path.write_bytes(content)
    return path


def test_loads_the_file_env_init_writes(tmp_path: Path) -> None:
    keys = load_signing_keys(_write(tmp_path, f"2026-10-27={CURRENT}\n"))

    assert keys == (SigningKey("2026-10-27", SecretBytes(bytes.fromhex(CURRENT))),)


def test_first_key_signs_and_second_only_verifies(tmp_path: Path) -> None:
    keys = load_signing_keys(_write(tmp_path, f"new={CURRENT}\nold={PREVIOUS}\n"))
    settings = dummy_settings(signing_keys=keys)

    assert settings.signing_key.kid == "new"
    assert settings.signing_key.key.get_secret_value() == bytes.fromhex(CURRENT)
    old = settings.verification_key("old")
    assert old is not None and old.get_secret_value() == bytes.fromhex(PREVIOUS)
    assert settings.verification_key("missing") is None


def test_accepts_crlf_blank_lines_upper_case_and_longer_keys() -> None:
    longer = "AB" * 48
    keys = parse_signing_keys(f"\r\nk1={longer}\r\n\r\n", "test")

    assert [k.kid for k in keys] == ["k1"]
    assert keys[0].key.get_secret_value() == bytes.fromhex(longer)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", "found 0 keys, expected 1 to 2"),
        ("\n\n", "found 0 keys, expected 1 to 2"),
        (f"a={CURRENT}\nb={PREVIOUS}\nc={CURRENT}\n", "found 3 keys, expected 1 to 2"),
        (f"{CURRENT}\n", "line 1: expected kid=hexkey"),
        (f"a={CURRENT}\nbad kid {CURRENT}={PREVIOUS}\n", "line 2: kid must be"),
        (f"={CURRENT}\n", "line 1: kid must be"),
        (f"{'k' * 33}={CURRENT}\n", "line 1: kid must be"),
        (f"{PREVIOUS}={CURRENT}\n", "line 1: kid must be"),
        (f"a={CURRENT}\na={PREVIOUS}\n", "line 2: duplicate kid a"),
        (f"a={CURRENT[:-1]}z\n", "line 1: key for kid a is not hex"),
        (f"a={CURRENT}0\n", "line 1: key for kid a is not hex"),  # odd length
        (f"a=c0 {CURRENT}\n", "line 1: key for kid a is not hex"),  # fromhex would allow spaces
        (f"a={CURRENT[:62]}\n", "line 1: key for kid a is shorter than 32 bytes"),
        ("a=\n", "line 1: key for kid a is not hex"),
    ],
    ids=[
        "empty",
        "blank",
        "three-keys",
        "no-equals",
        "kid-with-spaces",
        "empty-kid",
        "long-kid",
        "key-as-kid",
        "duplicate-kid",
        "non-hex",
        "odd-length",
        "spaces",
        "31-bytes",
        "empty-key",
    ],
)
def test_refuses_without_echoing_a_value(tmp_path: Path, content: str, expected: str) -> None:
    path = _write(tmp_path, content)

    with pytest.raises(ConfigError) as caught:
        load_signing_keys(path)

    message = str(caught.value)
    assert message.startswith(f"Invalid signing keys: {path}: {expected}")
    for value in (CURRENT, PREVIOUS, CURRENT[:62], "bad kid", "k" * 33):
        assert value not in message


def test_unreadable_file_names_the_path_only(tmp_path: Path) -> None:
    missing = tmp_path / "absent"

    with pytest.raises(ConfigError) as caught:
        load_signing_keys(missing)

    assert str(caught.value) == f"Invalid signing keys: {missing}: cannot read (FileNotFoundError)"
    assert caught.value.__suppress_context__


def test_non_ascii_file_does_not_quote_its_bytes(tmp_path: Path) -> None:
    path = _write(tmp_path, f"a={CURRENT}\n".encode() + b"\xffsecret\n")

    with pytest.raises(ConfigError) as caught:
        load_signing_keys(path)

    assert str(caught.value) == f"Invalid signing keys: {path}: not ASCII text"
    assert "secret" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_settings_take_one_or_two_keys() -> None:
    key = SigningKey("k", SecretBytes(bytes.fromhex(CURRENT)))

    for keys in ((), (key, key._replace(kid="l"), key._replace(kid="m"))):
        with pytest.raises(ValidationError):
            dummy_settings(signing_keys=keys)


def test_app_reads_the_fixed_path_and_refuses_to_start_without_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert Path("/run/secrets/jwt_signing_keys") == SIGNING_KEYS_PATH
    if SIGNING_KEYS_PATH.exists():
        pytest.skip("a real key file is mounted here")
    monkeypatch.setenv("DATABASE_URL", "postgresql://capsule:dummy@db.invalid:5432/capsule")
    monkeypatch.setenv("REDIS_URL", "redis://cache.invalid:6379/0")

    with pytest.raises(ConfigError, match="jwt_signing_keys: cannot read"):
        create_app()
