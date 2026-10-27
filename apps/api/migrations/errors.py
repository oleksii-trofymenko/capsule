"""What a failed migration may print (ADR-022): never the driver message, which can quote row
values (`DETAIL: Key (email)=(...) already exists`), the statement or its parameters."""

from sqlalchemy.exc import DBAPIError


def sanitised_exit(exc: BaseException) -> SystemExit:
    """Exception type, SQLSTATE and constraint name only. Raise it `from None`."""
    cause = exc.orig if isinstance(exc, DBAPIError) and exc.orig is not None else exc
    kind = type(exc).__name__
    if cause is not exc:
        kind += f" ({type(cause).__name__})"
    parts = [f"migration failed: {kind}"]
    diag = getattr(cause, "diag", None)
    if diag is not None:
        if diag.sqlstate:
            parts.append(f"sqlstate={diag.sqlstate}")
        if diag.constraint_name:
            parts.append(f"constraint={diag.constraint_name}")
    return SystemExit("; ".join(parts))
