# Chat proxy detector scope — implementation record

## Decision

The privacy-protection contract is to use the global detector in the chat proxy so that proxy scanning is aligned with the broader global-detection path, rather than silently using only the lightweight detector.

## Current implementation (checked 31 October 2026)

- `validate_and_mask_chat_payload()` in `app.py` calls `analyze_global(content)`.
- The proxy uses the global detector's default label-masking mode before constructing the upstream payload.
- `POST /api/scan` remains on the lightweight `analyze()` path. This is intentional; the two scan endpoints have different documented scopes.
- The global detector combines KAVACH-native rules, Presidio recognizers and selected contextual rules. The inspected implementation calls Presidio with `language="en"`; contextual and native rules also run when the Presidio stage raises an exception.

## Proxy regression coverage

The current `tests/test_chat_proxy_masking.py` contains:

1. A mocked-upstream test confirming an email is masked before forwarding.
2. A mocked global-detector test confirming that the proxy calls `analyze_global()`, forwards its masked text, and reports the redaction count.
3. A real contextual-rule test using a fictional confidential-business sentence that triggers `CONFIDENTIAL_BUSINESS` in `analyze_global()` but not in `analyze()`.
4. A bearer-secret test confirming that the raw synthetic canary is absent from the mock-upstream payload.
5. A high-risk blocking test confirming HTTP 422 and zero upstream requests.
6. A Presidio-failure test confirming contextual masking still occurs.

All six proxy tests passed on 31 October 2026. They cover masking, redaction accounting, secret removal, high-risk blocking and contextual fallback when Presidio is unavailable. All use a mocked upstream.

## Remaining validation

- Completed: the real global-only contextual rule was exercised through the proxy using a mocked upstream; the original synthetic phrase was absent from the forwarded payload.
- Retain tests for masking, redaction accounting and existing auth/origin/allowlist/request-validation behavior.
- Completed: full Windows preflight passed on 31 October 2026 with 62 Python tests and all recorded validator, extension, parity and syntax checks.
- Measure detector/proxy latency if making performance claims. Do not infer end-to-end latency from detector-only timings.
- Keep the proxy bound to a local/mock upstream until authentication, upstream forwarding, blocking, error handling, rate limits and deployment configuration have been independently reviewed.

## Language and accuracy limits

The Presidio call in `kavach/global_detector.py` uses `language="en"`. The evaluator's language field is used to group/report rows; the detector callback in `eval/run.py` receives the prompt text, not the row language. Therefore language-wise report sections are metadata-based slices, not proof that the detector selected or supports each language. Do not claim multilingual detection based on those tables.
