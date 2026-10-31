# KAVACH Lite — Remaining validation work pack

This folder contains reviewed support material for final validation. The proxy/global-detector decision has already been implemented in the current checkout; see `docs/proxy_detector_scope_plan.md` for the current state and remaining regression coverage.

## Included

- `blind_eval/participant_instructions.md` — protocol for 3–4 independent writers to create a synthetic holdout.
- `blind_eval/collector_checklist.md` — merge, freeze and one-run checklist.
- `tools/validate_blind_gold.py` — format/annotation validator; does not run KAVACH or print prompt contents.
- `tools/test_validate_blind_gold.py` — eight validator self-tests; these are not KAVACH detector tests.
- `tools/run_preflight.ps1` — Windows preflight for Python, JavaScript, extension and syntax checks.
- `tools/run_blind_eval.ps1` — validates and hashes an external holdout, runs it once, archives results beside the external gold file, and restores existing `results/report.*` files.
- `docs/security_review_2026-10-30.md` — source-snapshot security review; verify each item against the current checkout before treating it as complete.
- `docs/proxy_detector_scope_plan.md` — implementation record for the chat-proxy global-detector change.

## Current findings

- `/v1/chat/completions` now calls `analyze_global()` before forwarding masked message content. `/api/scan` intentionally remains on `analyze()`.
- Presidio in the global detector is invoked with `language="en"`; language-grouped evaluation tables do not prove multilingual detection because the detector callback receives text without the row language.
- The extension scans prompt text locally in the browser. Its per-type policy uses `chrome.storage.sync`. The inspected extension source has no direct fetch/XHR/beacon/WebSocket request, but the extension privacy statement must not claim that all settings are exclusively local or that the destination AI service never receives a submitted prompt.
- `eval.fake` prints synthetic values for seven types only (`AADHAAR`, `PAN`, `PHONE`, `CARD`, `UPI_ID`, `GSTIN`, `EMAIL`). It has no `--help` interface and does not generate `IFSC` or `API_KEY`.
- `eval/run.py` writes error metadata, entity-type labels and character offsets; its error records do not include raw prompt text or entity values.

## Global detection benchmark ? 31 October 2026

Latest recorded run: generated synthetic test split, 165 prompts including 45 negative prompts.

- Global detector false-alarm rate: 0% (0/45 negative prompts flagged).
- Global MICRO_ALL: precision 0.92, recall 1.00, F1 0.96.
- Global MICRO_SHARED: precision 1.00, recall 1.00, F1 1.00.
- Global latency: p50 7.490 ms; p95 12.693 ms.
- Native KAVACH false-alarm rate: 0%; MICRO_ALL F1: 1.00.
- Five focused global-detector regression tests were added; the full suite passed with 67 Python tests.

Limitations:
- PERSON and LOCATION have no corresponding gold-positive examples in this dataset. Their detection quality is not established.
- The benchmark is self-authored synthetic evaluation, not an independent blind evaluation or production accuracy claim.
- Language-grouped report sections do not establish multilingual detection: Presidio is invoked with language="en", and the detector does not receive the row language label.
- Global detection is slower than the native detector; its additional coverage has a measurable latency cost.

## Recommended order

1. The chat proxy now uses `analyze_global()`. All six proxy masking tests passed, covering email, global findings, contextual masking, bearer-secret masking, high-risk blocking and Presidio-failure fallback.
2. The full Windows preflight passed on 31 October 2026: 67 Python tests, eight validator self-tests, extension checks, 1,557/1,557 detector parity and syntax checks.
3. Review the final Git diff and commit only approved source, tests, tools and documentation. Ensure `git status` is clean.
4. Record the frozen Git commit before any participant writes prompts.
5. Give the instructions to 3?4 people who have not seen KAVACH code, existing gold prompts, previous results or scanner output. Use only synthetic values.
6. Collect, merge and validate the holdout outside the Git repository.
7. Run `tools\run_blind_eval.ps1` once. Preserve the hash and archive; do not tune against this dataset.

## Output handling

The blind-runner's `errors.jsonl` contains metadata and offsets, not raw prompt contents or entity values. The external gold file contains the prompt text and annotations. Keep that file and its archive private even though the values are synthetic. The runner refuses a dirty Git tree, refuses a gold file inside the repository, records the commit and SHA-256, and refuses to run when its one-time lock folder already exists.
