# Independent synthetic holdout evaluation

- Prompts: 60 (20 positive, 20 tricky positive, 20 negative)
- SHA-256: `5d4e4ae163a2197e9e6755cf5075cc169bacb3d0e1e53deaf63f10ac2686b480`
- Scope: synthetic fixtures only; this is not human evaluation or a production accuracy claim.
- Entity types: AADHAAR (2), API_KEY (2), CARD (2), CONFIDENTIAL_BUSINESS (2), CRYPTO (2), EMAIL (2), GSTIN (2), IBAN (2), IFSC (2), IP_ADDRESS (2), LOCATION (2), MAC_ADDRESS (2), MEDICAL_INFO (2), MEDICAL_LICENSE (2), NRP (2), PAN (2), PERSON (2), PHONE (2), UPI_ID (2), US_SSN (2)
- Matching: exact entity type and at least 50% character-span overlap, using `eval.run.evaluate`.
- False-positive rate: negative prompts with one or more predicted entities / all negative prompts.
- Latency: per-detector wall-clock milliseconds per prompt; p50 and p95. First-run model initialization is included when it occurs.

## Overall results

| System | Precision | Recall | F1 | Negative prompt FPR | False positives on negatives | Latency p50 ms | Latency p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| kavach | 0.95 | 0.45 | 0.61 | 5.0% | 1 | 0.196 | 0.354 |
| kavach_global | 0.86 | 0.95 | 0.90 | 20.0% | 4 | 30.782 | 66.030 |
| kavach_block | 0.95 | 0.45 | 0.61 | 5.0% | 1 | 0.196 | 0.321 |
| regex_only | 0.74 | 0.35 | 0.47 | 15.0% | 3 | 0.114 | 0.255 |
| presidio | 0.80 | 0.20 | 0.32 | 5.0% | 1 | 30.152 | 79.278 |
| presidio_custom | 0.86 | 0.30 | 0.44 | 5.0% | 1 | 29.897 | 39.725 |
| presidio_norm | 0.86 | 0.30 | 0.44 | 5.0% | 1 | 30.951 | 39.513 |

## Per-entity results

### kavach

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | 1.00 | 1.00 | 1.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | 1.00 | 1.00 | 1.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | 1.00 | 1.00 | 1.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.67 | 1.00 | 0.80 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 1.00 | 1.00 | 1.00 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

### kavach_global

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | 1.00 | 1.00 | 1.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | 1.00 | 0.50 | 0.67 |
| CRYPTO | 2 | 1.00 | 1.00 | 1.00 |
| EMAIL | 2 | 1.00 | 1.00 | 1.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | 1.00 | 1.00 | 1.00 |
| IFSC | 2 | 1.00 | 1.00 | 1.00 |
| IP_ADDRESS | 2 | 0.67 | 1.00 | 0.80 |
| LOCATION | 2 | 0.40 | 1.00 | 0.57 |
| MAC_ADDRESS | 2 | 1.00 | 1.00 | 1.00 |
| MEDICAL_INFO | 2 | 1.00 | 1.00 | 1.00 |
| MEDICAL_LICENSE | 2 | 1.00 | 1.00 | 1.00 |
| NRP | 2 | 1.00 | 0.50 | 0.67 |
| PAN | 2 | 0.67 | 1.00 | 0.80 |
| PERSON | 2 | 1.00 | 1.00 | 1.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 1.00 | 1.00 | 1.00 |
| US_SSN | 2 | 0.67 | 1.00 | 0.80 |

### kavach_block

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | 1.00 | 1.00 | 1.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | 1.00 | 1.00 | 1.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | 1.00 | 1.00 | 1.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.67 | 1.00 | 0.80 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 1.00 | 1.00 | 1.00 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

### regex_only

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 0.50 | 1.00 | 0.67 |
| API_KEY | 2 | n/a | 0.00 | 0.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | 1.00 | 1.00 | 1.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | n/a | 0.00 | 0.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.67 | 1.00 | 0.80 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 0.50 | 1.00 | 0.67 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

### presidio

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | n/a | 0.00 | 0.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | n/a | 0.00 | 0.00 |
| GSTIN | 2 | n/a | 0.00 | 0.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | n/a | 0.00 | 0.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.50 | 1.00 | 0.67 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | n/a | 0.00 | 0.00 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

### presidio_custom

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | n/a | 0.00 | 0.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | n/a | 0.00 | 0.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | n/a | 0.00 | 0.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.50 | 1.00 | 0.67 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 1.00 | 1.00 | 1.00 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

### presidio_norm

