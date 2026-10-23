# Kavach browser extension (Chrome / Edge)

Scans your prompt before it is sent to ChatGPT, Claude or Gemini. Detection runs in the page; the
extension has no network code and requests only the `storage` permission (enforced by a test).

## Load it
1. Open `chrome://extensions`, switch on **Developer mode**.
2. **Load unpacked** and choose this `extension` folder.
3. Open the extension's **Details > Extension options** to set Allow / Warn / Mask / Block per data type.

## Try it
Open a supported site, type `my pan is ABCPE1234F`, press Enter. A dialog should appear.
Use `python -m eval.fake` for realistic fake values. Never test with real personal data.

## Tests (need Node 18+)
    python -m eval.export_parity extension/tests/parity.json
    node extension/tests/parity.js                 # JS port must equal the Python detector
    node extension/tests/policy_and_privacy.js     # policy rules + no-network / minimal-permission check

## Known limits
- Site selectors for the prompt box and send button are heuristics; AI sites change their pages often.
- "Send anyway" clicks the send button if found, otherwise asks you to press send again.
- Browser-only: it cannot stop a user switching browser or app. Not a replacement for enterprise DLP.
