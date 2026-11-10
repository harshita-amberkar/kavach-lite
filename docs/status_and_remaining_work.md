# KAVACH Lite — current status and remaining work

**Status snapshot:** 31 October 2026. Test counts below are from the user's recorded local Windows preflight output; they are not a claim that tests ran in this document-authoring session.

**Supported release operation:** local Windows use through the PowerShell
launchers. Docker files are experimental and unsupported for this release;
token provisioning, persistent SQLite storage, and multi-process rate
limiting have not been validated. Do not expose the Docker configuration to
a network or treat it as production-ready.

## Security implementation update — 4 November 2026

Since this historical status snapshot, the current source includes local-only Ollama validation/proxy controls, source-text exclusion from Ollama requests, bounded TXT/PDF uploads, pypdf resource limits, security headers/CSP, selected in-memory per-client API rate limits, and transactional 30-day audit retention. See the current README and `docs/security_validation.md` for exact behavior. SQLite remains unencrypted by default; rate limits remain single-process; the extension does not run backend Presidio. These controls do not amount to a production security review or guarantee detection accuracy.

## Implemented

- Python deterministic detection, masking and risk scoring.
- Global detection layer combining KAVACH-native rules, Presidio and selected contextual/secret rules.
- FastAPI backend and dashboard with Protect/Settings, Standard/Autonomous workflows, text and supported file scanning.
- Chrome extension content scripts for ChatGPT, Claude and Gemini with per-type Allow/Warn/Mask/Block policies.
- Optional bounded local Ollama reviewer/workflow; deterministic detection and masking remain authoritative.
- Metadata-oriented workflow audit storage.
- Configured OpenAI-compatible chat-completions proxy with request validation, masking and allowlisted upstream payload construction.
- Chat proxy now invokes `analyze_global(content)`; `/api/scan` remains on the lightweight `analyze()` path.
- Validation support files: blind-gold validator, eight validator self-tests, Windows preflight and one-time external holdout runner.

## Recorded local validation

The latest recorded preflight after the global detector context-filter changes reported:

- 67 Python unit tests passed.
- Python bytecode compilation passed.
- Eight blind-gold validator self-tests passed.
- Extension policy/privacy tests passed.
- Python/JavaScript detector parity: 1,557/1,557.
- Dashboard and extension JavaScript syntax checks passed.
- Extension manifest JSON validation passed.
- `git diff --check` passed; Git emitted LF-to-CRLF working-copy notices, not whitespace errors.

These results apply to that checkout and test run. Rerun the preflight after subsequent changes before committing or presenting final results.

## Remaining before final submission

1. **Proxy end-to-end regression: COMPLETED.** All six proxy tests passed: email masking, mocked global finding, real contextual finding, bearer-secret masking, high-risk blocking before forwarding, and contextual fallback when Presidio is unavailable.
2. **Documentation and privacy wording: UPDATED.** README, extension options page and manifest distinguish local browser scanning, Chrome Sync policy storage, the destination AI provider and the separate FastAPI proxy.
3. **Deployment/security work remains future work:** selected authentication, origin, request, header, rate-limit, privacy and upload controls are implemented and regression-tested locally. A separately designed and reviewed non-loopback/multi-instance deployment, shared rate limiting, encrypted storage, and real-provider validation are not implemented. Do not call the proxy production-ready solely because mocked tests pass.
4. **Independent synthetic holdout: COMPLETED.** A separate, project-authored synthetic set was frozen by SHA-256 and evaluated without tuning. This is not a human evaluation; the abandoned participant-collection workflow was not used. See `docs/independent_synthetic_holdout.md` and `results/independent_synthetic_holdout/`.
5. **Manual browser testing: COMPLETED for selected cases.** User-reported tests passed for EMAIL Mask, Warn and Block on ChatGPT, Claude and Gemini; EMAIL Block persisted after reloading; and a synthetic PAN was detected and masked on ChatGPT. Continue checking site compatibility as supported sites change; these tests do not cover every identifier or site state.
6. **Submission materials:** review the final report, presentation placeholders and screenshots. Any demonstration should use synthetic data.

## Evaluation limitations

- Existing hand-written gold sets and development/regression sets have been used during detector development; they are not independent blind holdouts.
- The current `eval.fake` utility supplies seven types only: Aadhaar, PAN, phone, card, UPI ID, GSTIN and email. It does not generate IFSC or API-key fixtures.
- `eval.run` records language labels for grouped reporting, but calls each detector with prompt text only. Presidio in `global_detector.py` currently runs with `language="en"`. Language-grouped results must not be presented as proof of multilingual detection.
- `errors.jsonl` contains error kind, system, row ID, language/tag metadata, entity-type labels and character offsets; it does not contain raw prompt text or entity values. The external gold file itself does contain prompts and must remain private.
- Synthetic benchmark scores are limited to the tested distributions and do not establish production-wide accuracy.

## Completion criteria

- Focused proxy tests and full preflight pass on the frozen checkout.
- README, privacy wording and status documents match the code.
- Reviewed files are committed and `git status` is clean before independent data collection.
- The separate synthetic holdout is generated reproducibly, hash-checked and evaluated without tuning. Human-authored participant collection is not part of this milestone.
- Final report and presentation clearly state scope, limits, test evidence and what remains unverified.


## Manual browser extension validation ? 31 October 2026

User-reported manual tests completed successfully:

- EMAIL Mask, Warn and Block policies passed on ChatGPT, Claude and Gemini.
- EMAIL Block policy persisted after reloading the Chrome extension.
- A synthetic PAN-format value was detected and masked as `[PAN]` on ChatGPT.

Scope note: These are manual browser validation results, not an independent security audit or proof that every identifier, browser version, device or application state has been tested.

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
