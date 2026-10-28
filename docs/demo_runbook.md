# KAVACH Lite — Demo Runbook

## 1. Project overview

KAVACH Lite detects and masks supported sensitive information in prompts
before they are forwarded to AI services.

Components:
- Python detection and masking engine
- FastAPI backend and dashboard
- Chrome extension with privacy policies
- Optional local Ollama AI reviewer
- SQLite workflow audit history
- Evaluation and regression tests

## 2. Start-up checks

The most recently recorded verification run reported:
- 42 Python tests passed
- Extension policy/privacy checks passed
- 1557/1557 Python-JavaScript parity cases identical

Repeat these checks before the demonstration.

## 3. Demonstrate masking

Use this synthetic input:

Contact demo@example.com for support.

Expected masked output:

Contact [EMAIL] for support.

Explain that KAVACH detects supported sensitive values and applies the
configured protection policy.

## 4. Demonstrate the local AI reviewer

Ensure Ollama and the configured model are available.
Set the agent variables before starting the demonstration server:

$env:KAVACH_AGENT_ENABLED = "1"
$env:KAVACH_AGENT_TIMEOUT = "30"

Submit synthetic data to POST /api/agentic/scan.

A previous live test returned agent status "ok", workflow status
"completed", verification "passed", and audit status "saved".
Verify the statuses again during the demo.

The AI review is advisory; deterministic detection and masking remain
separate from its judgment.

## 5. Demonstrate audit history

Use GET /api/agentic/history with a valid KAVACH token.

Show workflow status, finding counts, agent status, verification status,
and human-review flags. Do not show tokens, raw prompts, or free-form
AI explanations.

## 6. Explain evaluation results

The locked synthetic dataset contains 51 prompts:
- 12 tagged real
- 12 tagged tricky
- 27 tagged neg

The recorded run reported micro-F1 of 1.00 and zero negative prompts
flagged for KAVACH and block mode.

These results are limited to a small handcrafted dataset and do not
establish production-wide accuracy.

## 7. Known limitations

- Evaluation datasets are small and synthetic.
- Pattern-based sanitization may miss unfamiliar sensitive formats.
- Local AI review can be unavailable or incorrect.
- Verification only checks findings supported by the scanner.
- Automated tests do not cover every deployment or attack scenario.

## 8. Final checklist

- [ ] Python tests pass.
- [ ] Extension privacy and parity checks pass.
- [ ] Dashboard authentication works.
- [ ] Synthetic prompt is masked as expected.
- [ ] Agent and verification statuses are checked separately.
- [ ] Audit history displays metadata only.
- [ ] No API tokens appear in screenshots or shared logs.
- [ ] Results are presented with dataset sizes and limitations.
