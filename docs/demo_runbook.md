# KAVACH Lite — Demo Runbook

**Updated:** 30 October 2026
**Latest application commit:** `e9c2cc6`

## 1. Project overview

KAVACH Lite detects and masks supported sensitive information in prompts
before users share them with AI tools.

Main components:
- Python detection and masking engine
- FastAPI backend and dashboard
- Global detection using KAVACH rules and Presidio
- Chrome extension for ChatGPT, Claude and Gemini
- Optional autonomous privacy workflow using local Ollama
- SQLite workflow audit metadata
- Synthetic evaluation and regression tests

The dashboard has two user-facing sections:

- **Protect:** scan prompts, choose protection options, inspect protected
  output, copy it and scan supported documents.
- **Settings:** save default protection mode and masking format, and find
  Chrome extension policy instructions.

The dashboard no longer displays Recent Activity. Backend audit recording
and the history API remain available.

## 2. Understand the two protection choices

Protection mode and masking format are separate settings.

### Protection mode

| Mode | Purpose |
|---|---|
| Standard | Runs global detection and masking. |
| Autonomous | Runs the bounded multi-step workflow, including verification and audit recording. |

### Masking format

| Format | Purpose |
|---|---|
| Label | Replaces detected values with labels such as `[EMAIL]` and `[PHONE]`. |
| Partial | Keeps the last four digits for supported Aadhaar, card and phone findings. Other types continue to use labels. |

Dashboard defaults are stored in the current browser's local storage.
They do not configure Chrome extension per-type policies.

## 3. Start KAVACH

Open PowerShell in:

`C:\Users\vijay\Downloads\kavach\kavach`

### Check Ollama

```powershell
ollama --version
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

The configured demo model in the current setup is `llama3.2:3b`.

If Ollama is not running, start it in a separate terminal:

```powershell
ollama serve
```

Do not start another instance if the service is already running.

### Start the FastAPI server

In the KAVACH project terminal:

```powershell
.\.venv\Scripts\Activate.ps1

$env:KAVACH_API_TOKEN = [guid]::NewGuid().ToString("N")
Set-Clipboard $env:KAVACH_API_TOKEN

$env:KAVACH_AGENT_ENABLED = "1"
$env:KAVACH_AGENT_TIMEOUT = "30"

.\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

Keep this terminal open. The API token is copied to the clipboard.
Paste it into the dashboard when prompted. Do not display or commit it.

To demonstrate without local AI review, use
`$env:KAVACH_AGENT_ENABLED = "0"` before starting the server.
Deterministic scanning and masking remain available.

Open:

`http://127.0.0.1:8000/`

Check the health endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected: a successful response with status `ok`.

## 4. Demonstrate Settings

Open **Settings**.

Demonstrate:
1. Default protection mode: Standard or Autonomous.
2. Default masking format: Label or Partial.
3. Save preferences.
4. Refresh the page and confirm that the preferences persist.
5. Use Reset defaults to restore Standard and Label.

These settings are browser-local dashboard preferences.

### Chrome extension policies

The extension has separate per-data-type actions:
- Allow
- Warn
- Mask automatically
- Block

To configure them:
1. Open `chrome://extensions`.
2. Find KAVACH and select Details.
3. Open Extension options.
4. Choose the action for each supported data type.
5. Save settings.

Extension policies use Chrome extension storage and are managed
separately from dashboard preferences.

## 5. Demonstrate Standard protection

Open **Protect** and select Standard.

Use synthetic data:

```text
Contact Demo User.
Phone: 9876543210
Email: demo@example.com
```

Choose Partial and click **Check & Protect**.

Expected protected output:

```text
Contact Demo User.
Phone: XXXXXX3210
Email: [EMAIL]
```

Switch to Label and scan again.

Expected:

```text
Contact Demo User.
Phone: [PHONE]
Email: [EMAIL]
```

Show:
- Detected item count and risk information
- View detected items
- Protected prompt preview
- Copy protected prompt

Explain that users should review the protected prompt before sharing.
Detection is heuristic and cannot guarantee that every sensitive value
will be found.

## 6. Demonstrate Autonomous protection

Choose Autonomous and Partial.

Use the same synthetic prompt and select **Check & Protect**.

Expected protected output:

```text
Contact Demo User.
Phone: XXXXXX3210
Email: [EMAIL]
```

The Protection Summary communicates the outcome in user-friendly terms:
- Protection check completed
- Verified, when verification passed and no human review is required
- Review recommended, when the workflow needs human attention
- Number of detected items

The technical workflow details are intentionally hidden from normal
dashboard users.

### Explain the autonomous workflow

Internally, the workflow coordinates:
1. Global sensitive-information scanning
2. Bounded autonomous tool selection
3. Deterministic masking
4. Verification of protected output
5. Remediation or human-review escalation
6. Metadata-only audit recording

The local model is advisory. It does not control authoritative
detection or masking.

### Partial-masking verification regression

A previous issue caused the last four digits retained by Partial masking
to be misclassified during autonomous verification. The runtime was
updated to avoid treating exact, intentionally partially masked spans
as new findings during the verification rescan.

Regression tests cover:
- Correct preservation of a partial phone mask.
- Remasking of genuine residual findings.

