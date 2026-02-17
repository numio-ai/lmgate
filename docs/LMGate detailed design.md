# LMGate MVP — Design Document

**Date**: 2026-02-16
**Input**: `docs/LMGate functional specification.md`

---

## 1. Architecture

LMGate is a two-process system: **nginx + njs** handles all client traffic, **LMGate (Python/aiohttp)** handles AuthZ decisions and stats collection.

```
                         ┌─────────────────────────────────────────┐
                         │              nginx + njs                │
  Client ──HTTP/1.1───►  │                                         │
         ◄────────────   │  auth_request ──► LMGate /auth          │
                         │                                         │
                         │  proxy_pass ────► LLM Provider API      │
                         │                                         │
                         │  njs: accumulate response body          │
                         │  njs: POST stats ──► LMGate /stats      │
                         └─────────────────────────────────────────┘

                         ┌─────────────────────────────────────────┐
                         │              LMGate (Python)            │
                         │                                         │
                         │  /auth endpoint (AuthZ decisions)       │
                         │  /stats endpoint (usage data collection)│
                         │  /healthz endpoint (readiness probe)    │
                         │  allow-list loader (CSV, poll reload)   │
                         └─────────────────────────────────────────┘
```

### Why two processes?

- **Maximize reuse**: nginx handles proxying, TLS, SSE streaming, and (post-MVP) HTTP/2 — no custom proxy code needed.
- **Minimal new code**: njs scripts are thin glue (~15 lines each). All business logic lives in Python.
- **Uniform REST interface**: nginx communicates with LMGate exclusively via HTTP (`/auth`, `/stats`) — consistent and debuggable, no shared filesystem for data exchange.

### Failure modes

- **AuthZ: fail closed** — if LMGate is unreachable, nginx returns 403.
- **Stats: fail open** — if the stats POST fails, proxying continues unaffected.

### Protocol support

| Protocol | MVP | Post-MVP |
|----------|-----|----------|
| HTTP/1.1 | Yes | Yes |
| SSE (streaming) | Yes (native nginx) | Yes |
| HTTP/2 (client-facing) | No | Config-only change (nginx native) |
| AWS EventStream | Yes (transparent byte streaming) | Yes |
| AWS SigV4 passthrough | Yes (headers/body untouched) | Yes |

---

## 2. Request Flow

Clients call LMGate with a provider prefix. nginx routes by prefix and strips it before proxying.

### 2.1 Happy Path (Non-Streaming)

1. Client sends request to `https://lmgate/<provider>/<path>`.
2. nginx issues `auth_request` to LMGate `/auth`.
3. LMGate extracts API key, checks allow-list, returns 200 + `X-LMGate-ID` header.
4. nginx `proxy_pass` to upstream provider.
5. njs `js_body_filter` accumulates response body into a variable.
6. nginx streams response to client unchanged.
7. *(after client response completes)* njs fire-and-forget POSTs metadata + response body to LMGate `/stats`.
8. LMGate parses response, extracts tokens, writes JSONL.

### 2.2 Key Design Decisions in the Flow

**`X-LMGate-ID` header correlation**: LMGate returns an internal key ID during `auth_request`. nginx passes it in the stats POST. This avoids LMGate needing to correlate auth and stats by API key later.

**njs body accumulation with cap**: njs copies response body chunks without blocking client streaming, enforcing a 2 MB cap. If exceeded, capture stops and token counts are marked `unknown`. njs never parses or interprets JSON — it forwards bytes only.

**AWS SigV4 passthrough**: nginx passes all headers and body unchanged. SigV4 integrity is preserved because the signed payload is never modified.

**SSE/streaming**: njs accumulates the full streamed body. Token counts are typically in the final SSE event. Best-effort extraction — if not found, stats entry has null token counts.

---

## 3. AuthZ Design

**Key extraction precedence** (first valid credential wins):
1. `Authorization: Bearer <key>`
2. `Authorization: AWS4-HMAC-SHA256 Credential=<AccessKeyId>/...` (extract Access Key ID only)
3. `x-api-key`

**Allow-list**: CSV file, loaded at startup (missing file = FATAL). Polled by mtime every 30s, atomically swapped on change. In-memory `dict[str, AllowListEntry]` for O(1) lookup.

---

## 4. Stats Design

**Ingestion**: njs POSTs a JSON envelope containing request metadata and the full response body. LMGate detects provider from the `host` field, parses `response_body` for token counts, and writes a JSONL record.

**Resilience**: Stats ingestion uses a bounded in-memory queue. Overflow drops stats entries but never blocks proxying. Graceful fallback — if response body is not JSON or token fields are missing, the entry is written with null token counts. Parse errors never crash the stats path.

**Output**: Append-only JSONL. Buffered async writes flushed on a configurable interval (default 10s). Size-based rotation with timestamp suffix.

---

## 5. Configuration Approach

- YAML config file as primary source.
- Environment variable overrides with `LMGATE_` prefix, double-underscore for nesting (e.g., `LMGATE_AUTH__POLL_INTERVAL_SECONDS`).
- nginx config is a separate file, not managed by the Python config system.

---

## 6. Out of Scope (MVP)

- TLS termination
- Stats query API / dashboard
- Multi-host / HA deployment
- Rate limiting
- Per-key permissions beyond allow/deny
