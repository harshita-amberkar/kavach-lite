# Independent synthetic holdout

## Scope and status

This is a new, project-authored synthetic holdout, separate from `eval/gold/`,
the `eval.gen` development generator, `eval/global_benchmark.py`, and the
previous `gold_holdout.txt`. It contains no human-submitted examples and is
not a human evaluation. The abandoned participant-collection workflow was
not used. The dataset was frozen and evaluated without using its results to
change detector rules.

The set has 60 unique prompts: 20 positive, 20 tricky positive and 20
negative. It covers 20 entity types, with two positive examples per type:

`AADHAAR`, `API_KEY`, `CARD`, `CONFIDENTIAL_BUSINESS`, `CRYPTO`, `EMAIL`,
`GSTIN`, `IBAN`, `IFSC`, `IP_ADDRESS`, `LOCATION`, `MAC_ADDRESS`,
`MEDICAL_INFO`, `MEDICAL_LICENSE`, `NRP`, `PAN`, `PERSON`, `PHONE`,
`UPI_ID`, and `US_SSN`.

All identifier-shaped values are generated as fictional test fixtures.
Checksum-valid Aadhaar, card, GSTIN, IBAN and crypto fixtures are produced
from a fixed PRNG seed; contact values and other identifiers are also
synthetic. Negative rows include benign prose and identifier-like lookalikes.
Rows use English text with occasional code/config phrasing; the set does not
test multilingual detection.

## Reproduction and freeze

From the repository root, with the project virtual environment active:

```powershell
.\.venv\Scripts\python.exe -m eval.independent_holdout.generate
.\.venv\Scripts\python.exe -m eval.independent_holdout.run
```

The generator uses seed `20261103`, its own templates and fixed row order. It
does not import or read existing gold or development examples. It writes
`eval/independent_holdout/dataset.jsonl` and a SHA-256 sidecar. The evaluator
checks the sidecar and a separately pinned SHA-256 in
`eval/independent_holdout/run.py`; both must match. Regeneration updates the
editable sidecar only and does not approve a changed dataset. A new approved
hash must be changed explicitly in runner configuration after review. The
approved dataset SHA-256 is:

`5d4e4ae163a2197e9e6755cf5075cc169bacb3d0e1e53deaf63f10ac2686b480`

## Evaluation method

The runner reuses the framework's type-and-span overlap matcher and system
registry but writes corrected results to
`results/independent_synthetic_holdout_steady_state/`, leaving the previous
holdout report and existing benchmark reports untouched. Systems evaluated were `kavach`,
`kavach_global`, `kavach_block`, `regex_only`, `presidio`,
`presidio_custom`, and `presidio_norm`.

Precision, recall and F1 are micro entity metrics. A prediction is a match
only when its type is exact and it overlaps at least half of the gold span.
Negative-prompt false-positive rate (FPR) is the share of negative prompts
with one or more predictions. Latency is measured per prompt after every
detector receives the same synthetic warm-up prompt, and steady-state p50/p95
are reported separately. Shared registry initialization time is recorded
before warm-up. Per-system cold-start latency is omitted because Presidio
models initialize eagerly while KAVACH Global initializes lazily, making
per-system cold measurements non-comparable. Error records contain row IDs, tags, entity labels
and offsets only; they do not copy prompt text or values.

## Results

| System | Precision | Recall | F1 | Negative FPR | Steady-state p50 ms | Steady-state p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| KAVACH | 0.95 | 0.45 | 0.61 | 5.0% | 0.036 | 0.058 |
| KAVACH Global | 0.86 | 0.95 | 0.90 | 20.0% | 8.275 | 17.360 |
| KAVACH block | 0.95 | 0.45 | 0.61 | 5.0% | 0.066 | 0.178 |
| Regex only | 0.74 | 0.35 | 0.47 | 15.0% | 0.032 | 0.043 |
| Presidio | 0.80 | 0.20 | 0.32 | 5.0% | 9.850 | 13.305 |
| Presidio custom | 0.86 | 0.30 | 0.44 | 5.0% | 12.222 | 16.960 |
| Presidio normalized | 0.86 | 0.30 | 0.44 | 5.0% | 9.244 | 13.897 |

The current run took 5509.994 ms to initialize the shared system registry;
that setup duration is not included in the steady-state per-prompt figures.

The historical `results/independent_synthetic_holdout/report.md` and its
JSON/error files are preserved. The corrected report in
`results/independent_synthetic_holdout_steady_state/` supersedes that earlier
run for latency methodology and the current rerun; it does not overwrite the
historical artifact. Aggregate results reproduced in the prior rerun, but one
overlapping negative prediction changed attribution from US_SSN to US_ITIN.
Exact per-entity reproducibility is not claimed. Consult the corrected report
for current metrics.

KAVACH Global detected 38 of 40 gold entities (95% recall) but flagged 4 of
20 negative prompts (20% FPR). Its two false negatives were one tricky
confidential-business example and one tricky NRP example. KAVACH detected
18 of 40 gold entities (45% recall), with 1 of 20 negative prompts flagged;
it did not detect the global-only entity classes in this set. Full per-entity
metrics and error counts by tag/entity are in the generated report. Review
the metadata-only `errors.jsonl` alongside the dataset when diagnosing a row.

The native detector's 22 false negatives were the two examples for each of
11 global-only types. Its one false alarm was a PAN-shaped inventory SKU.
KAVACH Global's six unmatched predictions included four negative-prompt
alarms (US_SSN, PAN, LOCATION and IP_ADDRESS) and two LOCATION predictions
on positive prompts. Its remaining misses were the tricky confidential-
business and NRP examples.

## Limits

This small, fixed, project-authored synthetic set has only two positive gold
examples per entity type and 20 negatives, so negative FPR changes in
five-percentage-point steps. It is a reproducible distribution shift, not an
independent sample of real user data. It does not
establish production accuracy, real-world prevalence, multilingual ability,
or human evaluation. The global detector's higher recall came with a higher
false-positive rate and substantially higher latency on this run. Results
are specific to this dataset and environment.
