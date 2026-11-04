# Kavach browser extension (Chrome / Edge)

Scans your prompt before it is sent to ChatGPT, Claude or Gemini. Detection runs in the page; the
extension has no network code and requests only the `storage` permission (enforced by a test).
The extension does not send prompt text to the KAVACH backend; if you choose to submit, the
destination AI site receives the content left by the configured policy (original or masked).
Per-type extension policies are synchronized through
Chrome storage. This local extension behavior does not describe the separate backend chat proxy.

## Load it
1. Open `chrome://extensions`, switch on **Developer mode**.
2. **Load unpacked** and choose this `extension` folder.
3. Open the extension's **Details > Extension options** to set Allow / Warn / Mask / Block per data type.

## Try it
Open a supported site, type `my pan is ABCPE1234F`, press Enter. A dialog should appear.
Use `python -m eval.fake` for realistic fake values. Never test with real personal data.

## Tests (need Node 18+)

Run these non-mutating checks from the repository root. They do not regenerate or rewrite the parity fixture:

```sh
node --check extension/content.js
node --check extension/options.js
node extension/tests/policy_and_privacy.js
node extension/tests/parity.js
```

`eval/regen_parity.py` is a fixture-generation utility, not a test command; it rewrites `extension/tests/parity.json` and creates a backup.

## Known limits
- Site selectors for the prompt box and send button are heuristics; AI sites change their pages often.
- "Send anyway" clicks the send button if found, otherwise asks you to press send again.
- `AADHAAR_POSSIBLE` is not shown in the Options page, so users cannot configure it there. Its default policy action is **Warn**. The policy resolver can honor an explicit `AADHAAR_POSSIBLE` value if one is supplied internally, but the Options page cannot set it and saving options omits that value.
- **Native Python and extension shared types:** AADHAAR, AADHAAR_POSSIBLE, PAN, GSTIN, PHONE, CARD, EMAIL, UPI_ID, IFSC, API_KEY, PASSWORD, OTP, and PASSPORT. Their tested native rule behavior is compared on the 1,557-case parity fixture. The fixture now reflects the current Python source; nine stale Aadhaar-context expectations were corrected.
- **Additional deterministic rules in the extension:** complete private-key/database-URL/Bearer/JWT patterns as `API_KEY`, explicitly labelled US SSNs, selected medical-context phrases, and selected confidential-business phrases. These mirror the backend's deterministic global rules and are covered by shared synthetic cases.
- **Backend global-only Presidio types:** PERSON, LOCATION, IBAN, IP_ADDRESS, MAC_ADDRESS, CRYPTO, MEDICAL_LICENSE, NRP, US_ITIN, US_DRIVER_LICENSE, US_PASSPORT, US_BANK_NUMBER, UK_NINO, UK_NHS, UK_PASSPORT, AU_ABN, AU_ACN, AU_TFN, and AU_MEDICARE. The extension does not run Presidio, so it does not detect these types. Presidio can also find different formats of types the extension already supports; for example, global detection may identify a person or location where the extension does not. The extension's US_SSN rule is limited to explicitly labelled SSNs; Presidio may recognize other forms.
- `1557/1557` parity refers only to `scanNative()` versus the checked-in native Python fixture. It does not claim parity with Presidio. Separate shared regression cases cover the deterministic global rules included in the extension and representative Presidio-only results.
- The global API masks all findings according to its label/partial mode. The extension instead applies its own per-type Allow/Warn/Mask/Block policy and uses label masking; these policies and partial-mask behavior are not equivalent.
- Browser-only: it cannot stop a user switching browser or app. Not a replacement for enterprise DLP.
