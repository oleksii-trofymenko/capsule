"""JWT signing keys (ADR-014, ADR-015): one `kid=hexkey` line per key; the first line signs.

The file is a Compose secret, so its path is fixed here rather than configured. Errors name the
path, the line number, the `kid` or the count, never a key or a rejected line.
"""

import re
from pathlib import Path

from pydantic import SecretBytes

from core.config import ConfigError, SigningKey

SIGNING_KEYS_PATH = Path("/run/secrets/jwt_signing_keys")
MIN_KEY_BYTES = 32  # ADR-014
MAX_KEYS = 2  # the current key and at most one previous key (ADR-015 rotation)
# ADR-015: the UTC creation date, `-N` for another key that day. A key can never pass as one.
_KID = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(-[0-9]{1,2})?")
_HEX = re.compile(r"[0-9a-fA-F]+")


def parse_signing_keys(text: str, source: str) -> tuple[SigningKey, ...]:
    """Keys in file order. Blank lines are skipped; `source` names the file in errors."""
    keys: list[SigningKey] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        where = f"{source}: line {number}"
        kid, sep, hex_key = line.partition("=")
        if not sep:
            raise ConfigError(f"Invalid signing keys: {where}: expected kid=hexkey")
        if not _KID.fullmatch(kid):
            # The kid is not echoed: a malformed line may be a pasted key.
            raise ConfigError(
                f"Invalid signing keys: {where}: kid must be a date like 2026-10-27, "
                "with -N for another key that day"
            )
        if any(k.kid == kid for k in keys):
            raise ConfigError(f"Invalid signing keys: {where}: duplicate kid {kid}")
        if not _HEX.fullmatch(hex_key) or len(hex_key) % 2:
            raise ConfigError(f"Invalid signing keys: {where}: key for kid {kid} is not hex")
        if len(hex_key) < MIN_KEY_BYTES * 2:
            raise ConfigError(
                f"Invalid signing keys: {where}: key for kid {kid} is shorter than "
                f"{MIN_KEY_BYTES} bytes"
            )
        keys.append(SigningKey(kid, SecretBytes(bytes.fromhex(hex_key))))
    if not 1 <= len(keys) <= MAX_KEYS:
        raise ConfigError(
            f"Invalid signing keys: {source}: found {len(keys)} keys, expected 1 to {MAX_KEYS}"
        )
    return tuple(keys)


def load_signing_keys(path: Path = SIGNING_KEYS_PATH) -> tuple[SigningKey, ...]:
    try:
        text = path.read_bytes().decode("ascii")
    except OSError as exc:
        raise ConfigError(
            f"Invalid signing keys: {path}: cannot read ({type(exc).__name__})"
        ) from None
    except UnicodeDecodeError:
        # Its message quotes the offending bytes.
        raise ConfigError(f"Invalid signing keys: {path}: not ASCII text") from None
    return parse_signing_keys(text, str(path))
