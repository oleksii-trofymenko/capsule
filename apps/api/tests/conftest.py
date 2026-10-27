import asyncio
import logging
import logging.config
import sys
from collections.abc import Iterator

import pytest
from uvicorn.config import LOGGING_CONFIG

from core.logging import QUIET_LOGGERS, SERVER_ACCESS_LOGGER, SERVER_LOGGERS


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, object]]:
    # psycopg's async mode needs a selector event loop; Windows defaults to Proactor.
    options: dict[str, object] = {}
    if sys.platform == "win32":
        options["loop_factory"] = asyncio.SelectorEventLoop
    return ("asyncio", options)


@pytest.fixture(autouse=True)
def _restore_root_logging() -> Iterator[None]:
    """create_app() installs a JSON handler on the root logger; undo it after each test."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    quiet = {name: logging.getLogger(name).level for name in QUIET_LOGGERS}
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    for name, quiet_level in quiet.items():
        logging.getLogger(name).setLevel(quiet_level)


@pytest.fixture
def uvicorn_logging() -> Iterator[None]:
    """Apply uvicorn's own logging config, as `uvicorn` does before it calls the app factory."""
    names = (*SERVER_LOGGERS, SERVER_ACCESS_LOGGER)
    saved = {
        name: (
            logging.getLogger(name).handlers[:],
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in names
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    yield
    for name, (handlers, level, propagate) in saved.items():
        server_logger = logging.getLogger(name)
        server_logger.handlers[:] = handlers
        server_logger.setLevel(level)
        server_logger.propagate = propagate
