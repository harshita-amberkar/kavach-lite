# KAVACH Lite — focused security and privacy review

**Review date:** 2026-10-30
**Review type:** Static source-snapshot review; not a penetration test or certification.

> **Historical snapshot, superseded for current implementation status.** This
> review was based on an older checkout and explicitly did not inspect
> several then-current files. Its findings and recommendations below describe
> that snapshot only. See the 4 November 2026 addendum at the end for controls
> verified against the current source. Neither review is a certification.

## Source evidence and limitations

This review inspected:

- `app.py` Library snapshot last modified 2026-10-25 (23,649 bytes).
- `kavach/global_detector.py` source printed in a PowerShell capture dated 2026-10-28.
- `extension/content.js` source printed in a PowerShell capture dated 2026-10-30.
- Prior project handoff and previously reported tests.

The latest Windows checkout was not mounted in this session. The review did not inspect the latest `agent.py`, `agent_runtime.py`, `agentic.py`, `audit.py`, all extension manifest/background files, or run live browser/network tests. Therefore, statements below are limited to the source excerpts available and should be checked against the current checkout.

## Positive controls visible in the inspected backend snapshot

1. **API token gate:** protected `/api/*` routes (except `/api/health`) and `/v1/chat/completions` require `X-KAVACH-Token`, compared with `secrets.compare_digest`.
2. **Browser-origin check:** write requests with an `Origin` header are checked against the request origin.
3. **Host restriction:** `TrustedHostMiddleware` uses the configured `KAVACH_ALLOWED_HOSTS`, defaulting to `127.0.0.1,localhost`.
4. **Upstream destination controls:** public upstreams require HTTPS and an exact hostname allowlist; local mock use requires explicit opt-in. The HTTP client disables environment proxy trust and redirects.
5. **Proxy input limits:** chat body is capped at 1 MiB, message count at 100, each text message at 20,000 characters, and streaming is rejected.
6. **Allowlisted proxy payload:** only selected request fields are forwarded, and each message content is replaced with `masked_text` before the upstream request is made.
7. **Document limits:** uploads are capped at 5 MiB and PDFs at 20 pages; only TXT/PDF are accepted. Scanned-image PDFs without extractable text are rejected.
8. **Extension content-script behaviour:** the inspected content script reads per-type policy from `chrome.storage.sync` and performs `Kavach.scan`, `Kavach.decide`, and `Kavach.mask` in the content-script path. It contains handlers for Enter and send-button clicks. No direct `fetch`, XHR, `sendBeacon` or WebSocket call was visible in this source excerpt; the whole extension was not audited.

## Priority findings

### Resolved finding ? extension privacy wording needed context

The earlier options page said that nothing typed was ever sent anywhere by KAVACH. That statement was too absolute. The extension options page and manifest description have now been revised.

The current wording distinguishes the extension's in-browser prompt scanning, per-type policy settings stored with `chrome.storage.sync`, and submission of a prompt to the destination AI provider. The inspected extension JavaScript contains no direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or WebSocket calls. The manifest requests the Chrome `storage` permission and declares no host permissions.

**Remaining limitation:** this is a static source inspection, not a browser runtime network trace or a complete privacy audit of Chrome Sync and the destination AI provider. The extension statement applies only to the extension path. The separate FastAPI chat proxy forwards masked prompt content to its configured upstream and must be assessed independently.

### P1 — Presidio language is explicitly English in the global detector

The inspected `analyze_global()` calls `analyzer.analyze(..., language="en")`. This limits the Presidio recognizer pass to English. Existing KAVACH-specific normalisation or rules may support selected Indian-language digit formats, but the global Presidio pass should not be described as multilingual.

**Action:** document supported language behaviour accurately; add labelled Hindi, Marathi, Hinglish and Devanagari-digit cases to evaluation. Add additional language recognizers only when there is data to evaluate them.

### P1 — Upstream hostname allowlisting is not complete SSRF protection

The backend code itself comments that hostname allowlisting is not complete SSRF protection. DNS resolution and network egress are separate concerns.

**Action:** keep KAVACH bound to loopback for the current local development scope. For any deployment beyond localhost, enforce outbound network egress controls at the OS/container/network layer and review DNS resolution behaviour. Do not expose the local development server publicly.

### P1 — PDF parser resource consumption needs a separate check

The visible route limits upload size and page count, which is useful, but the source snapshot does not show a CPU/time or memory isolation boundary around `PdfReader` and page text extraction.

**Action:** test with malformed and highly compressed synthetic PDFs, measure worst-case parse time/memory, and consider parsing in a resource-limited worker if the app is ever exposed beyond local use. Keep OCR out of scope unless explicitly added.

### P1 — Agent and audit implementation was not independently inspected in this pass

Previous project records report tests that the sensitive value is not sent to the local model and that audit rows contain workflow metadata only. Those are useful regression signals, but the current `agent.py`, `agent_runtime.py`, `agentic.py` and `audit.py` source was not available for this review.

**Action:** inspect the exact current source and retain tests that assert the raw prompt and each synthetic sensitive sentinel are absent from the Ollama request and SQLite record. Also inspect failure paths, logs, exception messages and model-unavailable behaviour. Treat best-effort sanitization as a risk control, not a guarantee.

### P2 — Local API token handling is appropriate for a local prototype, not multi-user deployment

The inspected backend generates a process token when `KAVACH_API_TOKEN` is absent and logs that token at startup so the dashboard can use it. The dashboard stores its token in `sessionStorage`. This is workable for a local development UX, but anyone with access to the terminal log can obtain the token, and same-origin JavaScript can read session storage.

