# Evaluation (43 prompts, split=all)

Dataset mode: hand-written gold
Gold file: `eval/gold/gold_holdout.txt`

## kavach

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/20
False-positive entities on negative prompts: 0
Latency p50: 0.031 ms; p95: 0.052 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 1.00 | 1.00 | 1.00 |
| API_KEY | 1.00 | 1.00 | 1.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## kavach_block

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/20
False-positive entities on negative prompts: 0
Latency p50: 0.030 ms; p95: 0.040 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 1.00 | 1.00 | 1.00 |
| API_KEY | 1.00 | 1.00 | 1.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## regex_only

Negative-prompt false-alarm rate: 25.0%
Negative prompts flagged: 5/20
False-positive entities on negative prompts: 5
Latency p50: 0.020 ms; p95: 0.026 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.43 | 1.00 | 0.60 |
| API_KEY | n/a | 0.00 | 0.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 0.75 | 1.00 | 0.86 |
| PHONE | n/a | 0.00 | 0.00 |
| UPI_ID | 0.50 | 1.00 | 0.67 |
| MICRO_ALL | 0.65 | 0.65 | 0.65 |
| MICRO_SHARED | 0.71 | 0.80 | 0.75 |

## presidio

Negative-prompt false-alarm rate: 5.0%
Negative prompts flagged: 1/20
False-positive entities on negative prompts: 1
Latency p50: 6.283 ms; p95: 9.136 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.75 | 1.00 | 0.86 |
| API_KEY | n/a | 0.00 | 0.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | n/a | 0.00 | 0.00 |
| MICRO_ALL | 0.94 | 0.65 | 0.77 |
| MICRO_SHARED | 0.94 | 1.00 | 0.97 |

## presidio_custom

Negative-prompt false-alarm rate: 5.0%
Negative prompts flagged: 1/20
False-positive entities on negative prompts: 1
Latency p50: 6.471 ms; p95: 8.912 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.75 | 1.00 | 0.86 |
| API_KEY | n/a | 0.00 | 0.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.95 | 0.78 | 0.86 |
| MICRO_SHARED | 0.94 | 1.00 | 0.97 |

## presidio_norm

Negative-prompt false-alarm rate: 5.0%
Negative prompts flagged: 1/20
False-positive entities on negative prompts: 1
Latency p50: 6.362 ms; p95: 7.756 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.75 | 1.00 | 0.86 |
| API_KEY | n/a | 0.00 | 0.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.95 | 0.78 | 0.86 |
| MICRO_SHARED | 0.94 | 1.00 | 0.97 |

# Results by gold tag

## real (17 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=0.77, R=0.59, F1=0.67
- **presidio:** MICRO_ALL P=1.00, R=0.65, F1=0.79
- **presidio_custom:** MICRO_ALL P=1.00, R=0.76, F1=0.87
- **presidio_norm:** MICRO_ALL P=1.00, R=0.76, F1=0.87

## tricky (6 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=1.00, R=0.83, F1=0.91
- **presidio:** MICRO_ALL P=1.00, R=0.67, F1=0.80
- **presidio_custom:** MICRO_ALL P=1.00, R=0.83, F1=0.91
- **presidio_norm:** MICRO_ALL P=1.00, R=0.83, F1=0.91

## neg (20 prompts)
- **kavach:** 0/20 prompts flagged (0.0%); 0 false-positive entities
- **kavach_block:** 0/20 prompts flagged (0.0%); 0 false-positive entities
- **regex_only:** 5/20 prompts flagged (25.0%); 5 false-positive entities
- **presidio:** 1/20 prompts flagged (5.0%); 1 false-positive entities
- **presidio_custom:** 1/20 prompts flagged (5.0%); 1 false-positive entities
- **presidio_norm:** 1/20 prompts flagged (5.0%); 1 false-positive entities

# Results by language

## en (18 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=0.80, F1=0.73
- presidio: MICRO_SHARED P=0.83, R=1.00, F1=0.91
- presidio_custom: MICRO_SHARED P=0.83, R=1.00, F1=0.91
- presidio_norm: MICRO_SHARED P=0.83, R=1.00, F1=0.91

## hi (12 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.80, R=0.80, F1=0.80
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00

## mr (7 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=0.67, F1=0.67
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00

## hinglish (5 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=1.00, F1=0.80
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00

## mr_en (1 prompts)
- kavach: MICRO_SHARED P=n/a, R=n/a, F1=n/a
- kavach_block: MICRO_SHARED P=n/a, R=n/a, F1=n/a
- regex_only: MICRO_SHARED P=n/a, R=n/a, F1=n/a
- presidio: MICRO_SHARED P=n/a, R=n/a, F1=n/a
- presidio_custom: MICRO_SHARED P=n/a, R=n/a, F1=n/a
- presidio_norm: MICRO_SHARED P=n/a, R=n/a, F1=n/a
