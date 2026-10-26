# Evaluation (51 prompts, split=all)

Dataset mode: hand-written gold
Gold file: `eval/gold/gold.txt`

## kavach

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/20
False-positive entities on negative prompts: 0
Latency p50: 0.038 ms; p95: 0.076 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 1.00 | 1.00 | 1.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## kavach_block

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/20
False-positive entities on negative prompts: 0
Latency p50: 0.035 ms; p95: 0.066 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 1.00 | 1.00 | 1.00 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## regex_only

Negative-prompt false-alarm rate: 40.0%
Negative prompts flagged: 8/20
False-positive entities on negative prompts: 8
Latency p50: 0.021 ms; p95: 0.037 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.29 | 1.00 | 0.45 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 0.71 | 0.83 |
| PHONE | 1.00 | 0.50 | 0.67 |
| UPI_ID | 0.50 | 1.00 | 0.67 |
| MICRO_ALL | 0.66 | 0.88 | 0.75 |
| MICRO_SHARED | 0.67 | 0.83 | 0.74 |

## presidio

Negative-prompt false-alarm rate: 35.0%
Negative prompts flagged: 7/20
False-positive entities on negative prompts: 7
Latency p50: 6.518 ms; p95: 16.082 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.36 | 0.80 | 0.50 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.75 | 1.00 | 0.86 |
| UPI_ID | n/a | 0.00 | 0.00 |
| MICRO_ALL | 0.76 | 0.70 | 0.73 |
| MICRO_SHARED | 0.76 | 0.97 | 0.85 |

## presidio_custom

Negative-prompt false-alarm rate: 35.0%
Negative prompts flagged: 7/20
False-positive entities on negative prompts: 7
Latency p50: 6.458 ms; p95: 7.909 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.36 | 0.80 | 0.50 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.75 | 1.00 | 0.86 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.81 | 0.97 | 0.89 |
| MICRO_SHARED | 0.76 | 0.97 | 0.85 |

## presidio_norm

Negative-prompt false-alarm rate: 35.0%
Negative prompts flagged: 7/20
False-positive entities on negative prompts: 7
Latency p50: 6.092 ms; p95: 7.319 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.42 | 1.00 | 0.59 |
| CARD | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| GSTIN | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.75 | 1.00 | 0.86 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.82 | 1.00 | 0.90 |
| MICRO_SHARED | 0.76 | 1.00 | 0.87 |

# Results by gold tag

## real (27 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=0.78, R=0.86, F1=0.82
- **presidio:** MICRO_ALL P=0.96, R=0.69, F1=0.81
- **presidio_custom:** MICRO_ALL P=0.97, R=1.00, F1=0.99
- **presidio_norm:** MICRO_ALL P=0.97, R=1.00, F1=0.99

## tricky (4 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=0.80, R=1.00, F1=0.89
- **presidio:** MICRO_ALL P=0.75, R=0.75, F1=0.75
- **presidio_custom:** MICRO_ALL P=0.75, R=0.75, F1=0.75
- **presidio_norm:** MICRO_ALL P=0.80, R=1.00, F1=0.89

## neg (20 prompts)
- **kavach:** 0/20 prompts flagged (0.0%); 0 false-positive entities
- **kavach_block:** 0/20 prompts flagged (0.0%); 0 false-positive entities
- **regex_only:** 8/20 prompts flagged (40.0%); 8 false-positive entities
- **presidio:** 7/20 prompts flagged (35.0%); 7 false-positive entities
- **presidio_custom:** 7/20 prompts flagged (35.0%); 7 false-positive entities
- **presidio_norm:** 7/20 prompts flagged (35.0%); 7 false-positive entities

# Results by language

## en (24 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.65, R=0.93, F1=0.76
- presidio: MICRO_SHARED P=0.74, R=1.00, F1=0.85
- presidio_custom: MICRO_SHARED P=0.74, R=1.00, F1=0.85
- presidio_norm: MICRO_SHARED P=0.74, R=1.00, F1=0.85

## hi (7 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=1.00, F1=0.80
- presidio: MICRO_SHARED P=0.60, R=0.75, F1=0.67
- presidio_custom: MICRO_SHARED P=0.60, R=0.75, F1=0.67
- presidio_norm: MICRO_SHARED P=0.67, R=1.00, F1=0.80

## mr (7 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=1.00, F1=0.80
- presidio: MICRO_SHARED P=0.80, R=1.00, F1=0.89
- presidio_custom: MICRO_SHARED P=0.80, R=1.00, F1=0.89
- presidio_norm: MICRO_SHARED P=0.80, R=1.00, F1=0.89

## hinglish (11 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.67, R=0.40, F1=0.50
- presidio: MICRO_SHARED P=0.83, R=1.00, F1=0.91
- presidio_custom: MICRO_SHARED P=0.83, R=1.00, F1=0.91
- presidio_norm: MICRO_SHARED P=0.83, R=1.00, F1=0.91

## mr_en (1 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=1.00, R=0.50, F1=0.67
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00
