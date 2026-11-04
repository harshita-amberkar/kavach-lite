# KAVACH Lite: India-Aware PII Guardrail for AI Tools

KAVACH Lite is a privacy-focused project that detects and masks potentially sensitive information before it is shared with AI tools. It combines an India-aware rule-based detector, a FastAPI backend, a Chrome extension for prompt-time warnings and masking, an evaluation framework, and an optional local-LLM advisory reviewer.

KAVACH is a development project, not a guarantee that every sensitive value or data-leakage path will be detected.

The supported Windows launcher binds the backend to `127.0.0.1`; this is a local, single-user development setup, not a hosted service or 24/7 monitoring product. Ollama is restricted to loopback. If `/v1/chat/completions` is configured for a remote provider, KAVACH forwards the **masked** message to that configured upstream, so use of that route is not fully local.

**Supported release operation:** run KAVACH locally on Windows using the
PowerShell launchers documented below. The included Dockerfile and
`.dockerignore` are experimental and unsupported; Docker is not a supported
deployment for this release. Its configuration has not been validated for
API-token provisioning, persistent SQLite storage, or multi-process rate
limiting. Do not expose the Docker container to a network or treat it as
production-ready.

## Features

- **Sensitive-data detection:** configured recognizers for Aadhaar, PAN, phone numbers
, payment-card numbers, email addresses, UPI IDs, GSTIN, IFSC, and supported secrets.
- **Checksum/context checks:** Aadhaar Verhoeff, GSTIN check-character, and card Luhn validation help reduce certain false positives.
- **Masking and risk scoring:** scan responses include finding types, character offsets, confidence scores, masked text, and a risk assessment.
- **Chrome extension:** prompt scanning and configurable allow, warn, mask, and block actions for ChatGPT, Claude, and Gemini. Website UI changes can affect compatibility.
- **FastAPI backend:** text scanning, file scanning, global detection, autonomous workflow execution, and a configured OpenAI-compatible chat-completions proxy route.
- **User-focused dashboard:** Protect and Settings sections, persistent browser-local defaults, a shared protected preview, and a simple protection summary.
- **Evaluation lab:** hand-written gold-set evaluation, synthetic benchmarks, comparison systems, and Python/JavaScript detector-parity tests.
- **Bounded autonomous local agent:** When enabled, Ollama (`llama3.2:3b` by default) selects from an allowlist of workflow tools. Python executes those tools; deterministic detection, masking, and verification remain authoritative. The agent is disabled by default, uses safe workflow metadata for planning, and cannot run arbitrary shell commands or access arbitrary files.

Prompt scanning in the Chrome extension is performed in the browser. Its per-type policy settings use `chrome.storage.sync`; the extension source inspected for this review contains no direct `fetch`, `XMLHttpRequest`, `sendBeacon`, or WebSocket calls. This describes the extension path only. It does not describe the separate FastAPI chat-completions proxy or the destination AI service.

**Novelty note:** Microsoft Presidio already has `IN_AADHAAR` and `IN_PAN` recognizers, and commercial data-protection products exist. KAVACH does not claim that Indian-ID detection alone is novel. Its project focus is the evaluated combination of India-aware detection, prompt-time browser protection, policy actions, and a local advisory workflow.

## Dashboard

The dashboard is designed around two user-facing sections:

- **Protect:** paste a prompt, choose a protection mode, choose a masking
  format, run the check, inspect detected items, review the protected
  preview, and copy the protected text.
- **Settings:** save the default protection mode and masking format,
  find the Chrome extension policy instructions, and review local server
  and AI configuration information.

### Protection modes

| Mode | Behavior |
|---|---|
| Standard | Calls the global scan endpoint and displays the protected result. |
| Autonomous | Runs the bounded multi-step workflow, including verification and audit recording. |

### Masking formats

| Format | Behavior |
|---|---|
| Label | Replaces detected values with labels such as `[EMAIL]` or `[PHONE]`. |
| Partial | Preserves the last four digits for supported Aadhaar, card, and phone findings. Other findings continue to use labels. |

Protection mode and masking format are separate choices.

Dashboard defaults are stored in browser local storage. They apply to the
dashboard in that browser and are not server-wide settings.