**Action:** do not share startup logs or screenshots containing the token. Keep the service loopback-only. Add a strict Content Security Policy and standard response headers after checking the current static assets for inline scripts/styles; avoid presenting this token scheme as multi-user authentication.

## Regression evidence and remaining tests

**Completed on the current Windows checkout:**

- The chat proxy uses `analyze_global()` and masks a real `CONFIDENTIAL_BUSINESS` contextual-rule finding before a mocked upstream receives the message.
- Proxy email masking and mocked global-detector masking tests passed.
- Existing security tests passed for API-token enforcement, health access, same-origin requests, cross-origin rejection and untrusted-host rejection.
- The full preflight passed with 67 Python tests, eight validator self-tests, extension policy/privacy checks and 1,557/1,557 Python/JavaScript parity.

**Still recommended before any real-provider or non-local deployment:**

- Capture a synthetic secret canary in the mock-upstream request and assert that the raw canary is absent and the masked placeholder is present.
- Test high-risk blocking and failure behaviour, including Presidio unavailable, upstream errors and malformed provider responses.
- Verify redirect handling, DNS/network egress restrictions, oversized chat requests and upload limits.
- Exercise extension Enter-key and send-button flows on each supported site for Mask, Warn, Block, Allow and user override behaviour.
- Inspect and test agent/audit failure paths and PDF parser resource consumption.

These recommendations are not claims that the corresponding tests have passed. Keep the proxy local/mock-only until the remaining checks and deployment review are complete.

## Overall judgement

The inspected backend has several useful local-development protections and explicit resource limits. The earlier source-snapshot chat-proxy detector mismatch has since been resolved in the current checkout and covered by mocked-upstream regression tests. The whole-extension runtime network behaviour, agent/audit data handling, PDF resource limits, upstream deployment controls and real-provider proxy behaviour still require further validation. The product should remain described as a **local-first prototype**. This review is not a production-security certification.

## Follow-up inspection — 31 October 2026

The extension options page previously stated that nothing typed is ever sent anywhere by KAVACH. That wording was too absolute. The inspected extension JavaScript uses `chrome.storage.sync` for per-type policy settings and contains no direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or WebSocket calls. The manifest requests the `storage` permission and declares no host permissions. The options-page wording and manifest description have been revised to distinguish local browser prompt scanning, Chrome Sync policy storage, and submission to the destination AI provider. This source inspection is not a runtime network trace and does not characterize the separate FastAPI chat-completions proxy.

### Global detector benchmark evidence ? 31 October 2026

The current generated synthetic test split contains 165 prompts and 45 negatives. After adding PERSON-context and business-identifier phone filters, the recorded global detector false-alarm rate was 0% (0/45), with MICRO_ALL F1 0.96 and MICRO_SHARED F1 1.00. Latency was p50 7.490 ms and p95 12.693 ms.

This is limited synthetic benchmark evidence, not a penetration test, independent evaluation or production-wide accuracy claim. PERSON and LOCATION positive detection remain unvalidated because the gold dataset contains no corresponding positive examples. Presidio is configured for English; language-grouped results do not establish multilingual support.

## Current implementation addendum — 4 November 2026

The following controls were checked against the current source after the
historical review. They are implemented features, not proof of complete
security or detection accuracy:

- The supported Windows launcher binds Uvicorn to `127.0.0.1`; startup checks
  `/api/health`, and the stop script validates process identity before stop.
  The health route is public; other API routes require the KAVACH token.
- The supported release mode is local Windows operation through the
  PowerShell launchers. Docker remains experimental and unsupported; token
  provisioning, persistent SQLite storage, and multi-process rate limiting
  are unvalidated. Do not expose its configuration to a network or treat it
  as production-ready.
- Ollama URLs accept only `localhost` or loopback IP literals. Requests
  disable environment proxy inheritance and redirects. The agent receives
  bounded workflow metadata or finding type/confidence data and a redacted
  context marker, never the original or masked prompt or detected source
  values. The configured chat proxy is separate and forwards masked messages
  to its selected upstream.
- File scans accept TXT/PDF only, cap the file at 5 MiB and the complete
  multipart request at 5 MiB plus 64 KiB, and cap PDFs at 20 pages. pypdf
  parsing has resource limits; malformed/parser-limit PDFs receive a generic
  read error while password, file-size, page-count and no-readable-text cases
  have fixed explanatory responses. OCR is not implemented.
- Responses receive CSP, `nosniff`, and `no-referrer`; API and proxy responses
  are `no-store`. The in-memory rolling limits are 30/minute for `/api/scan`,
  10/minute for `/api/scan-file`, and 20/minute for `/v1/chat/completions`,
  with HTTP 429 and `Retry-After: 60`. They are process-local and do not cover
  `/api/scan-global` or `/api/agentic/scan`.
- SQLite audit writes contain workflow metadata only. Expired rows are
  transactionally cleaned after audit writes, at most hourly; retention is
  30 days by default and `KAVACH_AUDIT_RETENTION_DAYS=0` disables cleanup.
  SQLite is not encrypted by default.
- Extension detection remains distinct from backend global detection: the
  extension does not run Presidio. Its 1,557 parity fixture checks native
  Python/JavaScript behavior only; selected deterministic global rules have
  separate regression cases.

The current setup is local-first. Distributed rate limiting, cloud hosting,
24/7 monitoring, encrypted SQLite, OCR, production certification and
guaranteed accuracy are not implemented. Interactive FastAPI `/docs` may be
blocked by the strict CSP; `/openapi.json` remains available. Future exposure
beyond loopback needs a separate deployment and security review.
