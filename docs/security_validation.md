# KAVACH Security Validation

## Purpose

This document records automated and live checks performed during
development. These results describe the tested implementation and
synthetic fixtures; they are not a certification or proof of security
against every possible attack.

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
  Ollama endpoint. Pattern-based sanitization is not a guarantee that
  every possible sensitive value will be detected.
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
- Pattern-based redaction may miss previously unseen sensitive formats.
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
