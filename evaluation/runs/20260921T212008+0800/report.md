# SJ18 prompt-preservation result

- Run: `20260921T212008+0800`
- Status: `complete`
- Dataset SHA-256: `2d10c8008c7c42b155ae60d04908ebef56b3712868cfa30bd56fe1221ad98009`
- Requested model: `jev-latest`
- Returned models: `{"jev-1.13.0":18}`
- Requests: 18 attempted, 18 successful, no automatic retries
- Brier score: 0.001

## Thresholds

| threshold | TP | TN | FP | FN | accuracy | balanced | precision | recall | specificity | F1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.50 | 3 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.60 | 3 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.70 | 3 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.80 | 3 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.90 | 3 | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The fixed primary threshold is 0.50. The best observed threshold is descriptive only and was not selected on a separate validation set.

## Categories at threshold 0.50

| category | n | accuracy | mean p(true) | range |
| --- | ---: | ---: | ---: | --- |
| preserved | 3 | 1.000 | 0.960 | 0.960–0.960 |
| deletion | 3 | 1.000 | 0.063 | 0.030–0.100 |
| contradiction | 3 | 1.000 | 0.013 | 0.010–0.020 |
| count_change | 3 | 1.000 | 0.010 | 0.010–0.010 |
| prohibition_dropped | 3 | 1.000 | 0.023 | 0.010–0.040 |
| style_change | 3 | 1.000 | 0.020 | 0.010–0.040 |

## Per-case probabilities

| id | category | expected | p(true) | predicted@0.50 | model | elapsed ms |
| --- | --- | --- | ---: | --- | --- | ---: |
| preserved-01 | preserved | true | 0.960 | true | jev-1.13.0 | 1195 |
| preserved-02 | preserved | true | 0.960 | true | jev-1.13.0 | 811 |
| preserved-03 | preserved | true | 0.960 | true | jev-1.13.0 | 840 |
| deletion-01 | deletion | false | 0.030 | false | jev-1.13.0 | 861 |
| deletion-02 | deletion | false | 0.100 | false | jev-1.13.0 | 840 |
| deletion-03 | deletion | false | 0.060 | false | jev-1.13.0 | 847 |
| contradiction-01 | contradiction | false | 0.020 | false | jev-1.13.0 | 827 |
| contradiction-02 | contradiction | false | 0.010 | false | jev-1.13.0 | 825 |
| contradiction-03 | contradiction | false | 0.010 | false | jev-1.13.0 | 809 |
| count-change-01 | count_change | false | 0.010 | false | jev-1.13.0 | 828 |
| count-change-02 | count_change | false | 0.010 | false | jev-1.13.0 | 822 |
| count-change-03 | count_change | false | 0.010 | false | jev-1.13.0 | 853 |
| prohibition-dropped-01 | prohibition_dropped | false | 0.010 | false | jev-1.13.0 | 818 |
| prohibition-dropped-02 | prohibition_dropped | false | 0.020 | false | jev-1.13.0 | 822 |
| prohibition-dropped-03 | prohibition_dropped | false | 0.040 | false | jev-1.13.0 | 806 |
| style-change-01 | style_change | false | 0.010 | false | jev-1.13.0 | 819 |
| style-change-02 | style_change | false | 0.040 | false | jev-1.13.0 | 799 |
| style-change-03 | style_change | false | 0.010 | false | jev-1.13.0 | 907 |

## Limits

- This is a small, hand-authored, class-imbalanced diagnostic set.
- It covers explicit English prompt constraints and Noul mode only.
- It does not establish general accuracy or a production-calibrated threshold.
