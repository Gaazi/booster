"""Verify process-local invalidation and the safe static-only deployment policy."""

import asyncio
import multiprocessing
import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any, Callable, Iterator

from booster import CachePolicy, RocketBooster


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

    def request(self, method: str, path: str = "/catalog", cookie: str = "") -> WorkerReply:
        """Issue a request or a process-local cache-clear command."""
        self.connection.send((method, path, cookie))
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
    """Create a shared-file origin with public, private and mutation responses."""
    async def application(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """Read or update the same origin state from either worker."""
        if scope["method"] == "POST":
            source.write_bytes(b"new")
        private = any(key == b"cookie" for key, _ in scope["headers"])
        body = (b"private:" if private else b"") + source.read_bytes()
        control = b"private, no-store" if private else b"public"
        headers = [(b"content-type", b"text/plain"), (b"cache-control", control)]
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": body})
    return application


async def dispatch(engine: RocketBooster, command: tuple[str, str, str]) -> bytes:
    """Exercise the real ASGI middleware without a framework or network server."""
    method, path, cookie = command
    headers = [(b"host", b"workers.test")]
    if cookie:
        headers.append((b"cookie", cookie.encode("ascii")))
    scope = {"type": "http", "method": method, "path": path, "headers": headers}
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


def worker_main(connection: Connection, source: Path, policy: CachePolicy) -> None:
    """Own one independent cache and serve commands until the parent stops it."""
    engine = RocketBooster(origin_app(source), cache_policy=policy,
                           enable_compression=False, enable_minification=False)
    try:
        while (command := connection.recv()) is not None:
            if command[0] == "CLEAR":
                engine.cache.clear()
                body = b""
            else:
                body = asyncio.run(dispatch(engine, command))
            connection.send(WorkerReply(os.getpid(), body, engine.cache.count()))
    finally:
        connection.close()


@contextmanager
def running_workers(source: Path, policy: CachePolicy) -> Iterator[tuple[Worker, Worker]]:
    """Start two fresh interpreters sharing only their origin file."""
    context = multiprocessing.get_context("spawn")
    workers: list[Worker] = []
    with ExitStack() as cleanup:
        for _ in range(2):
            parent, child = context.Pipe()
            process = context.Process(target=worker_main, args=(child, source, policy))
            process.start()
            child.close()
            workers.append(Worker(process, parent))
            cleanup.callback(workers[-1].close)
        yield workers[0], workers[1]


def test_mutation_and_admin_clear_are_process_local(tmp_path: Path) -> None:
    """Prove the stale peer boundary and explicit all-worker invalidation recovery."""
    source = tmp_path / "origin.txt"
    source.write_bytes(b"old")
    with running_workers(source, CachePolicy()) as (first, second):
        left, right = first.request("GET"), second.request("GET")
        assert left.pid != right.pid and left.pid != os.getpid()
        assert left.body == right.body == b"old"
        assert left.entries == right.entries == 1
        assert first.request("POST").body == b"new"
        assert first.request("GET").body == b"new"
        assert second.request("GET").body == b"old"
        assert second.request("GET", cookie="session=secret").body == b"private:new"
        assert first.request("CLEAR").entries == 0
        assert second.request("GET").body == b"old"
        assert second.request("CLEAR").entries == 0
        assert second.request("GET").body == b"new"
        assert second.request("GET", cookie="session=other").body == b"private:new"
        assert second.request("GET").body == b"new"


def test_static_only_policy_keeps_mutable_routes_fresh_across_workers(tmp_path: Path) -> None:
    """Avoid stale mutable pages without adding a distributed cache dependency."""
    source = tmp_path / "origin.txt"
    source.write_bytes(b"old")
    with running_workers(source, CachePolicy(include_paths=("/static/",))) as workers:
        first, second = workers
        assert first.request("GET").body == second.request("GET").body == b"old"
        assert first.request("GET").entries == second.request("GET").entries == 0
        assert first.request("GET", "/static/app.v1.css").entries == 1
        assert second.request("GET", "/static/app.v1.css").entries == 1
        assert first.request("POST").body == b"new"
        assert first.request("GET").body == second.request("GET").body == b"new"
        assert second.request("GET", "/static/app.v2.css").body == b"new"
        assert second.request("GET", "/static/app.v1.css").body == b"old"
