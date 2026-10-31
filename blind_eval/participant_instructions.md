# Independent synthetic prompt collection — participant instructions

## Purpose

Create a small, independently authored synthetic test set for KAVACH Lite. The aim is to check how a frozen detector handles naturally worded prompts written by people who have not seen its code, existing prompts or earlier results.

## Privacy and independence rules

- Use fictional scenarios and synthetic values only.
- Never use a real person's name with their actual phone number, email, government identifier, payment-card number, account number or credential.
- Do not copy prompts from the KAVACH README, presentation, dashboard samples, existing gold files, or internet examples.
- Do not ask an AI assistant to write or rewrite the prompts.
- Do not inspect KAVACH code, scanner output, or previous evaluation errors.

## Each participant writes exactly 10 rows

**Seven positive rows** (`real` or `tricky`):
- Use a mix of ordinary and less-obvious prompt wording.
- Include at least one `tricky` row with unusual spacing, punctuation, context, or code/text formatting.
- Use only the separate synthetic values supplied by the collector. Do not invent real-looking identifiers or credentials.
- The current `eval.fake` utility prints synthetic values for seven types only: `AADHAAR`, `PAN`, `PHONE`, `CARD`, `UPI_ID`, `GSTIN`, and `EMAIL`. It does not generate `IFSC` or `API_KEY`. Do not fabricate IFSC or API-key values; include those types only if the collector separately supplies reviewed synthetic fixtures.
- Across the group, cover the supplied types as evenly as natural prompt writing allows. A row may contain more than one marked value.
- Mark every sensitive value exactly with `[[TYPE:value]]`, keeping the value inside the brackets exactly as it appears in the prompt.

**Three negative rows** (`neg`):
- Write plausible ordinary prompts containing non-sensitive look-alikes, such as fictional order/reference/invoice/ticket numbers or ordinary technical text.
- Do not include actual sensitive identifiers or credentials.
- Do not put any `[[TYPE:value]]` markers in a negative row.

## Row format

Use one prompt per line, with an explicit language label and tag:

`en:real | prompt text with [[EMAIL:synthetic-value]]`

`en:tricky | prompt text with [[PAN:synthetic-value]]`

`en:neg | prompt text with no entity markers`

Use `hi`, `mr`, `hinglish`, or `mr_en` only when you naturally write the prompt in that language. Keep the annotation markers and type names exactly as shown. Do not add headings or comments to the data file.

**Language evaluation limitation:** the evaluator records the language label and produces language-grouped report sections, but its detector callback receives prompt text without a language argument. Presidio in KAVACH's global detector is currently invoked with `language="en"`. Non-English rows are exploratory and must not be described as evidence of validated multilingual detection. Prefer English rows for the main comparable sample; include non-English rows only when a participant can write them naturally.

## Synthetic values supplied by the collector

The current utility can be run from the project root with:

`.\.venv\Scripts\python.exe -m eval.fake`

It prints one generated value for each of the seven supported types listed above. It does not provide a `--help` interface or write a dataset file. The collector should run it separately for each participant and distribute each participant's generated values privately. Never use real personal data or actual credentials. If a value cannot be safely generated, omit that type from the holdout rather than inventing a real-looking value.

## Independence

Do not discuss KAVACH detection rules or expected scanner behavior with other participants. The task is to write natural prompt examples, not to reverse-engineer the detector. The collector should keep each participant's rows in a separate file until merging and record anonymous participant IDs only (P01, P02, etc.).
