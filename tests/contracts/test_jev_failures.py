import asyncio
import json
from threading import Event
from time import monotonic, sleep

import anyio
import httpx
import pytest

import agent_guard.providers.transport as transport_module
from agent_guard.core.errors import ConfigurationError, EvaluationError, IntegrationError
from agent_guard.providers.transport import JevTransport


@pytest.mark.parametrize("timeout", [0, -1, 0.09, 120.01, float("inf"), float("nan")])
def test_invalid_total_deadline_fails_local_setup(timeout: float) -> None:
    with pytest.raises(ConfigurationError):
        JevTransport("token", timeout=timeout)


def test_deadline_bounds_and_default_are_accepted_without_network() -> None:
    assert JevTransport("token").timeout == 10.0
    assert JevTransport("token", timeout=0.1).timeout == 0.1
    assert JevTransport("token", timeout=120.0).timeout == 120.0


async def test_one_attempt_and_immediate_completed_error() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["authorization"] == "Bearer token"
        return httpx.Response(429, json={"detail": "secret@example.com"})

    transport = await JevTransport("token", transport=httpx.MockTransport(handler)).aprepare()
    started = monotonic()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"model": "typesafe/jev-1.13"})
        assert error.value.reason_code == "provider_http_error"
        assert "secret@example.com" not in str(error.value)
        assert calls == 1
        assert monotonic() - started < 2
    finally:
        await transport.aclose()


@pytest.mark.parametrize("status", [302, 401, 403, 429, 503])
async def test_rejection_and_redirect_make_one_attempt_without_fallback(status: int) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, headers={"location": "https://example.invalid/redirect"},
                              content=b"secret@example.com")

    transport = await JevTransport("token", transport=httpx.MockTransport(handler)).aprepare()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"state": "safe"})
        assert error.value.reason_code == "provider_http_error"
        assert "secret@example.com" not in str(error.value)
        assert calls == 1
    finally:
        await transport.aclose()


async def test_network_unavailable_is_sanitized_evaluation_error() -> None:
    calls = 0

    async def unavailable(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("credential=top-secret")

    transport = await JevTransport("token", transport=httpx.MockTransport(unavailable)).aprepare()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"state": "safe"})
        assert error.value.reason_code == "provider_unavailable"
        assert "top-secret" not in str(error.value)
        assert calls == 1
    finally:
        await transport.aclose()


async def test_cancellation_propagates_without_retry() -> None:
    calls = 0
    entered = asyncio.Event()

    async def slow(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await anyio.sleep(1)
        return httpx.Response(200, json={"ok": True})

    transport = await JevTransport("token", transport=httpx.MockTransport(slow)).aprepare()
    try:
        task = asyncio.create_task(transport.apost({"state": "safe"}))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert calls == 1
    finally:
        await transport.aclose()


async def test_total_deadline_bounds_slow_response_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def response(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b'{"ok":true}')

    def slow_decode(raw: bytes) -> object:
        sleep(0.3)
        return {"ok": True}

    monkeypatch.setattr(transport_module.json, "loads", slow_decode)
    transport = await JevTransport("token", timeout=0.1,
                                   transport=httpx.MockTransport(response)).aprepare()
    started = monotonic()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"state": "safe"})
        assert error.value.reason_code == "provider_timeout"
        assert monotonic() - started < 0.25
        assert calls == 1
    finally:
        await transport.aclose()


def test_sync_total_deadline_includes_portal_queue_wait() -> None:
    calls = 0
    occupied = Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=b'{"ok":true}')

    async def occupy_portal() -> None:
        occupied.set()
        sleep(0.3)  # noqa: ASYNC251 - deliberately block the portal queue

    transport = JevTransport("token", timeout=0.1,
                             transport=httpx.MockTransport(handler)).prepare()
    assert transport._portal is not None
    blocker = transport._portal.start_task_soon(occupy_portal)
    assert occupied.wait(timeout=1)
    started = monotonic()
    try:
        with pytest.raises(EvaluationError) as error:
            transport.post({"state": "safe"})
        assert error.value.reason_code == "provider_timeout"
        assert monotonic() - started < 0.25
        blocker.result(timeout=1)
        assert calls == 0
    finally:
        transport.close()


async def test_request_limit_rejects_before_attempt() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    transport = await JevTransport("token", transport=httpx.MockTransport(handler)).aprepare()
    try:
        with pytest.raises(IntegrationError):
            await transport.apost({"state": "x" * (512 * 1024)})
        assert calls == 0
    finally:
        await transport.aclose()


async def test_response_limit_and_total_deadline() -> None:
    async def oversized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (256 * 1024 + 1))

    transport = await JevTransport("token", transport=httpx.MockTransport(oversized)).aprepare()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"state": "safe"})
        assert error.value.reason_code == "provider_response_oversized"
    finally:
        await transport.aclose()

    async def slow(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(0.3)
        return httpx.Response(200, content=json.dumps({"ok": True}).encode())

    transport = await JevTransport("token", timeout=0.1,
                                   transport=httpx.MockTransport(slow)).aprepare()
    try:
        with pytest.raises(EvaluationError) as error:
            await transport.apost({"state": "safe"})
        assert error.value.reason_code == "provider_timeout"
    finally:
        await transport.aclose()