Chrome extension policies are separate. They are configured from the
extension Options page and stored using Chrome extension storage.

The dashboard intentionally does not show a separate Recent Activity
page. Autonomous workflow metadata is still recorded by the backend and
can be retrieved through the audit history API.

The Protect workspace also supports TXT and text-based PDF scanning,
subject to the application's file-size limit.

## Architecture

```text
                         +----------------------+
                         |      KAVACH User     |
                         +----------+-----------+
                                    |
                  +-----------------+-----------------+
                  |                                   |
          +-------v--------+                  +-------v---------+
          | Chrome         |                  | Dashboard       |
          | Extension      |                  | Protect /       |
          | JavaScript     |                  | Settings        |
          | detector       |                  +-------+---------+
          +-------+--------+                          |
                  |                     +-------------+-------------+
                  |                     |                           |
          +-------v--------+    +-------v---------+        +--------v--------+
          | Extension      |    | Standard        |        | Autonomous      |
          | Allow / Warn / |    | /api/scan-global|        | /api/agentic/   |
          | Mask / Block   |    +-------+---------+        | scan            |
          +----------------+            |                  +--------+--------+
                                        |                           |
                              +---------v---------------------------v--+
                              | KAVACH Global Detection                |
                              | KAVACH rules + Presidio + context rules|
                              +-------------------+--------------------+
                                                  |
                                         +--------v--------+
                                         | Masking and     |
                                         | risk assessment |
                                         +--------+--------+
                                                  |
                                      Autonomous verification
                                      and metadata-only audit
                                                  |
                                         +--------v--------+
                                         | Protected output|
                                         +-----------------+

Gold / synthetic datasets --> Evaluation reports
```

The extension and backend are separate execution paths. They share detector behavior through a JavaScript/Python parity suite, but each path still needs independent integration testing. The autonomous agent uses a bounded tool loop; deterministic scanning, masking, and verification remain authoritative.

## Requirements

- Windows with PowerShell for the supported launcher scripts
- Python and packages in `requirements.txt`
- Node.js for extension tests
- Google Chrome to manually test the extension
- **Optional for the local agent:** Ollama and `llama3.2:3b`.

## Run locally: Windows PowerShell

Run commands from the project root (the directory containing `app.py`, `kavach/`, `eval/`, and `extension/`). The supported Windows launcher requires the project virtual environment and a root `.env` file. Create the environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create `.env` without printing the generated token. This command refuses to overwrite an existing `.env`; it writes the random token directly to the ignored local file and clears the in-memory token variable afterward:

```powershell
if (Test-Path .env) { throw ".env already exists; leaving it unchanged." }
$bytes = New-Object byte[] 48
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $rng.GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes)
    $config = @(
        "KAVACH_API_TOKEN=$token",
        "KAVACH_DB_PATH=data/kavach.db",
        "KAVACH_ALLOWED_HOSTS=127.0.0.1,localhost"
    )
    [IO.File]::WriteAllLines((Join-Path (Get-Location) ".env"), $config, [Text.Encoding]::ASCII)
}
finally {
    $rng.Dispose()
    [Array]::Clear($bytes, 0, $bytes.Length)
    Remove-Variable token -ErrorAction SilentlyContinue
}
```

`.env.example` contains the required keys with a safe token placeholder. It is a template, not a usable token; replace the placeholder with a locally generated token if you create `.env` by copying the template. Keep `.env` local and never paste the token into a command, screenshot, log, or repository. The launcher reads blank lines and `#` comments and otherwise expects unquoted `UPPERCASE_KEY=value` lines.

The launcher validates that `.venv\Scripts\python.exe` exists, `KAVACH_API_TOKEN` is nonblank and at least 40 characters, `KAVACH_DB_PATH` is nonblank, and `KAVACH_ALLOWED_HOSTS` includes both `127.0.0.1` and `localhost` as comma-separated entries with no spaces around the host names. It initializes the configured SQLite database, refuses to start if the selected port already has a listener, then starts Uvicorn on `127.0.0.1`. The default port is 8000; the optional `-Port` value must be from 1024 through 65535.

Start and stop KAVACH from the project root with the supported PowerShell scripts:

