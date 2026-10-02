# External Judgment Provider Contract

**Initial provider**: OpenRouter Decisions with Jev. This is an opt-in evaluation path; the default required local PII policy does not call it. [Research R4–R5](../research.md) records the selected wire and deadline decisions.

## Request

One enabled semantic check at one boundary makes at most one HTTP `POST` to `https://openrouter.ai/api/alpha/decisions`. Use `Authorization: Bearer <credential>` and JSON with `model: "typesafe/jev-1.13"`, exactly one named `questions` entry of `type: "choice"`, explicit `pass` and `violation` criteria, separate policy `instructions`, a `state` containing only the locally inspected evaluation content, and `provider.allow_fallbacks: false`. Do not add user identifiers, session IDs, raw traces, or automatic telemetry fields. No retry, redirect, evaluator fallback, or retry-window waiting is permitted.

The local PII preflight covers every content field sent to the provider, including candidate output, conversation context, evidence, and any supplied text embedded in custom criteria. Required PII findings or failures stop the request. Accepted outbound JSON is at most 512 KiB; no truncation. The chosen message/content forms and context limits come from [data-model.md](../data-model.md).

## Response

Read at most 256 KiB. Require the requested answer key and a `choice` answer with `choice` exactly `pass` or `violation`; require finite `confidence` in [0, 1] even if upstream omits it. An unexpected model identity, unknown choice/type, missing/malformed required field, or contradictory answer is an evaluation error, never a pass. A valid confidence equal to the configured minimum is accepted; lower confidence is inconclusive. The default semantic minimum is 0.80, configurable within [0, 1]. Preserve available model identity, token usage, and cost; unknown cost stays unknown. Do not copy raw provider responses into routine records or exceptions.

## Deadline and failures

The default total elapsed-time deadline is 10.0 seconds; valid configuration is finite 0.1–120.0 seconds. Start a monotonic timer when judgment invocation begins, before queueing; bound send, wait, body read, decode, and validation. A completed provider error reports immediately. Timeout, 429, rejected credentials after valid setup, other HTTP failures, unavailable service, and invalid response are evaluation errors governed by required/optional policy status. Cancellation remains cancellation. The sync surface uses a cancellable async operation through a prepared portal; the async surface uses cancellable async I/O.

## Contract evidence

Deterministic contract fixtures are authored from the official request/answer shapes, then held fixed before code execution. Cover valid pass/violation, confidence equality and below-minimum, absent confidence, wrong answer key, unexpected model, unknown label, 429, timeout, oversized body, and cancellation. No live network or API key is needed for those cases. A separately enabled provider smoke test may establish actual connectivity but cannot replace deterministic expectations.

Primary shape references: [request](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionsrequest.py), [choice question](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionschoicequestion.py), [choice answer](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionschoiceanswer.py), [response](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/decisionsresponse.py), and [provider preferences](https://raw.githubusercontent.com/OpenRouterTeam/python-sdk/main/src/openrouter/components/providerpreferences.py). Validate the pinned provider contract before implementation; current upstream source is research evidence, not a claim of live compatibility.
