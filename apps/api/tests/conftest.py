import asyncio
import logging
import sys
from collections.abc import Iterator

import pytest

from core.logging import QUIET_LOGGERS


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
