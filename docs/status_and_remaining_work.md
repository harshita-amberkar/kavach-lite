# KAVACH Lite — current status and remaining work

**Status snapshot:** 31 October 2026. Test counts below are from the user's recorded local Windows preflight output; they are not a claim that tests ran in this document-authoring session.

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

The latest recorded preflight after the proxy detector change reported:

- 59 Python unit tests passed.
- Python bytecode compilation passed.
- Eight blind-gold validator self-tests passed.
- Extension policy/privacy tests passed.
- Python/JavaScript detector parity: 1,557/1,557.
- Dashboard and extension JavaScript syntax checks passed.
- Extension manifest JSON validation passed.
- `git diff --check` passed; Git emitted LF-to-CRLF working-copy notices, not whitespace errors.

These results apply to that checkout and test run. Rerun the preflight after subsequent changes before committing or presenting final results.

## Remaining before final submission

1. **Proxy end-to-end regression: COMPLETED.** All three proxy tests passed, including a real global-only contextual-rule finding through a mocked upstream. The raw synthetic phrase was absent from the forwarded payload.
2. **Documentation and privacy wording: UPDATED.** README, demo runbook, extension options page and manifest now distinguish local browser scanning, Chrome Sync policy storage, the destination AI provider and the separate FastAPI proxy.
3. **Security validation:** independently review authentication, origin enforcement, upstream allowlisting, request limits, blocking/error handling, logging, extension behavior and deployment exposure. Do not call the proxy production-ready solely because mocked tests pass.
4. **Independent synthetic holdout:** collect 30–40 human-authored prompts from 3–4 people who have not seen the code, existing gold prompts or results. Use only synthetic values, freeze the commit, hash the dataset and run once. Do not tune against it.
5. **Manual browser testing:** verify the extension on the supported AI sites and record any site-UI compatibility issues.
6. **Submission materials:** review the final report, presentation placeholders, screenshots and demo runbook; rehearse the complete demo.

## Evaluation limitations

- Existing hand-written gold sets and development/regression sets have been used during detector development; they are not independent blind holdouts.
- The current `eval.fake` utility supplies seven types only: Aadhaar, PAN, phone, card, UPI ID, GSTIN and email. It does not generate IFSC or API-key fixtures.
- `eval.run` records language labels for grouped reporting, but calls each detector with prompt text only. Presidio in `global_detector.py` currently runs with `language="en"`. Language-grouped results must not be presented as proof of multilingual detection.
- `errors.jsonl` contains error kind, system, row ID, language/tag metadata, entity-type labels and character offsets; it does not contain raw prompt text or entity values. The external gold file itself does contain prompts and must remain private.
- Synthetic benchmark scores are limited to the tested distributions and do not establish production-wide accuracy.

## Completion criteria

- Focused proxy tests and full preflight pass on the frozen checkout.
- README, demo runbook, privacy wording and status documents match the code.
- Reviewed files are committed and `git status` is clean before independent data collection.
- Independent holdout is collected, hashed and run once without tuning.
- Final report and presentation clearly state scope, limits, test evidence and what remains unverified.
