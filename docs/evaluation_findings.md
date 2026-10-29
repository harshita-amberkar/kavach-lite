# KAVACH Lite — Evaluation Findings

Date: 26 October 2026

## 1. Evaluation setup

KAVACH was evaluated using a hand-written gold dataset containing
51 prompts: 27 real-tagged examples, 4 tricky examples, and
20 negative examples.

The results are preliminary and apply only to this dataset and
the local environment used for the benchmark.

## 2. KAVACH results

| Metric | Result |
|---|---:|
| Micro precision | 1.00 |
| Micro recall | 1.00 |
| Micro F1 | 1.00 |
| Negative prompts flagged | 0/20 |
| Negative-prompt false-alarm rate | 0.0% |
| Median latency (p50) | 0.038 ms |
| 95th-percentile latency (p95) | 0.070 ms |

The benchmark reported precision, recall, and F1 of 1.00 for
the listed Aadhaar, card, email, GSTIN, PAN, phone, and UPI
categories.

## 3. Comparison results

| System | Micro F1 | Negative false-alarm rate | p50 latency |
|---|---:|---:|---:|
| KAVACH | 1.00 | 0.0% | 0.038 ms |
| KAVACH block mode | 1.00 | 0.0% | 0.037 ms |
| Regex only | 0.75 | 40.0% | 0.021 ms |
| Presidio | 0.73 | 35.0% | 6.613 ms |
| Presidio custom | 0.89 | 35.0% | 6.332 ms |
| Presidio normalized | 0.90 | 35.0% | 6.042 ms |

These measurements describe this benchmark only. They do not
establish production-wide superiority over the comparison systems.

## 4. Error audit

The evaluation error file contained 63 records:

| System | FP | FN | Total |
|---|---:|---:|---:|
| Regex only | 18 | 5 | 23 |
| Presidio | 9 | 12 | 21 |
| Presidio custom | 9 | 1 | 10 |
| Presidio normalized | 9 | 0 | 9 |
| Total | 45 | 18 | 63 |

Across all comparison systems, 29 error records were false
positives on negative examples. Errors also occurred on real-tagged
and tricky examples.

No KAVACH error records appeared in this error file for this run.
The result should be validated with larger, independently prepared
datasets before stronger accuracy claims are made.

## 5. Language coverage

The benchmark included English, Hindi, Marathi, Hinglish, and
Marathi-English examples. KAVACH reported MICRO_SHARED precision,
recall, and F1 of 1.00 in each reported language group.

Some language groups were very small. For example, the
Marathi-English category contained one prompt. These results
therefore indicate initial coverage, not robust multilingual
generalization.

## 6. Limitations

- The dataset contains only 51 hand-written prompts.
- The examples are not an independently collected production dataset.
- Results may be affected by which identifiers and contexts appear
  in the gold prompts.
- Latency measurements are local benchmark measurements, not
  end-to-end user-perceived latency.
- The error records do not currently provide enough populated
  gold-label metadata to classify every error by entity type.
- More varied negative, ambiguous, multilingual, and unseen
  examples are required.

## 7. Conclusion

On the current hand-written benchmark, KAVACH achieved a micro-F1
of 1.00 and did not flag any of the 20 negative prompts.
The comparison systems recorded more errors and higher negative
false-alarm rates in this run.

The next evaluation step is to expand the dataset, improve the
error report's expected-versus-predicted metadata, and repeat the
benchmark without tuning rules solely to the existing prompts.

## 8. Holdout regression evaluation

A separate hand-written regression dataset contained 43 prompts:
17 real-tagged examples, 6 tricky examples, and 20 negative examples.

Before targeted fixes, KAVACH flagged two negative prompts:
one numeric batch/timestamp example as Aadhaar and one explicit
redacted credential placeholder as an API key.

After adding generic context handling for batch-like numbers and
filtering obvious credential placeholders, the regression run reported:

| Metric | Result |
|---|---:|
| Micro precision | 1.00 |
| Micro recall | 1.00 |
| Micro F1 | 1.00 |
| Negative prompts flagged | 0/20 |
| Negative false-alarm rate | 0.0% |
| Median latency (p50) | 0.031 ms |
| 95th-percentile latency (p95) | 0.052 ms |

