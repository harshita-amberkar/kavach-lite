# Collector checklist — freeze the blind evaluation

## Before collecting

- [ ] Freeze the KAVACH detector and record the current Git commit.
- [ ] Ensure the three or four writers have not seen the detector, existing gold files, previous evaluation reports or scanner output.
- [ ] From the project root, run `.\.venv\Scripts\python.exe -m eval.fake` separately for each participant. This prints seven synthetic values (`AADHAAR`, `PAN`, `PHONE`, `CARD`, `UPI_ID`, `GSTIN`, `EMAIL`); it does not support `--help` and does not generate `IFSC` or `API_KEY`.
- [ ] Do not ask participants to invent IFSC or API-key credentials. Include those types only if separately reviewed synthetic fixtures are supplied.
- [ ] Give each participant only their own synthetic value set and the participant instructions.

## Merge rules

- [ ] Each of 3–4 participants supplied exactly seven positive (`real`/`tricky`) and three negative (`neg`) rows.
- [ ] Keep an anonymous author manifest separately (P01, P02, etc.); do not add author names to prompt rows.
- [ ] Merge rows into `gold_hidden.txt`, one row per line.
- [ ] Use explicit tags on every row: `lang:real`, `lang:tricky`, or `lang:neg`.
- [ ] Positive rows contain one or more exact `[[TYPE:value]]` markers; negative rows contain none.
- [ ] Run `python .\tools\validate_blind_gold.py <path-to-gold_hidden.txt> --participants 3` (or `4`).
- [ ] Keep the final file **outside the Git repository**, for example `C:\Users\vijay\Downloads\kavach-blind-evaluation\gold_hidden.txt`.
- [ ] Keep the language mix and its limitations explicit: language labels are used for report grouping; the detector is not passed the label, and Presidio currently uses English.

## Freeze and run once

- [ ] Run `tools\run_preflight.ps1` first and resolve any failures.
- [ ] Commit all detector changes and ensure `git status` is clean.
- [ ] Do not tune the detector after viewing or discussing the new holdout prompts.
- [ ] Run `tools\run_blind_eval.ps1 -GoldFile "C:\Users\vijay\Downloads\kavach-blind-evaluation\gold_hidden.txt" -Participants 3` once.
- [ ] Preserve the generated `blind_evaluation_locked` folder and its SHA-256 manifest beside the external gold file.
- [ ] Do not use this dataset for tuning. Any future detector changes require a new independently authored holdout set.

## Interpretation and output privacy

Call this an **independently authored synthetic holdout**, not a real-world study or statistically representative sample. Report the number of writers, prompts, language mix, entity mix, frozen Git commit and dataset hash. Report per-type precision/recall/F1 and negative-prompt false alarms. A small set still has wide uncertainty; do not claim production-wide accuracy.

The current `eval/run.py` error records contain system name, error kind, row ID, language/tag metadata, entity-type labels and character offsets. They do **not** contain raw prompt text or entity values. Keep the original synthetic gold file and archived outputs access-controlled nevertheless.
