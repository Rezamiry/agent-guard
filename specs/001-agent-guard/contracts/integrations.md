# Native Integration Contract

**Authority**: [Native Integration Coverage in the spec](../spec.md), FR-31–FR-34, and AC-32–AC-34. This contract describes v1 supported arrangements only. Pin and execute against the selected framework versions before advertising compatibility.

## Shared adapter rules

Each adapter validates its declared topology and supported content before protected execution when those facts are visible. At every model submission it inspects the exact assembled model-bound snapshot after history, retrieval, context providers, and supported middleware additions. A changed snapshot after a previous decision is checked again. A known later mutator that can bypass the last observable guard causes a configuration failure. If arbitrary host code changes content outside the adapter's observable boundary, documentation names that limitation; the adapter must not claim universal interception.

Supported native content is text strings and text parts of system, user, assistant, and tool messages, plus developer messages where exposed, textual evidence, model-bound tool descriptions, and every string key and value of JSON-compatible tool arguments. Keep roles, part order, argument structure, and non-text scalar values. Reject opaque/multimodal content, excess context size, and unsupported language/shape explicitly. Never stringify an unknown native object or silently omit a text field. Apply the same inspection rule to final answers and extra context sent for output evaluation. See [data-model.md](../data-model.md) for inclusive limits and identity rules.

At the final boundary, inspect only a declared completed answer. Intermediate tool requests or model replies intended for tools are not final answers. Allowed native results, metadata, message IDs, and state updates pass through unchanged and protected host work occurs once. A block withholds final delivery but does not reverse earlier model cost, tool effects, graph checkpointing, or host tracing. Cancellation and caller exceptions propagate.

| Failure point | Classification |
| --- | --- |
| Known incompatible registration, missing declared boundary, known later mutator, or unsupported visible setup | Configuration failure before protected work. |
| Unexpected runtime content extraction, boundary identification, or native result/state preservation fault | Integration failure; stop affected submission/delivery regardless of optional policy status. |
| Detector/provider failure after valid setup | Evaluation error; required blocks, optional records. |
| Host operation exception or cancellation | Preserve original exception/cancellation. |

## LangChain

The supported arrangement is a native non-streaming agent with ordinary and asynchronous paths. A model-call wrapper guards each assembled request before its model call; a final agent hook guards the completed answer after supported output transformations and before caller return. The guard must observe the system message, request messages, text parts, and model-bound tool fields. Register the input guard closest to the model and the final-output guard as the last observer of the returned answer. If a later middleware component can mutate model-bound content or final output after the respective guard, reject the arrangement unless a later guard boundary rechecks the changed content. Preserve native response and state semantics.

An agent request may call the model more than once. Each model-bound snapshot requires its own input decision. The final hook runs for direct and retrieval answers, not each intermediate tool request. A non-streaming facade rejects streaming/event-stream entry before protected work. Direct calls that bypass the facade are outside its documented coverage.

## LangGraph

The supported arrangement is a declared non-streaming graph with ordinary and asynchronous invocation. The host declares each model submission and each final-answer-producing path. Its topology places assembly before an input guard that inspects the exact content the next model call consumes, and an output guard on every direct or retrieval final path before return. If a node privately builds or changes a prompt after a prior guard node, the model-boundary guard must run inside that observable submission path; otherwise the arrangement is unsupported. An allow guard contributes no unrelated state mutation. Preserve native state reducers, message identifiers, invocation config, and returned state.

An arbitrary graph with undeclared model calls or final paths is not represented as fully protected. Streaming/event-stream entry is rejected before protected work by the supported facade; direct graph access outside it is documented as uncovered. Identifiable evidence must be associated with the answer-generation step, never inferred merely from an arbitrary tool message.

## Microsoft Agent Framework Python

The supported native agent path is asynchronous. Chat-level middleware guards each model request after context-provider additions; agent-level middleware guards the completed agent result before delivery. Chat-level inspection repeats when a tool cycle causes another model call. Host-provided evidence identity and final-answer boundaries remain explicit. A synchronous native agent API is not promised; an ordinary Python script may run the async path through its own async entry point.

Use the callback and context contracts of the pinned installed package, preserve the native result and metadata, and reject a pipeline order that can mutate model-bound content after the last guard. The project's research found documentation drift in Microsoft context/callback names; an executable contract check against the pinned package is required before claiming the integration works.

## Acceptance evidence

For every supported framework and execution surface, controlled native-object cases cover safe and blocked input/output, direct and retrieval final answers, metadata/state preservation, multiple model submissions, provider-added or middleware-added PII, exact-limit and over-limit content, unsupported multimodal content, streaming rejection, early block side effects, and caller cancellation/errors. Fault cases distinguish setup incompatibility from unexpected runtime adapter failures and show that optional check status cannot allow an unguarded native handoff. The expected result for each case is established independently before implementation execution, per the constitution.

Official framework references used for the design: [LangChain middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom), [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api), and [Microsoft agent pipeline](https://learn.microsoft.com/en-us/agent-framework/agents/agent-pipeline). These references inform planned placement; installed-version behavior remains an acceptance gate.
