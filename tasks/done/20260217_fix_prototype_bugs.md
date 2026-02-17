---
status: done
---

# Fix Prototype Implementation Bugs

**Date**: 2026-02-17

## Problem

User guide verification revealed 3 implementation bugs where actual behavior diverges from documented behavior:

1. **Bedrock routing missing** — nginx.conf has no `/bedrock/` location block. Bedrock requests return 404.
2. **Allow-list polling not wired** — `AllowList.reload_if_changed()` exists but is never called. Allow-list changes require a restart despite docs saying otherwise.
3. **Provider detection broken in stats** — njs reads `r.headersOut["X-Upstream-Host"]` which is never set by nginx or upstream providers. Stats always show `provider: "unknown"`.

## Scope

**In scope:**
- Add `/bedrock/` upstream + location block (default region us-east-1)
- Wire `reload_if_changed()` into an asyncio periodic task using `poll_interval_seconds`
- Pass upstream host to njs via nginx variable (`$upstream_host`) instead of response header

**Out of scope:**
- Making bedrock region dynamically configurable via envsubst
- User guide changes (re-verify after fixes)

## Acceptance Criteria

- [x] `/bedrock/` requests route to `bedrock-runtime.us-east-1.amazonaws.com`
- [x] Allow-list CSV changes are picked up without restart
- [x] Stats records show correct provider (openai, anthropic, google, bedrock)
- [x] All existing tests pass
- [x] No new test regressions

## Quality Gates

- [x] `pytest` passes (all 75 tests)
- [x] Manual review of each changed file
