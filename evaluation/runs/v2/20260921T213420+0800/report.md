# SJ18-v2 paired prompt-preservation result

- Run: `20260921T213420+0800`
- Status: `complete`
- Dataset SHA-256: `7e42c7cfc3153b6c950242400f518bc62c06d89081bf55a722effdac890c9dd4`
- Requested model: `jev-latest`
- Returned models: `{"jev-1.13.0":24}`
- Requests: 24 attempted, 24 successful, no automatic retries

## Reference threshold 0.50

| split | n | TP | TN | FP | FN | balanced | Brier | AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 24 | 12 | 11 | 1 | 0 | 0.958 | 0.056 | 0.990 |
| calibration | 12 | 6 | 5 | 1 | 0 | 0.917 | 0.088 | 0.958 |
| validation | 12 | 6 | 6 | 0 | 0 | 1.000 | 0.024 | 1.000 |

## Calibration-selected threshold

Calibration selected `0.50` using maximum balanced accuracy; ties prefer the value closest to 0.50, then the lower value.

| split | TP | TN | FP | FN | balanced | Brier | AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| calibration | 6 | 5 | 1 | 0 | 0.917 | 0.088 | 0.958 |
| validation | 6 | 6 | 0 | 0 | 1.000 | 0.024 | 1.000 |

## Calibration threshold grid

| threshold | TP | TN | FP | FN | balanced | recall | specificity |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.05 | 6 | 2 | 4 | 0 | 0.667 | 1.000 | 0.333 |
| 0.10 | 6 | 3 | 3 | 0 | 0.750 | 1.000 | 0.500 |
| 0.15 | 6 | 3 | 3 | 0 | 0.750 | 1.000 | 0.500 |
| 0.20 | 6 | 4 | 2 | 0 | 0.833 | 1.000 | 0.667 |
| 0.25 | 6 | 4 | 2 | 0 | 0.833 | 1.000 | 0.667 |
| 0.30 | 6 | 4 | 2 | 0 | 0.833 | 1.000 | 0.667 |
| 0.35 | 6 | 4 | 2 | 0 | 0.833 | 1.000 | 0.667 |
| 0.40 | 6 | 4 | 2 | 0 | 0.833 | 1.000 | 0.667 |
| 0.45 | 6 | 5 | 1 | 0 | 0.917 | 1.000 | 0.833 |
| 0.50 | 6 | 5 | 1 | 0 | 0.917 | 1.000 | 0.833 |
| 0.55 | 6 | 5 | 1 | 0 | 0.917 | 1.000 | 0.833 |
| 0.60 | 6 | 5 | 1 | 0 | 0.917 | 1.000 | 0.833 |
| 0.65 | 5 | 5 | 1 | 1 | 0.833 | 0.833 | 0.833 |
| 0.70 | 5 | 5 | 1 | 1 | 0.833 | 0.833 | 0.833 |
| 0.75 | 5 | 5 | 1 | 1 | 0.833 | 0.833 | 0.833 |
| 0.80 | 4 | 6 | 0 | 2 | 0.833 | 0.667 | 1.000 |
| 0.85 | 4 | 6 | 0 | 2 | 0.833 | 0.667 | 1.000 |
| 0.90 | 3 | 6 | 0 | 3 | 0.750 | 0.500 | 1.000 |
| 0.95 | 0 | 6 | 0 | 6 | 0.500 | 0.000 | 1.000 |

## Language results at 0.50

| language | TP | TN | FP | FN | balanced | Brier | AUROC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| en | 6 | 5 | 1 | 0 | 0.917 | 0.084 | 0.958 |
| zh | 6 | 6 | 0 | 0 | 1.000 | 0.028 | 1.000 |

## Negative change types at 0.50

| change type | n | mean p(true) | max p(true) | false positives |
| --- | ---: | ---: | ---: | ---: |
| deletion | 2 | 0.590 | 0.760 | 1 |
| contradiction | 2 | 0.090 | 0.160 | 0 |
| count_or_relation | 2 | 0.035 | 0.040 | 0 |
| prohibition_violation | 2 | 0.065 | 0.090 | 0 |
| style_or_medium | 2 | 0.320 | 0.440 | 0 |
| attribute_scope | 2 | 0.035 | 0.040 | 0 |

