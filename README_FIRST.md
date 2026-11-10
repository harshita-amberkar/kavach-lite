# KAVACH Lite - Project Validation Guide

> Status: Independent, solo-developed software project. Benchmark results include a project-authored synthetic holdout, not a human-created or statistically representative evaluation.

## Current security behavior

The supported release runs locally on Windows through the PowerShell launchers. The included Docker files are experimental and unsupported; token provisioning, persistent SQLite storage, and multi-process rate limiting have not been validated. Do not expose the Docker setup to a network or treat it as production-ready. The Windows launcher binds the API to `127.0.0.1`, disables forwarded-header processing, and the server independently limits owner APIs to direct loopback clients in the default `local` access mode. The full owner dashboard is served at `/`; local dashboard use needs no owner token prompt. A future remote deployment must explicitly enable token mode and configure a strong token, and still requires separate deployment security review. This is local operation, not cloud hosting or 24/7 monitoring. Use `tools\stop_kavach.ps1` for identity-checked shutdown. The optional Ollama client is restricted to loopback, disables environment-proxy use and redirects, and sends workflow/finding metadata rather than original or masked prompts or detected source values. The separate chat proxy can forward masked messages to its configured upstream.

## Windows quick start

1. Install Python and, if you plan to run the extension checks, Node.js. Ollama is optional.
2. In PowerShell at the project root, create the virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Follow the [full Windows setup](README.md#run-locally-windows-powershell) to create a private `.env`. The default single-user local mode does not require an API token.
4. Start KAVACH with `.\tools\start_kavach.ps1`, check `http://127.0.0.1:8000/healthz`, and stop it with `.\tools\stop_kavach.ps1`.

The PowerShell launchers are the supported release path. Docker remains experimental and unsupported; see the README for its limitations.

File scanning accepts TXT/PDF only, with a 5 MiB file cap, 5 MiB + 64 KiB multipart request cap, 20-page PDF cap and bounded pypdf parsing. API responses include CSP/security headers; selected routes have per-client, in-memory rate limits. Audit storage is metadata-only with 30-day retention by default (`KAVACH_AUDIT_RETENTION_DAYS=0` disables cleanup); SQLite is not encrypted by default. See [README.md](README.md) and [security validation](docs/security_validation.md) for details and limitations.

The Chrome extension does not run backend Presidio detection. Its 1,557-case parity result covers native Python/JavaScript detection only; selected deterministic global rules have separate regression tests. Detection accuracy is not guaranteed.

User-reported manual functional tests passed for EMAIL Mask, Warn and Block on ChatGPT, Claude and Gemini; EMAIL Block persisted after reloading the extension; and a synthetic PAN was masked on ChatGPT. These results cover the listed cases and are not an independent security audit or a guarantee for every identifier or site state. Automated package, policy/privacy, detector-parity, syntax and manifest checks passed. Developer Mode was administrator-restricted on the review machine, so installation was not verified on that machine; this does not negate the recorded manual functional tests.

## Project components

- `app.py` — FastAPI application and API endpoints.
- `kavach/` — Core detection and masking engine.
- `extension/` — Chrome extension for local prompt protection.
- `static/` — Dashboard interface.
- `eval/` — Synthetic benchmark generation and evaluation.
- `tests/` — Python regression and security tests.
- `docs/` — Technical documentation and implementation records.

## Validation tools

- `tools/run_preflight.ps1` — Windows preflight for Python, JavaScript, extension and syntax checks.
- `eval/gen.py` — Generates the synthetic benchmark dataset.
- `eval/run.py` — Evaluates datasets and writes benchmark reports.

## Implementation notes

- `/v1/chat/completions` uses `analyze_global()` before forwarding masked message content.
- `/api/scan` uses the native `analyze()` detection engine.
- Presidio global detection currently uses English (`language="en"`). Language-grouped evaluation tables do not establish multilingual detection.
- The Chrome extension performs prompt detection locally and stores policy settings using `chrome.storage.sync`.
- When a user submits a prompt, the destination AI service receives the submitted content. KAVACH must not claim otherwise.
- `eval/gen.py` generates synthetic benchmark examples for AADHAAR, PAN, PHONE, CARD, UPI_ID, GSTIN and EMAIL.
- `eval/run.py` records error metadata, entity types and character offsets, not raw prompt text or entity values.

## Recorded global detection benchmark — 31 October 2026

Dataset: 165 synthetic prompts, including 45 negative prompts.

- Global false-alarm rate: 0% (0/45).
- Global MICRO_ALL: precision 0.92, recall 1.00, F1 0.96.
- Global MICRO_SHARED: precision 1.00, recall 1.00, F1 1.00.
- Global latency: p50 7.490 ms; p95 12.693 ms.
- Native KAVACH false-alarm rate: 0%; MICRO_ALL F1: 1.00.

### Benchmark limitations

- PERSON and LOCATION have no corresponding gold-positive examples in this dataset.
- Results are self-authored synthetic evaluations, not independent or production accuracy claims.
- Presidio is invoked with English language configuration; multilingual detection has not been established.
- Global detection has additional latency compared with the native detector.

## Recommended validation procedure

1. Run `python -m unittest discover -v`.
2. Run `tools\run_preflight.ps1` from the project root.
3. Check extension detector parity and policy tests.
4. Review `git diff --check` and `git status --short`.
5. Use synthetic or consented and anonymised data only.
6. Record benchmark limitations alongside reported results.

## Data handling

- Do not commit `.env`, API credentials, databases or runtime logs.
- Do not put real personal information into synthetic benchmark datasets.
- Keep audit records and local evaluation outputs protected.
- Do not describe self-authored benchmarks as independent blind evaluations.