| Entity | Gold count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| AADHAAR | 2 | 1.00 | 1.00 | 1.00 |
| API_KEY | 2 | n/a | 0.00 | 0.00 |
| CARD | 2 | 1.00 | 1.00 | 1.00 |
| CONFIDENTIAL_BUSINESS | 2 | n/a | 0.00 | 0.00 |
| CRYPTO | 2 | n/a | 0.00 | 0.00 |
| EMAIL | 2 | n/a | 0.00 | 0.00 |
| GSTIN | 2 | 1.00 | 1.00 | 1.00 |
| IBAN | 2 | n/a | 0.00 | 0.00 |
| IFSC | 2 | n/a | 0.00 | 0.00 |
| IP_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| LOCATION | 2 | n/a | 0.00 | 0.00 |
| MAC_ADDRESS | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_INFO | 2 | n/a | 0.00 | 0.00 |
| MEDICAL_LICENSE | 2 | n/a | 0.00 | 0.00 |
| NRP | 2 | n/a | 0.00 | 0.00 |
| PAN | 2 | 0.50 | 1.00 | 0.67 |
| PERSON | 2 | n/a | 0.00 | 0.00 |
| PHONE | 2 | 1.00 | 1.00 | 1.00 |
| UPI_ID | 2 | 1.00 | 1.00 | 1.00 |
| US_SSN | 2 | n/a | 0.00 | 0.00 |

## Error analysis

### kavach

- Errors: 23 total; 22 false negatives and 1 unmatched predictions.
- By tag: `{"neg": {"FP": 1}, "real": {"FN": 11}, "tricky": {"FN": 11}}`
- By entity: `{"CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "IBAN": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 1}, "PERSON": {"FN": 2}, "US_SSN": {"FN": 2}}`

### kavach_global

- Errors: 8 total; 2 false negatives and 6 unmatched predictions.
- By tag: `{"neg": {"FP": 4}, "real": {"FP": 2}, "tricky": {"FN": 2}}`
- By entity: `{"CONFIDENTIAL_BUSINESS": {"FN": 1}, "IP_ADDRESS": {"FP": 1}, "LOCATION": {"FP": 3}, "NRP": {"FN": 1}, "PAN": {"FP": 1}, "US_SSN": {"FP": 1}}`

### kavach_block

- Errors: 23 total; 22 false negatives and 1 unmatched predictions.
- By tag: `{"neg": {"FP": 1}, "real": {"FN": 11}, "tricky": {"FN": 11}}`
- By entity: `{"CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "IBAN": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 1}, "PERSON": {"FN": 2}, "US_SSN": {"FN": 2}}`

### regex_only

- Errors: 31 total; 26 false negatives and 5 unmatched predictions.
- By tag: `{"neg": {"FP": 3}, "real": {"FN": 13, "FP": 1}, "tricky": {"FN": 13, "FP": 1}}`
- By entity: `{"AADHAAR": {"FP": 2}, "API_KEY": {"FN": 2}, "CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "IBAN": {"FN": 2}, "IFSC": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 1}, "PERSON": {"FN": 2}, "UPI_ID": {"FP": 2}, "US_SSN": {"FN": 2}}`

### presidio

- Errors: 34 total; 32 false negatives and 2 unmatched predictions.
- By tag: `{"neg": {"FP": 1}, "real": {"FN": 16}, "tricky": {"FN": 16, "FP": 1}}`
- By entity: `{"API_KEY": {"FN": 2}, "CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "EMAIL": {"FN": 2}, "GSTIN": {"FN": 2}, "IBAN": {"FN": 2}, "IFSC": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 2}, "PERSON": {"FN": 2}, "UPI_ID": {"FN": 2}, "US_SSN": {"FN": 2}}`

### presidio_custom

- Errors: 30 total; 28 false negatives and 2 unmatched predictions.
- By tag: `{"neg": {"FP": 1}, "real": {"FN": 14}, "tricky": {"FN": 14, "FP": 1}}`
- By entity: `{"API_KEY": {"FN": 2}, "CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "EMAIL": {"FN": 2}, "IBAN": {"FN": 2}, "IFSC": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 2}, "PERSON": {"FN": 2}, "US_SSN": {"FN": 2}}`

### presidio_norm

- Errors: 30 total; 28 false negatives and 2 unmatched predictions.
- By tag: `{"neg": {"FP": 1}, "real": {"FN": 14}, "tricky": {"FN": 14, "FP": 1}}`
- By entity: `{"API_KEY": {"FN": 2}, "CONFIDENTIAL_BUSINESS": {"FN": 2}, "CRYPTO": {"FN": 2}, "EMAIL": {"FN": 2}, "IBAN": {"FN": 2}, "IFSC": {"FN": 2}, "IP_ADDRESS": {"FN": 2}, "LOCATION": {"FN": 2}, "MAC_ADDRESS": {"FN": 2}, "MEDICAL_INFO": {"FN": 2}, "MEDICAL_LICENSE": {"FN": 2}, "NRP": {"FN": 2}, "PAN": {"FP": 2}, "PERSON": {"FN": 2}, "US_SSN": {"FN": 2}}`

## Interpretation limits

The examples are deterministic, hand-authored synthetic templates with generated identifier-shaped values. The same generation script reproduces the checked-in JSONL and checksum. This provides a reproducible distribution shift from the existing benchmark, but it is still authored by the project and does not represent independent human-authored samples, real-world prevalence, or multilingual performance.
