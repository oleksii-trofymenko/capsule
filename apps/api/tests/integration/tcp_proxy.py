"""A TCP proxy for tests: forwards to a real service until `stall()`, then stops forwarding.

While stalled, connections stay open and accepted but no byte moves in either direction, which
is what a frozen or partitioned server looks like to the client. CI service containers cannot be
paused from the job, so this stands in for `docker pause`.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class StallingProxy:
    def __init__(self, upstream_host: str, upstream_port: int) -> None:
        self.upstream = (upstream_host, upstream_port)
        self.port = 0
        self._forwarding = asyncio.Event()
        self._forwarding.set()
        self._writers: set[asyncio.StreamWriter] = set()
        self._pumps: set[asyncio.Task[None]] = set()

    def stall(self) -> None:
        self._forwarding.clear()

    def resume(self) -> None:
        self._forwarding.set()

    async def _pump(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        with contextlib.suppress(ConnectionError, OSError):
            while data := await reader.read(65536):
                await self._forwarding.wait()  # data read while stalled is held, not forwarded
                writer.write(data)
                await writer.drain()
        writer.close()

    async def _accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._track(asyncio.current_task())
        self._writers.add(writer)
        await self._forwarding.wait()  # a new connection is accepted but gets no reply
        up_reader, up_writer = await asyncio.open_connection(*self.upstream)
        self._writers.add(up_writer)
        self._track(asyncio.create_task(self._pump(reader, up_writer)))
        self._track(asyncio.create_task(self._pump(up_reader, writer)))

    def _track(self, task: asyncio.Task[None] | None) -> None:
        if task is not None:
            self._pumps.add(task)
            task.add_done_callback(self._pumps.discard)

    @asynccontextmanager
    async def running(self) -> AsyncIterator["StallingProxy"]:
        server = await asyncio.start_server(self._accept, "127.0.0.1", 0)
        self.port = server.sockets[0].getsockname()[1]
        try:
            yield self
        finally:
            server.close()
            for task in list(self._pumps):
                task.cancel()
            await asyncio.gather(*self._pumps, return_exceptions=True)
            for writer in self._writers:
                writer.close()
            await server.wait_closed()
