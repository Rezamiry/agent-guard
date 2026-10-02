"""Bounded provider HTTP transport."""

import json
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import AbstractContextManager
from math import isfinite
from time import monotonic

import anyio
import httpx
from anyio.from_thread import BlockingPortal, start_blocking_portal

from agent_guard.core.errors import ConfigurationError, EvaluationError, IntegrationError

URL = "https://openrouter.ai/api/alpha/decisions"
MAX_REQUEST_BYTES = 512 * 1024
MAX_RESPONSE_BYTES = 256 * 1024


class JevTransport:
    def __init__(self, credential: str, *, timeout: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if not isinstance(credential, str) or not credential.strip() or any(
            char in credential for char in "\r\n"
        ):
            raise ConfigurationError("provider_credential_required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or (
            not isfinite(timeout) or not 0.1 <= timeout <= 120.0
        ):
            raise ConfigurationError("invalid_provider_deadline")
        self.credential = credential
        self.timeout = float(timeout)
        self.transport = transport
        self._client: httpx.AsyncClient | None = None
        self._portal_cm: AbstractContextManager[BlockingPortal] | None = None
        self._portal: BlockingPortal | None = None
        self._submission_pool: ThreadPoolExecutor | None = None

    def prepare(self) -> "JevTransport":
        if self._portal is not None:
            return self
        portal_cm = start_blocking_portal()
        portal = portal_cm.__enter__()
        try:
            portal.call(self.aprepare)
        except BaseException:
            portal_cm.__exit__(None, None, None)
            raise
        self._portal_cm = portal_cm
        self._portal = portal
        self._submission_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jev-submit")
        return self

    async def aprepare(self) -> "JevTransport":
        self._client = httpx.AsyncClient(
            transport=self.transport, timeout=None, follow_redirects=False, trust_env=False,
        )
        return self

    async def apost(self, payload: dict[str, object]) -> object:
        return await self._apost(payload, monotonic() + self.timeout)

    async def _apost(self, payload: dict[str, object], deadline: float) -> object:
        if self._client is None:
            raise ConfigurationError("provider_not_prepared")
        try:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            raise IntegrationError("provider_request_invalid") from None
        if len(body) > MAX_REQUEST_BYTES:
            raise IntegrationError("provider_request_oversized")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise EvaluationError("provider_timeout")
        try:
            with anyio.fail_after(remaining):
                async with self._client.stream(
                    "POST", URL, content=body,
                    headers={"Authorization": "Bearer " + self.credential,
                             "Content-Type": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        raise EvaluationError("provider_http_error")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise EvaluationError("provider_response_oversized")
                        chunks.append(chunk)
                raw = b"".join(chunks)
                data = await anyio.to_thread.run_sync(json.loads, raw, abandon_on_cancel=True)
                if monotonic() >= deadline:
                    raise EvaluationError("provider_timeout")
                return data
        except TimeoutError:
            raise EvaluationError("provider_timeout") from None
        except httpx.HTTPError:
            raise EvaluationError("provider_unavailable") from None
        except (UnicodeError, json.JSONDecodeError):
            raise EvaluationError("provider_response_invalid") from None

    def post(self, payload: dict[str, object]) -> object:
        deadline = monotonic() + self.timeout
        if self._portal is None or self._submission_pool is None:
            raise ConfigurationError("provider_not_prepared")
        submission = self._submission_pool.submit(
            self._portal.start_task_soon, self._apost, payload, deadline,
        )
        try:
            future = submission.result(timeout=max(0.0, deadline - monotonic()))
        except FutureTimeoutError:
            submission.cancel()
            raise EvaluationError("provider_timeout") from None
        try:
            return future.result(timeout=max(0.0, deadline - monotonic()))
        except FutureTimeoutError:
            future.cancel()
            raise EvaluationError("provider_timeout") from None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def close(self) -> None:
        if self._portal is not None and self._portal_cm is not None:
            self._portal.call(self.aclose)
            self._portal_cm.__exit__(None, None, None)
            self._portal = None
            self._portal_cm = None
        if self._submission_pool is not None:
            self._submission_pool.shutdown(wait=False, cancel_futures=True)
            self._submission_pool = None
