# Security policy

Agent Guard is alpha software. It is a defense-in-depth layer for agent inputs and outputs, not a
compliance guarantee. See the README's "What it does not do" section for known limits.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** using GitHub's
[private vulnerability reporting](https://github.com/Rezamiry/agent-guard/security/advisories/new)
rather than a public issue. Include the affected version, a minimal reproduction using synthetic
data, and the impact you observed.

Do not include real personal data, credentials or provider payloads in a report.

## Scope

In scope: a way to make a required check allow content its policy should block, to make the
library send content to an evaluator before the local PII check, or to leak checked text into a
decision, report or log.

Out of scope: detection-quality misses on inputs outside the documented limits (these are
welcome as ordinary issues with synthetic examples), and content that never passes through a
guarded boundary.