## Pair ranking

Correctly ranked: 12/12; mean margin `0.676`, minimum margin `0.160`.

| pair | split | language | positive p | negative p | margin | ranked |
| --- | --- | --- | ---: | ---: | ---: | --- |
| c01 | calibration | en | 0.920 | 0.760 | 0.160 | true |
| c02 | calibration | zh | 0.910 | 0.160 | 0.750 | true |
| c03 | calibration | en | 0.760 | 0.040 | 0.720 | true |
| c04 | calibration | zh | 0.920 | 0.090 | 0.830 | true |
| c05 | calibration | en | 0.610 | 0.440 | 0.170 | true |
| c06 | calibration | zh | 0.890 | 0.040 | 0.850 | true |
| v07 | validation | zh | 0.920 | 0.420 | 0.500 | true |
| v08 | validation | en | 0.910 | 0.020 | 0.890 | true |
| v09 | validation | zh | 0.860 | 0.030 | 0.830 | true |
| v10 | validation | en | 0.930 | 0.040 | 0.890 | true |
| v11 | validation | zh | 0.840 | 0.200 | 0.640 | true |
| v12 | validation | en | 0.910 | 0.030 | 0.880 | true |

## Per-case probabilities

| id | split | language | change | expected | p(true) | model | elapsed ms |
| --- | --- | --- | --- | --- | ---: | --- | ---: |
| c01-positive | calibration | en | preserved | true | 0.920 | jev-1.13.0 | 860 |
| c01-negative | calibration | en | deletion | false | 0.760 | jev-1.13.0 | 835 |
| c02-positive | calibration | zh | preserved | true | 0.910 | jev-1.13.0 | 819 |
| c02-negative | calibration | zh | contradiction | false | 0.160 | jev-1.13.0 | 811 |
| c03-positive | calibration | en | preserved | true | 0.760 | jev-1.13.0 | 817 |
| c03-negative | calibration | en | count_or_relation | false | 0.040 | jev-1.13.0 | 863 |
| c04-positive | calibration | zh | preserved | true | 0.920 | jev-1.13.0 | 812 |
| c04-negative | calibration | zh | prohibition_violation | false | 0.090 | jev-1.13.0 | 843 |
| c05-positive | calibration | en | preserved | true | 0.610 | jev-1.13.0 | 827 |
| c05-negative | calibration | en | style_or_medium | false | 0.440 | jev-1.13.0 | 1405 |
| c06-positive | calibration | zh | preserved | true | 0.890 | jev-1.13.0 | 778 |
| c06-negative | calibration | zh | attribute_scope | false | 0.040 | jev-1.13.0 | 913 |
| v07-positive | validation | zh | preserved | true | 0.920 | jev-1.13.0 | 808 |
| v07-negative | validation | zh | deletion | false | 0.420 | jev-1.13.0 | 858 |
| v08-positive | validation | en | preserved | true | 0.910 | jev-1.13.0 | 905 |
| v08-negative | validation | en | contradiction | false | 0.020 | jev-1.13.0 | 857 |
| v09-positive | validation | zh | preserved | true | 0.860 | jev-1.13.0 | 837 |
| v09-negative | validation | zh | count_or_relation | false | 0.030 | jev-1.13.0 | 836 |
| v10-positive | validation | en | preserved | true | 0.930 | jev-1.13.0 | 903 |
| v10-negative | validation | en | prohibition_violation | false | 0.040 | jev-1.13.0 | 904 |
| v11-positive | validation | zh | preserved | true | 0.840 | jev-1.13.0 | 831 |
| v11-negative | validation | zh | style_or_medium | false | 0.200 | jev-1.13.0 | 798 |
| v12-positive | validation | en | preserved | true | 0.910 | jev-1.13.0 | 927 |
| v12-negative | validation | en | attribute_scope | false | 0.030 | jev-1.13.0 | 858 |

## Errors at reference threshold 0.50

- `c01-negative` (calibration, en, deletion): expected `false`, p(true) `0.760`.

## Limits

- These are authored diagnostic pairs, not sampled production prompts.
- Calibration and validation are separate but share the same authoring process.
- Results cover one run of one returned provider model version.
