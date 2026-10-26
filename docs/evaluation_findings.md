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
| Median latency (p50) | 0.041 ms |
| 95th-percentile latency (p95) | 0.078 ms |

The benchmark reported precision, recall, and F1 of 1.00 for
the listed Aadhaar, card, email, GSTIN, PAN, phone, and UPI
categories.

## 3. Comparison results

| System | Micro F1 | Negative false-alarm rate | p50 latency |
|---|---:|---:|---:|
| KAVACH | 1.00 | 0.0% | 0.041 ms |
| KAVACH block mode | 1.00 | 0.0% | 0.039 ms |
| Regex only | 0.75 | 40.0% | 0.023 ms |
| Presidio | 0.73 | 35.0% | 7.448 ms |
| Presidio custom | 0.89 | 35.0% | 6.482 ms |
| Presidio normalized | 0.90 | 35.0% | 6.486 ms |

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