```powershell
.\tools\start_kavach.ps1
# Optional alternate port:
.\tools\start_kavach.ps1 -Port 8001
.\tools\stop_kavach.ps1
```

The start script waits for `/api/health`, copies the configured token to the clipboard without printing its value, and opens the dashboard in Chrome or the default browser. The stop script validates the recorded PID, executable path, and Uvicorn command before stopping that process. The `Start KAVACH.bat` and `Stop KAVACH.bat` wrappers invoke these scripts from the project root.

Useful URLs:

- API health: `http://127.0.0.1:8000/api/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Registered API schema: `http://127.0.0.1:8000/openapi.json`

The health endpoint in this version is `/api/health` (not `/health`). It reports local backend readiness, whether the configured SQLite file can be read, and optional Ollama service/model availability. Ollama is probed only when the agent is enabled; an unavailable database or Ollama does not make the scan API readiness endpoint fail. The dashboard refreshes this summary every 30 seconds. This is local process health visibility, not remote or continuous monitoring.

The dashboard and protected API routes use the `X-KAVACH-Token` header. Paste the launcher's copied token into the dashboard prompt. Do not commit, share, or include the token in screenshots or logs.

`GET /api/health` is intentionally public for local readiness checks; other `/api/*` routes and `/v1/chat/completions` require the token. Health checks do not create or modify the database. The supplied start script checks `/api/health` before opening the dashboard. Stop with `tools\stop_kavach.ps1`; it validates that the PID belongs to the expected project Python/Uvicorn process before stopping it.

### Browser response protection and request limits

Responses include a restrictive Content Security Policy, `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`. The policy allows same-origin scripts/styles and blocks objects and framing (`frame-ancestors 'none'`); dashboard scripts and styles load from the same origin. API and chat-proxy responses use `Cache-Control: no-store`. The built-in interactive FastAPI `/docs` page may not render because its framework UI uses inline/CDN scripts blocked by this policy; `/openapi.json` remains available. No unsafe-inline or unsafe-eval is enabled.

Per-client rolling 60-second limits currently apply to `/api/scan` (30), `/api/scan-file` (10), and `/v1/chat/completions` (20). Set `KAVACH_RATE_LIMIT_SCAN_PER_MINUTE`, `KAVACH_RATE_LIMIT_SCAN_FILE_PER_MINUTE`, and `KAVACH_RATE_LIMIT_CHAT_PER_MINUTE` in `.env` to change those counts; accepted values are 1 through 1000. Invalid values use the defaults. A limited request receives HTTP 429 and `Retry-After: 60`. These limits do not currently cover `/api/scan-global` or `/api/agentic/scan`.

Rate-limit counters are held in process memory and keyed by the connecting client IP. This fits the supported single-process, loopback Windows setup. Counters reset when KAVACH restarts and do not coordinate across multiple server processes or cloud instances; deployments with multiple instances need a shared rate-limit store and edge-level request controls.

### File scan limits

`POST /api/scan-file` accepts only TXT and PDF uploads. The complete multipart request is limited to 5 MiB plus 64 KiB for form framing; the uploaded file itself remains limited to 5 MiB. PDFs are limited to 20 pages and parsed with bounded pypdf stream, decompression, page-tree, and content-processing limits. Password-protected PDFs, oversized files, and over-page-limit PDFs receive fixed explanatory errors; malformed or parser/resource-limit PDFs receive a generic read error, and PDFs with no extractable text receive a no-readable-text response. Scanned-image PDFs are not OCR processed. Temporary upload handles are closed after the request. The application does not log or persist the uploaded file or extracted text.


### Optional autonomous local-agent setup

Install Ollama using its official installation instructions, then obtain the model:

```powershell
ollama pull llama3.2:3b
ollama list
```

To enable the optional agent with the supported launcher, add these unquoted lines to the local `.env` file:

```text
KAVACH_AGENT_ENABLED=1
KAVACH_AGENT_TIMEOUT=30
```

Then restart KAVACH with `tools\start_kavach.ps1` (stop an already running instance first). The agent is disabled unless `KAVACH_AGENT_ENABLED=1`.

Configuration:

- `KAVACH_AGENT_ENABLED`: set to `1` to enable; default is disabled (`0`).
- `KAVACH_AGENT_TIMEOUT`: request timeout in seconds; default is `30`. A longer timeout may be needed for model startup or slow inference.
- `KAVACH_OLLAMA_URL`: defaults to `http://127.0.0.1:11434/api/generate`.
- `KAVACH_OLLAMA_MODEL`: defaults to `llama3.2:3b`.

These environment variables apply to the process launched from that terminal. Restart the API after changing them. `KAVACH_OLLAMA_URL` accepts only HTTP(S) URLs whose host is `localhost`, `127.0.0.1`, or IPv6 loopback (`[::1]`); remote DNS names, LAN/public IPs, credentials in the URL, and other destinations are rejected. Ollama HTTP requests ignore environment proxy settings and do not follow redirects.

During autonomous planning, Ollama receives eligible tool names and a bounded workflow summary containing counts, finding types, risk/status metadata, and reason codes, not the original or masked prompt. The advisory review sends finding types and confidence values with a literal `[REDACTED]` context marker; it does not send source context or detected values. These are implemented request-construction controls, not a claim that KAVACH detects every sensitive value. Model outputs cannot override deterministic detection, masking, verification, or policy decisions.

### Linux or macOS

The PowerShell launcher is Windows-only. For manual startup, create the same local `.env` settings without printing the token, then export them into the server process:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python - <<'PY'
from pathlib import Path
import secrets

path = Path(".env")
if path.exists():
    raise SystemExit(".env already exists; leaving it unchanged.")
path.write_text(
    "KAVACH_API_TOKEN=" + secrets.token_urlsafe(48) + "\n"
    "KAVACH_DB_PATH=data/kavach.db\n"
    "KAVACH_ALLOWED_HOSTS=127.0.0.1,localhost\n",
    encoding="ascii",
)
PY
set -a
. ./.env
set +a
python -m uvicorn app:app --host 127.0.0.1 --reload
```

The shell commands explicitly load `.env`; Uvicorn does not load it automatically. Use the configured token in the dashboard's `X-KAVACH-Token` prompt.

### Load the Chrome extension

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Select **Load unpacked** and choose the project's `extension/` directory.
4. Test using synthetic text only, and review the extension's configured policies before demonstration.

The extension targets ChatGPT, Claude, and Gemini. In the final release review, installation was blocked because Developer mode was administrator-managed. Extension package checks and automated policy/privacy and detector-parity checks passed, but installed-extension Mask/Warn/Block behavior remains unverified in Chrome. Website interface changes can also require compatibility fixes.

### Future deployment readiness

KAVACH is not currently hosted and this release does not provide a production deployment. The Windows launchers support only a single-user loopback development setup. See [Deployment readiness](docs/deployment_readiness.md) for prerequisites and open work before a separately reviewed hosted deployment.

## API

### `GET /api/health`

Returns health status and application version. The version observed during development was `1.2.4`.

### `POST /api/scan`

Example request:

```json
{
  "text": "Contact demo@example.com for support.",
  "mode": "label"
}
```

The response includes `findings`, `masked_text`, and `risk`. If the optional agent is enabled, it also includes `agent_review`. Example masked text:

```text
Contact [EMAIL] for support.
```

The agent review is an advisory output. It does not modify the original findings, masked text, risk score, or policy actions.

### `POST /api/scan-global`

Runs the global detection pipeline, combining KAVACH rules, Presidio
recognizers, and contextual rules. The request accepts the same `text`
and `mode` fields as `/api/scan`, where `mode` is `label` or `partial`.

The Standard dashboard protection mode uses this endpoint. Its response
includes findings, masked text, risk information, and global-detection
metadata.

Example request:

```json
{
  "text": "Contact demo@example.com for support.",
  "mode": "partial"
}
```

### Autonomous agent endpoint

`POST /api/agentic/scan` runs the bounded agent workflow. The request accepts `text` and a masking `mode` of `label` or `partial`. The model may select only tools currently eligible for the workflow state; Python executes the approved actions. Scanning and masking are deterministic, and the masked output is verified before normal completion. Invalid actions or planner failures can trigger safe fallback and human review. The dashboard presents a simplified Protection Summary instead of exposing internal tool execution details.

`GET /api/agentic/history` returns autonomous workflow audit metadata. The dashboard does not currently expose this as a Recent Activity page. Raw prompts and sensitive values should not be stored in audit records.

### SQLite audit retention and privacy

The workflow audit database stores metadata only: workflow labels and status, finding types and counts, risk metadata, verification state, and bounded step metadata. It does not store source prompts, masked prompts, detected values, passwords, tokens, or free-form AI explanations. Audit rows older than 30 days are removed by default. Set `KAVACH_AUDIT_RETENTION_DAYS` in `.env` to change the period; `0` disables cleanup, and accepted nonzero values range from 1 through 36,500 days. Invalid settings fall back to 30 days.

Cleanup is scheduled asynchronously after an audit write, at most once per hour, so ordinary scans do not run retention queries. It deletes expired rows from `workflow_runs` in a SQLite write transaction and leaves the database and schema in place. If the database is locked or cleanup fails, KAVACH defers/skips that attempt and retries after the throttle interval on a later audit write. SQLite database files are **not encrypted by default**. Protect the configured database and its backups with Windows account and filesystem permissions, especially on shared or backed-up machines.

### Other routes

- `POST /api/scan-file`
- `POST /v1/chat/completions`

The chat-completions route is a configured upstream proxy. It runs the global detector (`analyze_global`) on message content and applies label masking before constructing the payload forwarded upstream. Its redaction count is based on the findings returned by that global pass. This is broader than the lightweight `analyze()` path used by `POST /api/scan`.

**Language limitation:** the Presidio component of the global detector is explicitly invoked with `language="en"`. KAVACH's native rules and selected contextual rules also run, but this does not establish multilingual Presidio coverage or validated detection quality for Hindi, Marathi, or Hinglish.

Before using the proxy with real data, separately review and test upstream forwarding, authentication, masking, blocking, error handling, rate limits, and deployment configuration. The current automated proxy tests use a mocked upstream; do not assume the route is production-ready based only on scan or mock-proxy tests.

## Tests

Run these from the project root.

### Python tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

### Dashboard JavaScript syntax

```powershell
node --check .\static\app.js
```

### Extension policy/privacy and detector parity

```powershell
node --check .\extension\content.js
node .\extension\tests\policy_and_privacy.js
node .\extension\tests\parity.js
```

### Python syntax check

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py kavach\agent.py kavach\detectors.py kavach\agent_runtime.py tests\test_agent_runtime.py
```