This dataset was used to identify and guide the fixes. It must therefore
be treated as a regression set, not as an independent unseen test set.
The post-fix scores measure the current behavior on these examples but
do not prove perfect real-world accuracy.

The original 51-prompt benchmark was rerun after the fixes. Its reported
micro-precision, micro-recall, and micro-F1 remained 1.00, with no
negative prompts flagged among its 20 negative examples.

Further evaluation should use additional examples that were not used
to select or tune the detector rules.

## 9. Locked synthetic evaluation set (v1)

The hand-written synthetic dataset at `eval/gold/gold_locked_v1.txt`
contains 51 prompts: 12 tagged `real`, 12 tagged `tricky`, and 27
tagged `neg`. It covers EMAIL, PHONE, PAN, IFSC, UPI_ID, and API_KEY.

Results from the recorded run:

| Metric | KAVACH | KAVACH block mode |
|---|---:|---:|
| Micro-F1 | 1.00 | 1.00 |
| Negative prompts flagged | 0/27 | 0/27 |
| Negative false-alarm rate | 0.0% | 0.0% |
| Latency p50 | 0.023 ms | 0.023 ms |
| Latency p95 | 0.035 ms | 0.032 ms |

All six represented entity types reported precision, recall, and F1 of
1.00 for both KAVACH modes on this run. Regex-only flagged 3/27 negative
prompts; Presidio, Presidio custom, and Presidio normalized each flagged
1/27.

These are measurements on a small, handcrafted synthetic dataset.
They do not establish production-wide accuracy or guarantee performance
on unseen real-world inputs. Freeze this version for future comparisons
rather than changing detector rules to optimize its score. Use a new,
separately designed dataset for subsequent detector tuning.


## 10. Latest evaluation rerun (29 October 2026)

The gold set and the separate regression dataset were rerun after the
autonomous-agent failure-handling tests were added. No detector rules
were changed for these runs.

### Gold set: 51 prompts

| System | Micro precision | Micro recall | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|---:|---:|
| KAVACH | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.055 ms | 0.146 ms |
| KAVACH block mode | 1.00 | 1.00 | 1.00 | 0/20 (0%) | 0.052 ms | 0.097 ms |
| Regex only | 0.66 | 0.88 | 0.75 | 8/20 (40%) | 0.030 ms | 0.055 ms |
| Presidio | 0.76 | 0.70 | 0.73 | 7/20 (35%) | 9.323 ms | 27.640 ms |
| Presidio custom | 0.81 | 0.97 | 0.89 | 7/20 (35%) | 7.986 ms | 11.041 ms |
| Presidio normalized | 0.82 | 1.00 | 0.90 | 7/20 (35%) | 7.976 ms | 10.086 ms |

### Regression set: 43 prompts

| System | Micro F1 | Negative prompts flagged | p50 latency | p95 latency |
|---|---:|---:|---:|---:|
| KAVACH | 1.00 | 0/20 (0%) | 0.039 ms | 0.067 ms |
| KAVACH block mode | 1.00 | 0/20 (0%) | 0.037 ms | 0.062 ms |
| Regex only | 0.65 | 5/20 (25%) | 0.029 ms | 0.043 ms |
| Presidio | 0.77 | 1/20 (5%) | 7.368 ms | 12.066 ms |
| Presidio custom | 0.86 | 1/20 (5%) | 7.381 ms | 9.323 ms |
| Presidio normalized | 0.86 | 1/20 (5%) | 7.721 ms | 11.032 ms |

The separate synthetic benchmark run reported zero false alarms on
210 clean sentences. This count is distinct from the 20 negative
prompts in each hand-written dataset.

A normalized prompt audit found no duplicates within either dataset
and no exact normalized overlap between the gold set and regression
set. The regression set was previously used to identify and guide
detector fixes, so these results are regression evidence rather than
an untouched blind evaluation. The perfect displayed scores remain
limited to the tested examples and do not establish real-world
detection accuracy or generalization.
