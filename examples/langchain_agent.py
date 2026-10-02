"""Native LangChain safe, blocked, retrieved-content, and tool-calling paths."""

from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from pydantic import Field

from agent_guard import Guard
from agent_guard.checks.pii import LocalPIIDetector
from agent_guard.core.errors import PolicyViolationError
from agent_guard.integrations.langchain import InputGuardMiddleware, create_guarded_agent


@tool
def lookup(query: str) -> str:
    """Look up account contact details for the given query."""
    return "Contact secret@example.com for account details."


class ScriptedToolModel(BaseChatModel):
    """A real chat model that requests one tool call, then returns final text."""

    turns: list[AIMessage] = Field(default_factory=list)
    calls: list[int] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-model"

    def bind_tools(self, tools: object, **kwargs: object) -> "BaseChatModel":
        return self

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  run_manager: object = None, **kwargs: object) -> ChatResult:
        index = len(self.calls)
        self.calls.append(index)
        return ChatResult(generations=[ChatGeneration(message=self.turns[index])])


def main() -> None:
    guard = Guard(detector=LocalPIIDetector()).prepare()
    try:
        # Note: the local PII detector's split-content fallback text (every part
        # concatenated with no separator, to catch PII split across boundaries)
        # can make spaCy's NER misread bare single-word concatenations as a
        # PERSON entity. This example therefore uses realistic sentences rather
        # than single words like "hello"/"safe" to avoid that benign near-match;
        # see AC-26 and the false-positive-rate gates in evaluations/manifests/v1.md.
        agent = create_guarded_agent(FakeListChatModel(responses=["Everything looks good."]),
                                     tools=[], guard=guard)
        safe = agent.invoke({"messages": [{"role": "user", "content": "How can I help you today?"}]})
        print("direct:", safe["messages"][-1].content)
        try:
            agent.invoke({"messages": [{"role": "user", "content": "secret@example.com"}]})
        except PolicyViolationError as exc:
            print("blocked input:", exc.reason_code)

        middleware = InputGuardMiddleware(guard)
        request = ModelRequest(
            model=FakeListChatModel(responses=["Everything looks good."]),
            messages=[HumanMessage("Summarize the retrieval"),
                      ToolMessage("secret@example.com", tool_call_id="retrieval")],
        )
        try:
            middleware.wrap_model_call(request, lambda _: ModelResponse(
                [AIMessage("Everything looks good.")]))
        except PolicyViolationError as exc:
            print("blocked retrieved text:", exc.reason_code)

        # A real tool-calling loop: the first turn requests a tool call and is
        # allowed; the tool runs and its PII-bearing result is appended as a
        # ToolMessage; the second assembled model request is independently
        # rechecked and blocked before that second model call ever happens.
        tool_model = ScriptedToolModel(turns=[
            AIMessage("", tool_calls=[{"name": "lookup", "args": {"query": "account"},
                                       "id": "c1"}]),
            AIMessage("Here is the info you asked for."),
        ])
        tool_agent = create_guarded_agent(tool_model, tools=[lookup], guard=guard)
        try:
            tool_agent.invoke({"messages": [{"role": "user", "content": "How do I contact support?"}]})
        except PolicyViolationError as exc:
            print("blocked tool output on recheck:", exc.reason_code, "model calls:", tool_model.calls)
    finally:
        guard.close()


if __name__ == "__main__":
    main()
