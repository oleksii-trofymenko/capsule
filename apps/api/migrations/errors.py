"""What a failed migration may print (ADR-022): never the driver message, which can quote row
values (`DETAIL: Key (email)=(...) already exists`), the statement or its parameters."""

from core.config import ConfigError
from core.db_errors import describe_db_error


def sanitised_exit(exc: BaseException) -> SystemExit:
    """Exception type, SQLSTATE and constraint name only. Raise it `from None`.

    A `ConfigError` keeps its fixed message: it names the variable and the rule, never the value.
    """
    if isinstance(exc, ConfigError):
        return SystemExit(f"ConfigError: {exc}")
    return SystemExit(f"migration failed: {describe_db_error(exc)}")
