"""One settings object, read from environment variables. `.env.example` lists every variable."""

from collections.abc import Mapping
from typing import Literal, NamedTuple
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretBytes,
    SecretStr,
    ValidationError,
    field_validator,
)

_PG_SCHEMES = {"postgres", "postgresql", "postgresql+psycopg"}
_REDIS_SCHEMES = {"redis", "rediss"}

# Field name -> environment variable.
ENV_VARS: dict[str, str] = {
    "database_url": "DATABASE_URL",
    "redis_url": "REDIS_URL",
    "log_level": "LOG_LEVEL",
    "ready_probe_timeout_s": "READY_PROBE_TIMEOUT_S",
    "database_connect_timeout_s": "DATABASE_CONNECT_TIMEOUT_S",
    "redis_socket_timeout_s": "REDIS_SOCKET_TIMEOUT_S",
}


class ConfigError(Exception):
    """Invalid or missing settings. The message never contains the rejected values."""


class SigningKey(NamedTuple):
    """One JWT signing key (ADR-014). Loaded by `core.signing_keys`, never from the environment."""

    kid: str
    key: SecretBytes


def normalise_database_url(url: str) -> str:
    """Return the URL with the psycopg 3 driver; plain `postgresql://` (as in CI) is accepted."""
    scheme, sep, rest = url.partition("://")
    if not sep or scheme.lower() not in _PG_SCHEMES:
        raise ValueError("must start with postgresql:// or postgresql+psycopg://")
    try:
        hostname = urlsplit(url).hostname
    except ValueError:
        # The stdlib message quotes the host (e.g. a bracketed name); never pass it on.
        raise ConfigError("Invalid settings: DATABASE_URL: host is not valid") from None
    if not hostname:
        raise ValueError("must name a host")
    return f"postgresql+psycopg://{rest}"


def database_url_from_env(environ: Mapping[str, str]) -> str:
    """DATABASE_URL alone, for tools that need no other settings (Alembic)."""
    var = ENV_VARS["database_url"]
    if var not in environ:
        raise ConfigError(f"Invalid settings: {var}: Field required")
    try:
        return normalise_database_url(environ[var])
    except ValueError as exc:
        raise ConfigError(f"Invalid settings: {var}: {exc}") from None


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    database_url: SecretStr
    redis_url: SecretStr
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Budget for each /v1/ready probe, enforced with asyncio.timeout around the whole call.
    ready_probe_timeout_s: float = Field(default=1.0, gt=0, le=10)
    # Client timeouts for normal traffic. libpq takes whole seconds.
    database_connect_timeout_s: int = Field(default=5, ge=1, le=60)
    redis_socket_timeout_s: float = Field(default=5.0, gt=0, le=60)
    # ADR-015 rotation: the first key signs; the second, if any, only verifies.
    signing_keys: tuple[SigningKey, ...] = Field(min_length=1, max_length=2)

    @field_validator("database_url", mode="before")
    @classmethod
    def _database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalise_database_url(value)
        return value

    @field_validator("redis_url", mode="before")
    @classmethod
    def _redis_url(cls, value: object) -> object:
        if isinstance(value, str):
            scheme = value.partition("://")[0].lower()
            if scheme not in _REDIS_SCHEMES or not urlsplit(value).hostname:
                raise ValueError("must be redis://host or rediss://host")
        return value

    @property
    def signing_key(self) -> SigningKey:
        return self.signing_keys[0]

    def verification_key(self, kid: str) -> SecretBytes | None:
        """Exact `kid` match, no fallback key (ADR-014)."""
        return next((k.key for k in self.signing_keys if k.kid == kid), None)

    @classmethod
    def from_env(
        cls, environ: Mapping[str, str], *, signing_keys: tuple[SigningKey, ...]
    ) -> "Settings":
        """`signing_keys` come from a file, not the environment (`core.signing_keys`)."""
        values: dict[str, object] = {
            field: environ[var] for field, var in ENV_VARS.items() if var in environ
        }
        values["signing_keys"] = signing_keys
        try:
            return cls.model_validate(values)
        except ValidationError as exc:
            problems = "; ".join(
                f"{ENV_VARS.get(str(err['loc'][0]), err['loc'][0])}: {err['msg']}"
                for err in exc.errors(include_input=False, include_url=False)
            )
            raise ConfigError(f"Invalid settings: {problems}") from None
