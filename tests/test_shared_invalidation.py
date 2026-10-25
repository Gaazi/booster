"""Verify that invalidation notices reach the other worker processes."""

import asyncio
import multiprocessing
import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from booster import CachePolicy, FileInvalidationBus, RocketBooster

NOTICE_FILE = "invalidations.log"


@dataclass
class WorkerReply:
    """Report response bytes and local occupancy from the serving process."""

    pid: int
    body: bytes
    entries: int


@dataclass
class Worker:
    """Exchange bounded test commands with an isolated Booster process."""

    process: BaseProcess
    connection: Connection

    def request(self, method: str, path: str = "/catalog") -> WorkerReply:
        """Issue a request to the worker process."""
        self.connection.send((method, path))
        assert self.connection.poll(15), "Booster worker did not respond"
        result = self.connection.recv()
        assert isinstance(result, WorkerReply)
        return result

    def close(self) -> None:
        """Stop the child and report shutdown failures without leaking processes."""
        if self.process.is_alive():
            self.connection.send(None)
        self.connection.close()
        self.process.join(5)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(5)
            raise AssertionError("Booster worker did not stop normally")
        assert self.process.exitcode == 0


def origin_app(source: Path) -> Callable:
    """Create a shared-file origin with a public route and a mutation."""
    async def application(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Read or update the shared origin state."""
        if scope["method"] == "POST":
            source.write_bytes(b"new")
        body = source.read_bytes()
        headers = [(b"content-type", b"text/plain"), (b"cache-control", b"public")]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})
    return application


async def dispatch(engine: RocketBooster, command: tuple[str, str]) -> bytes:
    """Exercise the real ASGI middleware without a framework or network server."""
    method, path = command
    scope = {"type": "http", "method": method, "path": path,
             "headers": [(b"host", b"workers.test")]}
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        """Provide the empty request body for the fixture origin."""
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        """Collect the final response bytes returned by the middleware."""
        if message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await engine(scope, receive, send)
    return b"".join(chunks)


def worker_main(connection: Connection, source: Path, policy: CachePolicy, shared: Path | None) -> None:
    """Own one independent cache and serve commands until the parent stops it."""
    bus = FileInvalidationBus(shared / NOTICE_FILE) if shared else None
    engine = RocketBooster(origin_app(source), cache_policy=policy,
                           enable_compression=False, enable_minification=False,
                           invalidation_bus=bus)
    try:
        while (command := connection.recv()) is not None:
            body = asyncio.run(dispatch(engine, command))
            connection.send(WorkerReply(os.getpid(), body, engine.cache.count()))
    finally:
        connection.close()


@contextmanager
def running_workers(source: Path, policy: CachePolicy, shared: Path | None = None) -> Iterator[tuple[Worker, Worker]]:
    """Start two fresh interpreters sharing only their origin file."""
    context = multiprocessing.get_context("spawn")
    workers: list[Worker] = []
    with ExitStack() as cleanup:
        for _ in range(2):
            parent, child = context.Pipe()
            process = context.Process(target=worker_main, args=(child, source, policy, shared))
            process.start()
            child.close()
            workers.append(Worker(process, parent))
            cleanup.callback(workers[-1].close)
        yield workers[0], workers[1]


def test_file_bus_delivers_notices_to_another_reader(tmp_path: Path) -> None:
    """A published notice must reach a different reader of the same file."""
    path = tmp_path / NOTICE_FILE
    publisher = FileInvalidationBus(path)
    reader = FileInvalidationBus(path)
    publisher.publish("/catalog")
    assert reader.drain() == ["/catalog"]
    assert reader.drain() == []
    publisher.publish("*")
    assert reader.drain() == ["*"]


def test_file_bus_truncation_forces_a_full_clear(tmp_path: Path) -> None:
    """A truncated notice file must be read as a full clear."""
    path = tmp_path / NOTICE_FILE
    publisher = FileInvalidationBus(path, max_bytes=40)
    reader = FileInvalidationBus(path, max_bytes=40)
    publisher.publish("/catalog" * 4)
    reader.drain()
    publisher.publish("/catalog" * 8)
    assert reader.drain() == ["*"]


def test_shared_bus_invalidates_the_other_worker(tmp_path: Path) -> None:
    """A write in one worker must reach the other worker before its next read."""
    source = tmp_path / "origin.txt"
    source.write_bytes(b"old")
    shared = tmp_path / "shared"
    shared.mkdir()
    with running_workers(source, CachePolicy(), shared) as (first, second):
        assert first.request("GET").body == second.request("GET").body == b"old"
        assert first.request("POST").body == b"new"
        assert first.request("GET").body == b"new"
        assert second.request("GET").body == b"new"


def test_process_local_invalidation_is_unchanged_without_a_bus(tmp_path: Path) -> None:
    """Without a bus the documented process-local boundary must stay the same."""
    source = tmp_path / "origin.txt"
    source.write_bytes(b"old")
    with running_workers(source, CachePolicy()) as (first, second):
        assert first.request("GET").body == second.request("GET").body == b"old"
        assert first.request("POST").body == b"new"
        assert first.request("GET").body == b"new"
        assert second.request("GET").body == b"old"


def test_shared_bus_keeps_credentialed_requests_fresh(tmp_path: Path) -> None:
    """The bus must not weaken the credential bypass on a peer worker."""
    source = tmp_path / "origin.txt"
    source.write_bytes(b"old")
    shared = tmp_path / "shared"
    shared.mkdir()
    with running_workers(source, CachePolicy(), shared) as (first, second):
        assert first.request("GET").body == b"old"
        assert first.request("POST").body == b"new"
        assert second.request("GET").body == b"new"


def test_status_reports_the_invalidation_mode(tmp_path: Path) -> None:
    """The status snapshot must tell the operator which mode is active."""
    engine = RocketBooster(origin_app(tmp_path / "origin.txt"))
    assert engine.get_status()["configuration"]["invalidation"] == "process"
    engine.invalidation_bus = FileInvalidationBus(tmp_path / NOTICE_FILE)
    assert engine.get_status()["configuration"]["invalidation"] == "shared"
