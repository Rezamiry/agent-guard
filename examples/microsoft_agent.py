"""Native async Microsoft agent with a context provider adding retrieved text."""

import asyncio

from agent_framework import ChatMiddlewareLayer, ChatResponse, ContextProvider, Message

from agent_guard import Guard
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.errors import PolicyViolationError
from agent_guard.integrations.microsoft import create_guarded_agent


class RetrievedText(ContextProvider):
    def __init__(self, text: str) -> None:
        super().__init__("retrieval")
        self.text = text

    async def before_run(self, *, agent, session, context, state) -> None:
        context.extend_messages(self, [Message("tool", [self.text])])


class RawFakeClient:
    async def get_response(self, messages, **kwargs):
        return ChatResponse(messages=[Message("assistant", ["safe"])])


class FakeClient(ChatMiddlewareLayer, RawFakeClient):
    def __init__(self) -> None:
        super().__init__()


async def main() -> None:
    guard = await Guard(detector=LocalPIIDetector()).aprepare()
    try:
        safe = create_guarded_agent(FakeClient(), guard,
                                    context_providers=(RetrievedText("Safe source text"),))
        print("retrieval:", (await safe.run([Message("user", ["hello"])] )).text)
        blocked = create_guarded_agent(FakeClient(), guard,
                                       context_providers=(RetrievedText("secret@example.com"),))
        try:
            await blocked.run([Message("user", ["hello"])])
        except PolicyViolationError as exc:
            print("blocked retrieved text:", exc.reason_code)
    finally:
        await guard.aclose()


if __name__ == "__main__":
    asyncio.run(main())