### Evaluation

```powershell
.\.venv\Scripts\python.exe -m eval.run --gold
.\.venv\Scripts\python.exe -m eval.benchmark
```

The evaluation runner writes `results/report.md`, `results/report.json`, and `results/errors.jsonl`. The gold dataset is at `eval/gold/gold.txt`. Run `python -m eval.run --help` for supported options.

## Current verification status

The full project preflight passed on 4 November 2026. It covers Python
tests/compilation, extension policy/privacy and detector parity, dashboard
and extension JavaScript syntax, manifest JSON, and `git diff --check`. Run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File
.\tools\run_preflight.ps1` from the project root for fresh results. Passing
these checks is not an accuracy guarantee, security certification, or
substitute for browser testing.

## Locked v1 evaluation

The separate frozen synthetic dataset
`eval/gold/gold_locked_v1.txt` contains 51 prompts:

- 12 tagged `real`
- 12 tagged `tricky`
- 27 tagged `neg`

The latest recorded run (29 October 2026) reported:

| System | Micro precision | Micro recall | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| KAVACH | 1.00 | 1.00 | 1.00 | 0/27 (0%) | 0.032 ms | 0.058 ms |
| KAVACH block | 1.00 | 1.00 | 1.00 | 0/27 (0%) | 0.029 ms | 0.040 ms |

The recorded reports are stored in `results/locked_v1_current/`
(`report.md`, `report.json`, and `errors.jsonl`).

This is a small synthetic evaluation set. Its results describe only
these test cases and do not establish production-wide accuracy or
generalization to unseen real-world data.

## Gold-set benchmark results

Latest rerun (29 October 2026): **51 hand-written prompts** in `eval/gold/gold.txt` (27 tagged `real`, 4 tagged `tricky`, and 20 tagged `neg`). The Hindi test entry was repaired to use readable Unicode and a checksum-valid synthetic Aadhaar test value. The detector code was not changed for that dataset repair.

| System | Micro precision | Micro recall | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| KAVACH | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.055 ms | 0.146 ms |
| KAVACH block | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.052 ms | 0.097 ms |
| Regex-only | 0.66 | 0.88 | 0.75 | 8/20 (40%) | 0.030 ms | 0.055 ms |
| Presidio | 0.76 | 0.70 | 0.73 | 7/20 (35%) | 9.323 ms | 27.640 ms |
| Presidio custom | 0.81 | 0.97 | 0.89 | 7/20 (35%) | 7.986 ms | 11.041 ms |
| Presidio normalized | 0.82 | 1.00 | 0.90 | 7/20 (35%) | 7.976 ms | 10.086 ms |

On this dataset, KAVACH reported per-type precision/recall/F1 of 1.00 for Aadhaar, card, email, GSTIN, PAN, phone, and UPI ID. This result applies only to the tested cases. The dataset is small and hand-written, so perfect scores do not establish real-world performance or generalization. The negative false-alarm result is based on only 20 negative prompts.

The latency figures above are detector/evaluation measurements; they do **not** include local-LLM inference or represent end-to-end API latency. The agent has not yet been evaluated against a sufficiently large labelled set for advisory-review accuracy, and its model latency varies with startup and host performance.

## Holdout regression evaluation

Latest rerun (29 October 2026): `eval/gold/gold_holdout.txt`,
containing 43 hand-written prompts (17 tagged `real`, 6 tagged
`tricky`, and 20 tagged `neg`).

| System | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|
| KAVACH | 1.00 | 0/20 (0%) | 0.039 ms | 0.067 ms |
| KAVACH block | 1.00 | 0/20 (0%) | 0.037 ms | 0.062 ms |
| Regex-only | 0.65 | 5/20 (25%) | 0.029 ms | 0.043 ms |
| Presidio | 0.77 | 1/20 (5%) | 7.368 ms | 12.066 ms |
| Presidio custom | 0.86 | 1/20 (5%) | 7.381 ms | 9.323 ms |
| Presidio normalized | 0.86 | 1/20 (5%) | 7.721 ms | 11.032 ms |

KAVACH reported precision, recall, and F1 of 1.00 for all listed
entity types in this run. The separate synthetic benchmark run also
reported zero false alarms on 210 clean sentences.

A normalized prompt audit found no duplicate prompts within either
the 51-prompt gold set or the 43-prompt regression set, and no exact
normalized prompt overlap between them. However, this regression set
was previously used to identify and guide detector fixes. It is
therefore **not an untouched blind test set** and must not be presented
as independent proof of generalization. Both datasets are small,
hand-written, synthetic evaluation resources; broader representative
testing remains necessary.

## Global detector benchmark (31 October 2026)

Generated synthetic test split: 165 prompts, 45 of them negative. Self-authored; not an independent evaluation.

| System | MICRO_ALL F1 | MICRO_SHARED F1 | Negative prompts flagged | p50 / p95 latency |
|---|---:|---:|---:|---:|
| KAVACH (native) | 1.00 | 1.00 | 0/45 | 0.067 / 0.092 ms |
| KAVACH Global | 0.96 | 1.00 | 0/45 | 7.490 / 12.693 ms |

The global detector first flagged 14/45 negatives (31.1%), caused by Presidio PERSON hits on ordinary words and a PHONE hit on an order ID. Context filters fixed these (five regression tests added). PERSON and LOCATION have no gold positives, so their quality is **not measured** and should be treated as experimental. PERSON is accepted only with explicit English name context.

## What the evidence does and does not show

- Presidio, given a one-line Devanagari-to-ASCII digit step ("Presidio normalized"), nearly matches KAVACH on these datasets (Micro F1 0.90 vs 1.00 on the 51-prompt set). KAVACH's advantage is that it normalises by default and avoids matching inside longer digit groups, not a fundamentally better detector.
- The existing gold and regression datasets are project-authored. A separate project-authored synthetic holdout is documented in `docs/independent_synthetic_holdout.md`; it is not human-created or statistically representative. Perfect scores on smaller datasets are regression results, not general accuracy evidence.
- Checksum-valid 12-digit numbers right after words such as order, PO, ticket or reference (with no Aadhaar context nearby) are downgraded to `AADHAAR_POSSIBLE` (warn only, not blocked). Presidio variants flag these without a warn/block distinction. A real Aadhaar written right after such a word, with no "aadhaar" within 40 characters, will only warn.
- UPI detection uses a fixed list of 22 handles; unlisted handles are missed. The Presidio baseline reuses this list, so UPI ties are by construction.
- The Presidio component runs with `language="en"` and score threshold 0.4. Language-grouped tables do not show multilingual quality.
- Global detection costs about 7.5 ms per scan versus about 0.07 ms for the native detector.
- Only the Chrome extension scans entirely in the browser. The web demo and proxy send text to a server.

## Privacy and limitations

- Use synthetic data or appropriately consented and anonymized samples. Do not place real personal identifiers, customer records, or credentials in test fixtures or public reports.
- The detector is rule-based and can miss unsupported formats, names, addresses, obfuscated data, and other sensitive information.
- Aadhaar checksum and context rules reduce certain false positives; they do not prove that a detected number belongs to a real person.
- The optional agent receives workflow metadata, finding types/confidence, and a redacted context marker; it is not sent source or masked prompt text. This does not guarantee that the deterministic detector finds every sensitive value before other application routes process it.
- The local LLM is advisory only. The deterministic detector and configured policy remain authoritative.
- The extension and backend have separate integration paths and need independent testing.
- The chat proxy needs additional security, authentication, upstream, and deployment review before real-data use.
- The in-memory rate limits are process-local and currently omit `/api/scan-global` and `/api/agentic/scan`; they are not distributed controls.
- SQLite is not encrypted by default. Cloud hosting, multi-instance rate limiting, at-rest database encryption, OCR, continuous monitoring, and a production security certification are not implemented features.
- Synthetic gold-set scores are not a substitute for evaluation on representative, consented, anonymized data.
- KAVACH is not a substitute for an organization's security controls, privacy review, or compliance program.

### Implemented controls and future work

Implemented in the current local application: loopback startup, token-protected API routes (with public `/api/health` readiness), same-origin write checks, response security headers, selected per-client rate limits, bounded TXT/PDF parsing, loopback-only Ollama requests, metadata-only SQLite audit records with configurable retention, and a browser extension with per-type policies. These controls reduce specific risks; they do not establish complete detection or security.

Future work, if the project scope expands, includes shared rate limiting for `/api/scan-global` and `/api/agentic/scan`, encrypted storage design, broader detector validation and language coverage, and a separately reviewed deployment model. OCR and additional file formats are not supported. There is no cloud service, 24/7 monitoring, production certification, or guarantee of detection accuracy.

## Demo checklist

For the full reproducible procedure, see
[`docs/demo_runbook.md`](docs/demo_runbook.md).

1. Check that Ollama and the configured `llama3.2:3b` model are available
   when demonstrating the optional local agent.
2. Start the FastAPI server with a local API token and confirm
   `GET /api/health` returns `status: ok`.
3. Open the dashboard and demonstrate its Protect and Settings sections.
4. Save the default protection mode and masking format, refresh the
   browser, and show that the preferences persist.
5. Demonstrate Standard + Label and Standard + Partial masking with
   synthetic phone and email data.
6. Demonstrate Autonomous + Partial masking and explain the simplified
   Protection Summary. Show the verification result only when it is
   accurately reported by the workflow.
7. Demonstrate document scanning and downloading the masked TXT output.
8. Load the unpacked Chrome extension and demonstrate its warning,
   masking, and blocking policies on supported AI sites.
9. Run the Python, dashboard JavaScript, and extension test commands.
10. Present evaluation dataset sizes, metrics, and limitations honestly.

## Responsible use

KAVACH Lite is a development project intended to reduce accidental exposure of sensitive information in AI prompts. It does not guarantee detection of all sensitive data or prevention of all information leaks.
