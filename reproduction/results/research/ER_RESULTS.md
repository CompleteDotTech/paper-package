# Real entity-matching experiments

Entity-disjoint DBLP-ACM evaluation. Every neural arm trained locally with the same budget.

| Arm | Accuracy | Macro-F1 | Sum Brier | False merge rate |
|---|---:|---:|---:|---:|
| train-prior | 0.1525 | 0.1324 | 0.8911 | 0.0000 |
| lexical-logistic | 0.9564 | 0.9198 | 0.0734 | 0.0794 |
| er-title-only | 0.9782 | 0.9587 | 0.0423 | 0.0476 |
| er-title-only-calibrated | 0.9782 | 0.9587 | 0.0404 | 0.0476 |
| er-full-context | 0.9806 | 0.9639 | 0.0321 | 0.0159 |
| er-full-context-calibrated | 0.9806 | 0.9639 | 0.0275 | 0.0159 |
| er-no-hard-negatives | 0.9831 | 0.9666 | 0.0305 | 0.0794 |
| er-no-hard-negatives-calibrated | 0.9831 | 0.9666 | 0.0271 | 0.0794 |

All probability scores use the sum-over-classes convention. Training, calibration and evaluation identities are disjoint.
Negative rate differs across splits due to pair blocking and disjoint matching. See balanced slices and manifests in er_results.json.
One seed and this bibliographic dataset do not establish biomedical generalization or a general neural advantage.

## Paired comparisons

```json
{
  "er-full-context minus er-title-only": {
    "accuracy_difference": 0.002421307506053269,
    "paired_95_percentile_interval": [
      -0.014527845036319613,
      0.01937046004842615
    ],
    "brier_difference": -0.010148018052014929,
    "brier_ci95": [
      -0.040367907662528325,
      0.01878641466681966
    ],
    "false_merge_rate_difference": -0.031746031746031744,
    "false_merge_ci95": [
      -0.09523809523809523,
      0.031746031746031744
    ],
    "false_merge_denominator": 63,
    "bootstrap_unit": "one evaluation pair with disjoint identity groups",
    "resamples": 2000,
    "multiplicity": "exploratory unadjusted interval; no confirmatory significance claim"
  },
  "er-full-context minus er-no-hard-negatives": {
    "accuracy_difference": -0.002421307506053269,
    "paired_95_percentile_interval": [
      -0.01694915254237288,
      0.012106537530266344
    ],
    "brier_difference": 0.0016462218454623455,
    "brier_ci95": [
      -0.024450924041788176,
      0.02844029762986636
    ],
    "false_merge_rate_difference": -0.06349206349206349,
    "false_merge_ci95": [
      -0.12698412698412698,
      -0.015873015873015872
    ],
    "false_merge_denominator": 63,
    "bootstrap_unit": "one evaluation pair with disjoint identity groups",
    "resamples": 2000,
    "multiplicity": "exploratory unadjusted interval; no confirmatory significance claim"
  },
  "er-full-context minus lexical-logistic": {
    "accuracy_difference": 0.024213075060532687,
    "paired_95_percentile_interval": [
      0.007203389830508478,
      0.043583535108958835
    ],
    "brier_difference": -0.04125688404259971,
    "brier_ci95": [
      -0.070215466011029,
      -0.013910067920651905
    ],
    "false_merge_rate_difference": -0.06349206349206349,
    "false_merge_ci95": [
      -0.12698412698412698,
      -0.015873015873015872
    ],
    "false_merge_denominator": 63,
    "bootstrap_unit": "one evaluation pair with disjoint identity groups",
    "resamples": 2000,
    "multiplicity": "exploratory unadjusted interval; no confirmatory significance claim"
  }
}
```

Sources: [Ditto data/code](https://github.com/megagonlabs/ditto), [base NLI checkpoint](https://huggingface.co/cross-encoder/nli-deberta-v3-small).
