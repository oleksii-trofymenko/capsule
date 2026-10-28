"""Shared test helpers: an in-process HTTP client and checks against contracts/openapi.yaml."""

import asyncio
import re
import threading
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path
from typing import Any

import httpx
import yaml
from alembic.config import Config
from fastapi import FastAPI
from jsonschema import Draft202012Validator
from pydantic import SecretBytes

from core.config import Settings, SigningKey
from modules.auth import hashing
from modules.auth.hashing import PasswordHashing

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "contracts" / "openapi.yaml"
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"
REQUEST_ID = re.compile(r"[A-Za-z0-9-]{1,64}")
# In memory, like the file `make up` writes; never a real key.
TEST_SIGNING_KEYS = (SigningKey("2026-01-01", SecretBytes(bytes(range(32)))),)


def dummy_settings(**overrides: object) -> Settings:
    """Settings that point nowhere; unit tests never open a connection."""
    values: dict[str, object] = {
        "database_url": "postgresql://capsule:dummy@db.invalid:5432/capsule",
        "redis_url": "redis://cache.invalid:6379/0",
        "signing_keys": TEST_SIGNING_KEYS,
    }
    return Settings.model_validate(values | overrides)


def alembic_config() -> Config:
    """apps/api/alembic.ini; env.py takes the database from DATABASE_URL."""
    return Config(ALEMBIC_INI)


@asynccontextmanager
async def client_for(app: FastAPI, *, lifespan: bool = False) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        if lifespan:
            async with app.router.lifespan_context(app):
                yield client
        else:
            yield client


@cache
def contract() -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    return spec


def schema_validator(schema: dict[str, Any]) -> Draft202012Validator:
    """Validator whose `#/components/...` references resolve inside the contract."""
    root = {"components": contract()["components"], **schema}
    return Draft202012Validator(root, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _resolve(obj: dict[str, Any]) -> dict[str, Any]:
    ref = obj.get("$ref")
    if ref is None:
        return obj
    node: Any = contract()
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return _resolve(node)


def assert_matches_contract(response: httpx.Response, path: str, method: str = "get") -> None:
    """Status, content type, body schema and X-Request-ID must be what the contract declares."""
    operation = contract()["paths"][path][method]
    declared = operation["responses"]
    status = str(response.status_code)
    assert status in declared, f"{method.upper()} {path} -> {status} is not in the contract"
    spec = _resolve(declared[status])

    if "content" in spec:
        media_type = response.headers["content-type"].split(";")[0].strip()
        assert media_type in spec["content"], f"{media_type} not declared for {status}"
        schema_validator(spec["content"][media_type]["schema"]).validate(response.json())
    else:
        assert response.content == b"", f"{status} declares no body"

    assert "X-Request-ID" in spec.get("headers", {})
    assert REQUEST_ID.fullmatch(response.headers["X-Request-ID"])


class BlockingHasher:
    """Stands in for the hasher's `hash` (patch `hashing._HASHER`): each call blocks its thread
    until `release` is set, and counts how many ran and how many ran at once."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.started = 0
        self.running = 0
        self.most_running = 0
        self._lock = threading.Lock()

    def hash(self, _: str) -> str:
        with self._lock:
            self.started += 1
            self.running += 1
            self.most_running = max(self.most_running, self.running)
        self.release.wait(5)
        with self._lock:
            self.running -= 1
        return "hashed"


async def wait_until(condition: Callable[[], bool], timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while not condition():
        assert time.monotonic() < deadline, "condition not reached"
        await asyncio.sleep(0.01)


async def fill_hash_slots(hasher: PasswordHashing, fake: BlockingHasher) -> list[asyncio.Task[str]]:
    """Every slot taken by a blocked hash; set `fake.release` and gather the tasks to free them."""
    tasks = [asyncio.create_task(hasher.hash("a test password")) for _ in range(hashing.SLOTS)]
    await wait_until(lambda: fake.started == hashing.SLOTS)
    return tasks