Test:
`test_partial_phone_suffix_is_not_remasked_as_person`

## 7. Demonstrate document scanning

Under Protect, select a synthetic TXT or text-based PDF.

Current limits:
- TXT and text-based PDF
- Maximum file size: 5 MB
- Image-only PDF/OCR is not supported in the current scope.

Steps:
1. Choose a document.
2. Select Scan document.
3. Review findings and risk information.
4. Inspect the masked text.
5. Select Download masked TXT.
6. Open the downloaded file and confirm the output is masked.

## 8. Demonstrate the Chrome extension

Open `chrome://extensions`.

If not already installed:
1. Enable Developer mode.
2. Select Load unpacked.
3. Select the project's `extension` folder.
4. Confirm KAVACH is enabled.

Supported sites in the current manifest:
- `https://chatgpt.com`
- `https://chat.openai.com`
- `https://claude.ai`
- `https://gemini.google.com`

Use synthetic information. Demonstrate:
- A clean prompt
- A prompt that triggers a warning
- Automatic masking
- Blocking under a Block policy
- The extension Options page

The extension performs its detection and masking locally in the browser.
Repeat manual browser checks after website UI changes.

## 9. Explain audit metadata

SQLite stores workflow metadata rather than original prompts or raw
sensitive values.

The history endpoint remains available:

`GET /api/agentic/history?limit=10`

It requires a valid `X-KAVACH-Token` header.

Example:

```powershell
$token = Read-Host "Paste the KAVACH_API_TOKEN"
$headers = @{ "X-KAVACH-Token" = $token }

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/agentic/history?limit=10" `
  -Headers $headers
```

Show only metadata such as workflow status, risk, finding types,
verification status and human-review flags. Never show tokens or raw
sensitive values during the demo.

## 10. Evaluation results and limitations

The locked synthetic v1 dataset contains 51 prompts:
- 12 tagged real
- 12 tagged tricky
- 27 tagged neg

The recorded KAVACH run reported:
- Micro precision: 1.00
- Micro recall: 1.00
- Micro F1: 1.00
- Negative prompts flagged: 0/27

These results apply only to a small handcrafted synthetic dataset.
They do not establish production-wide accuracy or guarantee detection
of unfamiliar sensitive information.

The holdout regression dataset was previously used to guide detector
fixes. Do not describe it as an untouched blind test set.

## 11. Run tests before a demonstration

From the project root:

### Python test suite

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Latest recorded result for the committed version: 57 tests passed.

### Python syntax

```powershell
.\.venv\Scripts\python.exe -m py_compile .\app.py .\kavach\agent_runtime.py
```

### Dashboard JavaScript

```powershell
node --check .\static\app.js
```

### Extension policy and privacy checks

```powershell
node .\extension\tests\policy_and_privacy.js
```

### Python–JavaScript parity

```powershell
node .\extension\tests\parity.js
```

Latest recorded result: 1557/1557 parity cases identical.

### Git whitespace check

```powershell
git diff --check
```

Repeat checks after code changes rather than relying only on historical
results.

## 12. Troubleshooting

| Problem | Check |
|---|---|
| Dashboard does not open | Check Uvicorn and `/api/health`. |
| API returns 401 | Check the dashboard API token. A server restart may rotate a generated token. |
| Autonomous review unavailable | Check the agent environment variable, Ollama service and configured model. |
| Old dashboard appears | Press Ctrl + Shift + R. |
| Settings do not persist | Check browser local storage and the dashboard origin. |
| Extension is unavailable | Check `chrome://extensions` and reload the unpacked extension. |
| PDF scan fails | Check that it is text-based and within the 5 MB limit. |
| Unexpected detection | Inspect finding type and positions, then reproduce with synthetic data before changing detection rules. |

## 13. Security and known limitations

- Detection is heuristic and may miss unfamiliar formats.
- Small synthetic datasets do not prove broad real-world accuracy.
- Presidio and local AI review can produce false positives or be unavailable.
- Verification checks patterns supported by the configured scanner.
- Successful verification does not guarantee that no sensitive information remains.
- Local AI review is advisory.
- Keep the demo server bound to `127.0.0.1`.
- Use synthetic or approved anonymized data.
- Automated tests do not cover every deployment, browser update or attack scenario.

## 14. Final demonstration checklist

- [ ] Ollama and configured model checked.
- [ ] KAVACH server starts successfully.
- [ ] API token configured and kept private.
- [ ] Dashboard and health endpoint work.
- [ ] Protect and Settings navigation work.
- [ ] Dashboard preferences persist after refresh.
- [ ] Standard + Label tested.
- [ ] Standard + Partial tested.
- [ ] Autonomous + Partial tested.
- [ ] Autonomous verification status checked.
- [ ] Protected prompt copy works.
- [ ] Document scanning and masked download tested.
- [ ] Chrome extension tested on supported sites.
- [ ] Extension policies demonstrated.
- [ ] Audit endpoint returns metadata only.
- [ ] Python and extension tests pass.
- [ ] Evaluation results shown with dataset sizes and limitations.
- [ ] No tokens or real sensitive values appear in screenshots or logs.