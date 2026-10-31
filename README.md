# KAVACH Lite: India-Aware PII Guardrail for AI Tools

KAVACH Lite is a privacy-focused project that detects and masks potentially sensitive information before it is shared with AI tools. It combines an India-aware rule-based detector, a FastAPI backend, a Chrome extension for prompt-time warnings and masking, an evaluation framework, and an optional local-LLM advisory reviewer.

KAVACH is a development project, not a guarantee that every sensitive value or data-leakage path will be detected.

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

- Windows with PowerShell, or Linux/macOS with a shell
- Python and packages in `requirements.txt`
- Node.js for extension tests
- Google Chrome to manually test the extension
- **Optional for the local agent:** Ollama and `llama3.2:3b`.

## Run locally: Windows PowerShell

Run commands from the project root (the directory containing `app.py`, `kavach/`, `eval/`, and `extension/`).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

If the virtual environment already exists, use it instead of recreating it. For this project, the explicit interpreter path also works:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Useful URLs:

- API health: `http://127.0.0.1:8000/api/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- Registered API schema: `http://127.0.0.1:8000/openapi.json`

The health endpoint in this version is `/api/health` (not `/health`).

The dashboard and protected API routes use the `X-KAVACH-Token` header.
For a local demo, configure a token in the same PowerShell process that
starts Uvicorn:

```powershell
$env:KAVACH_API_TOKEN = [guid]::NewGuid().ToString("N")
Set-Clipboard $env:KAVACH_API_TOKEN
```

Paste the copied token when the dashboard requests it. Do not commit,
share, or include the token in screenshots or logs.


### Optional autonomous local-agent setup

Install Ollama using its official installation instructions, then obtain the model:

```powershell
ollama pull llama3.2:3b
ollama list
```

Start the KAVACH API with the agent enabled in the same PowerShell process that launches Uvicorn:

```powershell
$env:KAVACH_AGENT_ENABLED = "1"
$env:KAVACH_AGENT_TIMEOUT = "30"
.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Configuration:

- `KAVACH_AGENT_ENABLED`: set to `1` to enable; default is disabled (`0`).
- `KAVACH_AGENT_TIMEOUT`: request timeout in seconds; default is `8`. A longer timeout may be needed for model startup or slow inference.
- `KAVACH_OLLAMA_URL`: defaults to `http://127.0.0.1:11434/api/generate`.
- `KAVACH_OLLAMA_MODEL`: defaults to `llama3.2:3b`.

These environment variables apply to the process launched from that terminal. Restart the API after changing them. Keep Ollama local for privacy-sensitive use; changing `KAVACH_OLLAMA_URL` to a remote service changes the data-flow and privacy assumptions.

During autonomous planning, Ollama receives a compact workflow summary and eligible-tool list, not the original or masked prompt. The separate advisory review path may send best-effort sanitized context. Sanitization patterns can miss unfamiliar secret formats, so keep the endpoint local and use synthetic data for testing. Model outputs cannot override deterministic detection, masking, verification, or policy decisions.

### Linux or macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

### Load the Chrome extension

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Select **Load unpacked** and choose the project's `extension/` directory.
4. Test using synthetic text only, and review the extension's configured policies before demonstration.

The extension targets ChatGPT, Claude, and Gemini. The developer previously reported 30/30 manual checks across these sites (16 ChatGPT, 7 Claude, 7 Gemini). These are limited manual checks, not comprehensive browser compatibility certification; website interface changes can require compatibility fixes.

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

The latest completed project verification run after the dashboard and
autonomous Partial-masking updates reported:

- Python unit tests: **67 passed** (full preflight, 31 October 2026).
- Dashboard JavaScript syntax check: **passed**.
- Python syntax checks for the application and autonomous runtime: **passed**.
- Extension policy/privacy tests: **passed**.
- Python/JavaScript detector parity: **1,557 of 1,557 cases identical**.
- Git whitespace check: **passed**.
- Autonomous Partial-masking regression test: **passed**.
- Genuine residual-finding remediation regression test: **passed**.

The live dashboard smoke test reported the expected Autonomous + Partial
output for the synthetic phone/email prompt. This is a developer-run
functional check, not a broad accuracy or security certification.

These results describe the tested development version. Repeat the checks
before a release or demonstration.

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
- All datasets are written by the project author (with AI assistance). No independent blind evaluation has been done. Perfect scores are regression results, not accuracy evidence.
- Checksum-valid 12-digit numbers right after words such as order, PO, ticket or reference (with no Aadhaar context nearby) are downgraded to `AADHAAR_POSSIBLE` (warn only, not blocked). Presidio variants flag these without a warn/block distinction. A real Aadhaar written right after such a word, with no "aadhaar" within 40 characters, will only warn.
- UPI detection uses a fixed list of 22 handles; unlisted handles are missed. The Presidio baseline reuses this list, so UPI ties are by construction.
- The Presidio component runs with `language="en"` and score threshold 0.4. Language-grouped tables do not show multilingual quality.
- Global detection costs about 7.5 ms per scan versus about 0.07 ms for the native detector.
- Only the Chrome extension scans entirely in the browser. The web demo and proxy send text to a server.

## Privacy and limitations

- Use synthetic data or appropriately consented and anonymized samples. Do not place real personal identifiers, customer records, or credentials in test fixtures or public reports.
- The detector is rule-based and can miss unsupported formats, names, addresses, obfuscated data, and other sensitive information.
- Aadhaar checksum and context rules reduce certain false positives; they do not prove that a detected number belongs to a real person.
- Agent context sanitization is best-effort. Patterns may fail to redact an unfamiliar secret format. Do not claim complete leakage prevention.
- The local LLM is advisory only. The deterministic detector and configured policy remain authoritative.
- The extension and backend have separate integration paths and need independent testing.
- The chat proxy needs additional security, authentication, upstream, and deployment review before real-data use.
- Synthetic gold-set scores are not a substitute for evaluation on representative, consented, anonymized data.
- KAVACH is not a substitute for an organization's security controls, privacy review, or compliance program.

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
