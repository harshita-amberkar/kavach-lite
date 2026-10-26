# Evaluation (51 prompts, split=all)

Dataset mode: hand-written gold
Gold file: `eval/gold/gold_locked_v1.txt`

## kavach

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/27
False-positive entities on negative prompts: 0
Latency p50: 0.023 ms; p95: 0.035 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| API_KEY | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## kavach_block

Negative-prompt false-alarm rate: 0.0%
Negative prompts flagged: 0/27
False-positive entities on negative prompts: 0
Latency p50: 0.023 ms; p95: 0.032 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| API_KEY | 1.00 | 1.00 | 1.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | 1.00 | 1.00 | 1.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 1.00 | 1.00 | 1.00 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 1.00 | 1.00 | 1.00 |
| MICRO_SHARED | 1.00 | 1.00 | 1.00 |

## regex_only

Negative-prompt false-alarm rate: 11.1%
Negative prompts flagged: 3/27
False-positive entities on negative prompts: 3
Latency p50: 0.016 ms; p95: 0.028 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| AADHAAR | 0.00 | n/a | n/a |
| API_KEY | n/a | 0.00 | 0.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.80 | 1.00 | 0.89 |
| UPI_ID | 0.50 | 1.00 | 0.67 |
| MICRO_ALL | 0.70 | 0.67 | 0.68 |
| MICRO_SHARED | 0.80 | 1.00 | 0.89 |

## presidio

Negative-prompt false-alarm rate: 3.7%
Negative prompts flagged: 1/27
False-positive entities on negative prompts: 1
Latency p50: 5.013 ms; p95: 6.337 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| API_KEY | n/a | 0.00 | 0.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.80 | 1.00 | 0.89 |
| UPI_ID | n/a | 0.00 | 0.00 |
| MICRO_ALL | 0.92 | 0.50 | 0.65 |
| MICRO_SHARED | 0.92 | 1.00 | 0.96 |

## presidio_custom

Negative-prompt false-alarm rate: 3.7%
Negative prompts flagged: 1/27
False-positive entities on negative prompts: 1
Latency p50: 4.999 ms; p95: 6.244 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| API_KEY | n/a | 0.00 | 0.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.80 | 1.00 | 0.89 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.94 | 0.67 | 0.78 |
| MICRO_SHARED | 0.92 | 1.00 | 0.96 |

## presidio_norm

Negative-prompt false-alarm rate: 3.7%
Negative prompts flagged: 1/27
False-positive entities on negative prompts: 1
Latency p50: 5.155 ms; p95: 5.626 ms

| Type | Precision | Recall | F1 |
|---|---:|---:|---:|
| API_KEY | n/a | 0.00 | 0.00 |
| EMAIL | 1.00 | 1.00 | 1.00 |
| IFSC | n/a | 0.00 | 0.00 |
| PAN | 1.00 | 1.00 | 1.00 |
| PHONE | 0.80 | 1.00 | 0.89 |
| UPI_ID | 1.00 | 1.00 | 1.00 |
| MICRO_ALL | 0.94 | 0.67 | 0.78 |
| MICRO_SHARED | 0.92 | 1.00 | 0.96 |

# Results by gold tag

## real (12 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=0.80, R=0.67, F1=0.73
- **presidio:** MICRO_ALL P=1.00, R=0.50, F1=0.67
- **presidio_custom:** MICRO_ALL P=1.00, R=0.67, F1=0.80
- **presidio_norm:** MICRO_ALL P=1.00, R=0.67, F1=0.80

## tricky (12 prompts)
- **kavach:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **kavach_block:** MICRO_ALL P=1.00, R=1.00, F1=1.00
- **regex_only:** MICRO_ALL P=0.80, R=0.67, F1=0.73
- **presidio:** MICRO_ALL P=1.00, R=0.50, F1=0.67
- **presidio_custom:** MICRO_ALL P=1.00, R=0.67, F1=0.80
- **presidio_norm:** MICRO_ALL P=1.00, R=0.67, F1=0.80

## neg (27 prompts)
- **kavach:** 0/27 prompts flagged (0.0%); 0 false-positive entities
- **kavach_block:** 0/27 prompts flagged (0.0%); 0 false-positive entities
- **regex_only:** 3/27 prompts flagged (11.1%); 3 false-positive entities
- **presidio:** 1/27 prompts flagged (3.7%); 1 false-positive entities
- **presidio_custom:** 1/27 prompts flagged (3.7%); 1 false-positive entities
- **presidio_norm:** 1/27 prompts flagged (3.7%); 1 false-positive entities

# Results by language

## en (28 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=0.50, R=1.00, F1=0.67
- presidio: MICRO_SHARED P=0.75, R=1.00, F1=0.86
- presidio_custom: MICRO_SHARED P=0.75, R=1.00, F1=0.86
- presidio_norm: MICRO_SHARED P=0.75, R=1.00, F1=0.86

## hi (8 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00

## mr (8 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00

## hinglish (7 prompts)
- kavach: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- kavach_block: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- regex_only: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_custom: MICRO_SHARED P=1.00, R=1.00, F1=1.00
- presidio_norm: MICRO_SHARED P=1.00, R=1.00, F1=1.00
