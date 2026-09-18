# Original fixture diagnostics

These hand-curated development examples test the repaired legacy harness. They are not official SciFact data or held-out biomedical validation. The identity model was trained on bibliographic records; names, organizations, proteins, and compounds here are outside that training distribution.

## Relation support: 50 examples

| Arm | Accuracy | Macro-F1 | Sum Brier | Errors | Execution |
|---|---:|---:|---:|---:|---|
| specialist-nli | 0.6800 | 0.6690 | 0.5728 | 0 | {'real': 50} |
| constant-SUPPORTS | 0.3000 | 0.1538 | 1.4000 | 0 | {'real': 50} |
| constant-NOT_ENOUGH_INFO | 0.4000 | 0.1905 | 1.2000 | 0 | {'real': 50} |
| lexical-overlap-negation | 0.5600 | 0.4905 | 0.8800 | 0 | {'real': 50} |

## Entity resolution: 88 binary-labeled + 12 uncertain examples

Only the 88 same/different labels enter semantic metrics. The 12 uncertain cases receive no correctness credit.

| Arm | Accuracy | Macro-F1 | Sum Brier | Errors | Execution |
|---|---:|---:|---:|---:|---|
| specialist-er | 0.5114 | 0.4314 | 0.8770 | 0 | {'real': 100} |
| constant-same | 0.8636 | 0.4634 | 0.2727 | 0 | {'real': 100} |
| normalized-exact | 0.1591 | 0.1481 | 1.6818 | 0 | {'real': 100} |
| dblp-train-lexical-logistic | 0.1364 | 0.1359 | 1.6207 | 0 | {'real': 100} |

## Uncertain ER predictions: descriptive only

| Arm | Predict same | Predict different | Confidence ≥ 0.9 / successful responses |
|---|---:|---:|---:|
| specialist-er | 4 | 8 | 9 / 12 |
| constant-same | 12 | 0 | 12 / 12 |
| normalized-exact | 0 | 12 | 12 / 12 |
| dblp-train-lexical-logistic | 3 | 9 | 6 / 12 |

Brier is the sum over all classes (range 0–2), including both classes for ER; log loss clips gold probabilities at 1e-15. Constant and deterministic lexical rules use point-mass encodings, so their confidence of 1 is not a calibration claim. Lexical logistic probabilities are fitted only on DBLP training pairs and are not assumed calibrated on these fixtures.

NLI receives the full supplied passages and actual claim. ER receives both mentions plus supplied context through the repaired benchmark. Every response records mode, backend version, errors, input serialization, and neural raw logits where available. Models run locally with zero API calls; observed wall time is recorded, and zero API fees does not imply zero compute cost.

Constant SUPPORTS, NOT_ENOUGH_INFO, and same controls are predeclared descriptive baselines, not chosen by optimizing fixture outcomes. NOT_ENOUGH_INFO and same happen to be the fixture majority labels. The shallow relation lexical rule uses a fixed 0.6 content-word overlap threshold and a four-word negation check.

Do not subtract historical headline accuracies from these results: interfaces, labels, error handling, inputs, and models changed. These examples have been used for development, include unadjudicated labels, and do not establish improved scientific generalization.

Reproduce: `.venv\Scripts\python.exe -m pgc.experiments.run_fixture_diagnostics`.
