# KAVACH Security Validation

## Purpose

This document records automated and live checks performed during
development. These results describe the tested implementation and
synthetic fixtures; they are not a certification or proof of security
against every possible attack.

> **Historical run record:** the 42-test count below describes an earlier
> development run, not the current checkout. Current release checks are run
> with `tools/run_preflight.ps1`; use its latest output for current results.
> The current controls and remaining limits are summarized at the end of
> this document.

## Automated verification

The recorded verification run reported:

- 42 Python unit tests passed.
- Chrome extension policy and privacy checks passed.
- Python and JavaScript detector parity: 1557/1557 cases identical.
- `git diff --check` reported no whitespace errors.

Relevant coverage includes:

- Agent disabled mode and malformed model responses.
- Redaction of synthetic sensitive values before local-model review.
- Masking before upstream chat-proxy forwarding.
- Exclusion of the KAVACH API token from startup logs.
- Audit-storage privacy using synthetic sentinel values.
- Extension policy/privacy behavior.

## Live synthetic workflow checks

A live authenticated scan returned masked output for a synthetic email:

`Contact [EMAIL] for support.`

The non-agent workflow completed with masking verification passed and
an audit record saved.

A subsequent workflow with the optional local agent enabled reported:

- Agent enabled: true.
- Agent review status: `ok`.
- One agent review returned.
- Workflow status: `completed`.
- Masking verification: `passed`.
- Audit status: `saved`.
- Human review required: false.

The corresponding SQLite record reported:

- Workflow: `global_privacy_workflow`.
- Status: `completed`.
- Agent status: `ok`.
- Agent review count: 1.
- Verification status: `passed`.
- Human review required: false.

These live tests used synthetic input.

## Privacy controls observed in the implementation

- The audit table stores workflow metadata, finding types and counts,
  risk information, agent status, verification status, and filtered
  workflow steps rather than original prompt text.
- Agent review context is sanitized before it is sent to the configured
  Ollama endpoint. The current request builders send finding types,
  confidence and bounded workflow metadata, with a literal `[REDACTED]`
  marker; original and masked prompt text and detected values are withheld.
- The chat proxy constructs an upstream payload using masked messages.
- The KAVACH API token is no longer written to application startup logs.
- The optional agent is advisory; deterministic scanning and masking
  remain separate from its review output.

## Limitations

- The evaluation datasets are small, handcrafted synthetic datasets.
  Their scores do not establish production-wide accuracy.
- The local AI review was tested on a synthetic example; its semantic
  judgment has not been independently validated here.
- Automated tests and smoke tests cover selected paths, not every
  deployment configuration or attack.
- The detector can miss unsupported or previously unseen formats; the agent
  does not receive source text to apply any additional source-value redaction.
- A successful verification rescan only establishes that the configured
  scanner found no remaining supported findings in that output.
- The configured local model endpoint and local host security remain
  deployment considerations.

## Demonstration guidance

Use synthetic or consented and anonymized data. Keep API tokens out of
screenshots, source files, commits, and shared logs. Bind the development
server to loopback unless a separately reviewed deployment design is
used. Describe all benchmark results with their dataset sizes and
limitations.

## Current implementation status — 4 November 2026

The earlier verification notes above are historical evidence. The current
implementation also has loopback-only Ollama URL validation with HTTP
environment-proxy inheritance and redirects disabled; a 5 MiB file limit,
a 5 MiB plus 64 KiB total multipart limit, a 20-page PDF cap and pypdf
resource limits; generic upload/parser errors; response CSP and standard
security headers; selected per-client API rate limits; and asynchronous,
transactional audit retention (30 days by default, `0` disables it).
SQLite remains unencrypted by default. The dashboard and owner APIs are
available only to loopback clients in default local mode; `/healthz` exposes
minimal liveness. Selected rate limits remain in-process, reset on restart,
and do not coordinate workers. The app does not use forwarding headers; an
upstream proxy can still change the address exposed by the ASGI server.
Limits do not apply to `/api/scan-global` or `/api/agentic/scan`.
Owner APIs are loopback-only by default and use the direct ASGI peer address;
`X-Forwarded-For`, `X-Real-IP`, and `Forwarded` do not establish local access.
The Windows launcher binds to `127.0.0.1` and disables proxy-header handling.
The local mode is for the current single-user laptop setup and must not sit
behind a reverse proxy. Future remote deployments must explicitly select
`KAVACH_OWNER_ACCESS_MODE=token` and configure a private token of at least 40
characters; token mode retains token authentication on owner APIs.
The extension
does not run the backend's Presidio recognizers; its parity number covers
only native detector fixtures, with separate regression coverage for
selected deterministic global rules.

The supported release setup is local Windows operation through the
PowerShell launchers, which bind to loopback. Docker is experimental and
unsupported; its token provisioning, persistent SQLite storage, and
multi-process rate limiting have not been validated. Do not expose the
Docker configuration to a network or use it as a production deployment.
The optional chat proxy can
send masked content to its configured upstream. Cloud hosting, distributed
rate limiting, continuous monitoring, OCR, production certification, and
guaranteed detection accuracy are not implemented. The full project
preflight passed on 4 November 2026, including Python tests and compilation,
extension policy/privacy checks, 1,557/1,557 native detector parity,
JavaScript syntax, manifest validation, and `git diff --check`. These
results describe this local checkout; passing preflight is not a security
certification.
