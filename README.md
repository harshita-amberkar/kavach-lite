# KAVACH Lite: India-Aware PII Guardrail for AI Tools

KAVACH Lite is a privacy-focused project that detects and masks potentially sensitive information before it is shared with AI tools. It combines an India-aware rule-based detector, a FastAPI backend, a Chrome extension for prompt-time warnings and masking, an evaluation framework, and an optional local-LLM advisory reviewer.

KAVACH is a development project, not a guarantee that every sensitive value or data-leakage path will be detected.

## Features

- **Sensitive-data detection:** configured recognizers for Aadhaar, PAN, phone numbers
, payment-card numbers, email addresses, UPI IDs, GSTIN, IFSC, and supported secrets.
- **Checksum/context checks:** Aadhaar Verhoeff, GSTIN check-character, and card Luhn validation help reduce certain false positives.
- **Masking and risk scoring:** scan responses include finding types, character offsets, confidence scores, masked text, and a risk assessment.
- **Chrome extension:** prompt scanning and configurable allow, warn, mask, and block actions for ChatGPT, Claude, and Gemini. Website UI changes can affect compatibility.
- **FastAPI backend:** text scanning, file scanning, and a configured OpenAI-compatible chat-completions proxy route.
- **Evaluation lab:** hand-written gold-set evaluation, synthetic benchmarks, comparison systems, and Python/JavaScript detector-parity tests.
- **Optional local-LLM reviewer:** Ollama with `llama3.2:3b` can return advisory assessments for detector findings. It is disabled by default and does not change detector findings, masking, risk scores, or policy decisions.

**Novelty note:** Microsoft Presidio already has `IN_AADHAAR` and `IN_PAN` recognizers, and commercial data-protection products exist. KAVACH does not claim that Indian-ID detection alone is novel. Its project focus is the evaluated combination of India-aware detection, prompt-time browser protection, policy actions, and a local advisory workflow.

## Architecture

```text
User prompt
    |
    +--> Chrome extension --> JavaScript detector --> policy action
    |
    +--> FastAPI /api/scan --> Python detection engine
                                  |
                                  +--> findings, masked text, risk
                                  |
                                  +--> optional local Ollama review
                                       (sanitized context; advisory only)

Gold dataset / benchmark --> evaluation reports in results/
```

The extension and backend are separate execution paths. They share detector behavior through a JavaScript/Python parity suite, but each path still needs its own integration testing. The optional agent is separate from the deterministic decision path.

## Requirements

- Windows with PowerShell, or Linux/macOS with a shell
- Python and packages in `requirements.txt`
- Node.js for extension tests
- Google Chrome to manually test the extension
- **Optional:** Ollama and `llama3.2:3b` for local-LLM review

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

### Optional local agent setup

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

The agent sends finding metadata and a short, best-effort sanitized context to the configured Ollama endpoint. Redaction patterns cannot guarantee removal of every possible secret. Agent assessments are advisory and must not be treated as authoritative detection or policy decisions.

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

The extension targets ChatGPT, Claude, and Gemini. Changes to those sites' interfaces can require compatibility fixes. Manual checks have previously reported clean-prompt submission, email warning, masking, and blocking working; this is not comprehensive browser compatibility certification.

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

### Other routes

- `POST /api/scan-file`
- `POST /v1/chat/completions`

The chat-completions route is a configured upstream proxy. Before using it with real data, separately review and test upstream forwarding, authentication, masking, blocking, error handling, and deployment configuration. Do not assume it is production-ready based only on the scan tests.

## Tests

Run these from the project root.

### Python tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

### Extension policy/privacy and detector parity

```powershell
node .\extension\tests\policy_and_privacy.js
node .\extension\tests\parity.js
```

### Python syntax check

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py kavach\agent.py kavach\detectors.py
```

### Evaluation

```powershell
.\.venv\Scripts\python.exe -m eval.run --gold
.\.venv\Scripts\python.exe -m eval.benchmark
```

The evaluation runner writes `results/report.md`, `results/report.json`, and `results/errors.jsonl`. The gold dataset is at `eval/gold/gold.txt`. Run `python -m eval.run --help` for supported options.

## Current verification status

The most recent reported release-check run completed successfully:

- Python unit tests: **22 passed**.
- Extension policy/privacy checks: **passed**.
- JavaScript/Python detector parity: **1,557 of 1,557 cases matched**.
- Python syntax checks for `app.py`, `kavach/agent.py`, and `kavach/detectors.py`: **passed**.
- Live API smoke check after the sanitizer update: email was detected and masked; local agent review returned `status: ok`.
- Three-case live smoke test: Email, PAN, and UPI returned their expected types with successful agent reviews after the PAN test value was corrected.

These are reported development checks. The live agent results are smoke tests, not an accuracy study of model judgments.

## Gold-set benchmark results

Latest reported run: **51 hand-written prompts** in `eval/gold/gold.txt` (27 tagged `real`, 4 tagged `tricky`, and 20 tagged `neg`). The Hindi test entry was repaired to use readable Unicode and a checksum-valid synthetic Aadhaar test value. The detector code was not changed for that dataset repair.

| System | Micro precision | Micro recall | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| KAVACH | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.039 ms | 0.074 ms |
| KAVACH block | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.036 ms | 0.069 ms |
| Regex-only | 0.66 | 0.88 | 0.75 | 8/20 (40%) | 0.021 ms | 0.037 ms |
| Presidio | 0.76 | 0.70 | 0.73 | 7/20 (35%) | 7.005 ms | 17.028 ms |
| Presidio custom | 0.81 | 0.97 | 0.89 | 7/20 (35%) | 6.802 ms | 8.421 ms |
| Presidio normalized | 0.82 | 1.00 | 0.90 | 7/20 (35%) | 6.890 ms | 8.550 ms |

On this dataset, KAVACH reported per-type precision/recall/F1 of 1.00 for Aadhaar, card, email, GSTIN, PAN, phone, and UPI ID. This result applies only to the tested cases. The dataset is small and hand-written, so perfect scores do not establish real-world performance or generalization. The negative false-alarm result is based on only 20 negative prompts.

The latency figures above are detector/evaluation measurements; they do **not** include local-LLM inference or represent end-to-end API latency. The agent has not yet been evaluated against a sufficiently large labelled set for advisory-review accuracy, and its model latency varies with startup and host performance.

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

1. Start Ollama if demonstrating the optional agent, and confirm `llama3.2:3b` is available.
2. Start the FastAPI service; confirm `GET /api/health` returns `status: ok`.
3. Open `/docs` and demonstrate a clean prompt and a synthetic prompt containing an email, PAN, or UPI ID.
4. Demonstrate the masked text, finding type, and risk score.
5. Enable `KAVACH_AGENT_ENABLED=1` and show the additional advisory review. Explain that it does not change detection or policy decisions.
6. Load the `extension/` directory unpacked in Chrome and demonstrate warning/masking behavior on a supported AI site using synthetic text.
7. Run the Python and extension test commands and show the current gold-set report.
8. State the dataset size, limitations, and best-effort nature of agent sanitization honestly.

## Responsible use

KAVACH Lite is a development project intended to reduce accidental exposure of sensitive information in AI prompts. It does not guarantee detection of all sensitive data or prevention of all information leaks.
