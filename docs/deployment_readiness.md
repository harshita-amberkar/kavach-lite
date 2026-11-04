# Deployment readiness

**Status (4 November 2026): not production-ready; no hosted deployment exists.** The supported operation for this release is single-user local development on Windows through the PowerShell launchers. This document records prerequisites for a future deployment; it is not a deployment guide for an available hosted service.

## Current controls and limits

| Area | Status | Current state |
|---|---|---|
| Production configuration | NEEDS WORK | Launcher uses loopback and local `.env`; there is no validated production profile, secret manager integration, or deployment configuration. |
| Secret handling | NEEDS WORK | API token is configured through an environment variable; hosting must provision a strong secret outside the image and logs. The fallback random process token is unsuitable for a multi-worker deployment because workers may differ. |
| Authentication/session | NEEDS WORK | Shared `X-KAVACH-Token` gate protects API routes; public `/api/health` is exempt. This is not user identity, authorization, or a managed session system. Browser token storage is client-side. |
| HTTPS/cookies | NEEDS WORK | Local launcher is HTTP loopback and the app does not implement secure cookie sessions. A hosted service needs TLS termination, HTTPS-only access, secure cookie/session design if applicable, trusted-proxy configuration, and HSTS policy review. |
| Database/persistence | NEEDS WORK | SQLite audit schema is initialized by application code; there is no versioned migration framework, automated backup/restore procedure, encryption-at-rest, or tested persistent-volume setup. SQLite is not encrypted by default. |
| Rate limiting/scaling | NEEDS WORK | Selected endpoint limits are process-memory counters; `/api/scan-global` and `/api/agentic/scan` are not covered. Counters reset on restart and do not coordinate workers. Add shared limits and edge controls before scaling. |
| Logging/privacy | NEEDS WORK | Application logging is basic; local launcher writes runtime logs under ignored `data/`. A hosted logging plan needs access controls, retention, redaction, alerting, and checks against raw prompts, uploaded text, tokens, and upstream bodies. |
| Health/monitoring | NEEDS WORK | `/api/health` gives local readiness information and is public; dashboard refreshes locally. No remote uptime monitoring, alerting, or operational on-call integration is provided. |
| Ollama | NOT APPLICABLE to hosted mode as configured | Optional agent endpoint is deliberately restricted to loopback. Hosted agent use requires an explicit supported model-serving/network design, authentication, egress restrictions, privacy review, and operational testing; remote Ollama URLs are currently rejected. |
| Docker | NEEDS WORK | Dockerfile and `.dockerignore` are experimental and unsupported. Container binds `0.0.0.0`, has no validated secret provisioning, persistent database volume, distributed rate limiting, TLS, or monitoring. Do not expose it publicly. |
| Browser extension | NEEDS WORK | The Chrome package and automated checks passed. Installation was blocked because Developer mode was administrator-managed; installed-extension Mask/Warn/Block behavior remains unverified. |
| OCR/continuous monitoring | NOT APPLICABLE | OCR, a hosted service, and continuous monitoring are not implemented features. |

## Prerequisites before hosting

1. Define the hosting threat model, supported users, data residency, privacy obligations, and whether `/v1/chat/completions` may forward masked content to third-party providers.
2. Add a production configuration with managed secrets, stable authentication/authorization, HTTPS termination and trusted proxy handling, strict host/origin policy, and explicit public health-check behavior.
3. Choose persistent storage and migration strategy. Add schema migrations plus documented, tested backup, restore, retention, encryption-at-rest, and access-control procedures.
4. Replace in-process rate limits with shared enforcement; cover every expensive route and add ingress/body/time limits and outbound network egress controls.
5. Establish structured, access-controlled, retention-limited logs and monitoring. Verify logs and error reporting never contain raw prompts, extracted document text, credentials, or upstream payloads.
6. Validate deployment artifacts and operations in an isolated staging environment: startup, graceful shutdown, health probes, worker counts, persistence, restore, incident response, dependency updates, and rollback.
7. Independently review and test real-provider proxy behavior and obtain a permitted Chrome environment to manually verify installed extension behavior.

No hosting, domain, or production credential is currently configured. The project should continue to be described as a local-first development application until those controls are implemented and reviewed.
