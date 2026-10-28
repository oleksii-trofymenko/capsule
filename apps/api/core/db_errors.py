"""What a database error may say in logs and exit messages (ADR-022): never the driver message,
which can quote row values (`DETAIL: Key (email)=(...) already exists`), the statement or its
parameters. Only the exception type, SQLSTATE and constraint name."""

import traceback
from collections.abc import Iterator

import psycopg
from sqlalchemy.exc import DBAPIError, SQLAlchemyError


def describe_db_error(exc: BaseException) -> str:
    """`IntegrityError (UniqueViolation); sqlstate=23505; constraint=<name>`, or the type alone."""
    cause = exc.orig if isinstance(exc, DBAPIError) and exc.orig is not None else exc
    kind = type(exc).__name__
    if cause is not exc:
        kind += f" ({type(cause).__name__})"
    parts = [kind]
    diag = getattr(cause, "diag", None)
    if diag is not None:
        if diag.sqlstate:
            parts.append(f"sqlstate={diag.sqlstate}")
        if diag.constraint_name:
            parts.append(f"constraint={diag.constraint_name}")
    return "; ".join(parts)


def exception_chain(exc: BaseException) -> Iterator[BaseException]:
    """`exc`, its causes and contexts, and the members of exception groups, each once."""
    seen: set[int] = set()
    stack = [exc]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        if isinstance(current, BaseExceptionGroup):
            stack.extend(reversed(current.exceptions))
        links = (current.__context__, current.__cause__, getattr(current, "orig", None))
        stack.extend(e for e in links if isinstance(e, BaseException))


LOCK_NOT_AVAILABLE = "55P03"  # lock_timeout expired


def is_lock_timeout(exc: BaseException) -> bool:
    cause = exc.orig if isinstance(exc, DBAPIError) else exc
    return isinstance(cause, psycopg.Error) and cause.sqlstate == LOCK_NOT_AVAILABLE


def is_db_error(exc: BaseException) -> bool:
    return isinstance(exc, SQLAlchemyError | psycopg.Error)


def involves_db_error(exc: BaseException) -> bool:
    return any(is_db_error(e) for e in exception_chain(exc))


def describe_chain(exc: BaseException) -> str:
    """Every exception in the chain described as above, outermost first. A driver error that a
    SQLAlchemy error wraps (and is chained from) is already part of that error's description."""
    chain = list(exception_chain(exc))
    wrapped = {id(e.orig) for e in chain if isinstance(e, DBAPIError) and e.orig is not None}
    return " <- ".join(describe_db_error(e) for e in chain if id(e) not in wrapped)


def describe_chain_with_frames(exc: BaseException) -> str:
    """`describe_chain` plus where each exception was raised: file, line, function and source
    line from `extract_tb`, never an exception message or a local value."""
    lines = [describe_chain(exc)]
    for e in exception_chain(exc):
        lines.append(f"{type(e).__name__} raised at:")
        lines.extend(traceback.format_list(traceback.extract_tb(e.__traceback__)))
    return "\n".join(line.rstrip("\n") for line in lines)
