# Relationship-fusion experiment protocol v1

## Status and scope

This protocol is committed before executing the new combination experiments. The original evaluation outcomes were already inspected and discussed before this follow-up. This is therefore an **exploratory post-hoc analysis of frozen inference**, not an independent test population, external preregistration, new Jev model, or fresh remote inference. Null and negative results will be retained. Original evidence and MANIFEST files must remain unchanged.

Base repository: `b4a7e3a2df0b77df9ba01f0c611927ca6d1ec914`. Inputs: the authenticated raw calls, predictions, and plan in `reproduction/results/jev/run-20260918`. Use `RecordedJev` to reconstruct probabilities and reject input or provenance changes. Task: supplied SciFact claim/abstract classification, materialized as `Document -> supports/refutes -> Claim`. NOT_ENOUGH_INFO and abstentions create no edge. This is not domain-predicate extraction or a KARMA reproduction.

## Arms

1. `baseline_choice`: unchanged generic Jev Choice decisions, one recorded call per example.
2. `fewshot_contract`: unchanged selected Jev formulation, one recorded call per example.
3. `mean_pool`: arithmetic mean of the two valid probability vectors; fixed equal weights, no fitting.
4. `agreement_gate`: arithmetic mean only when both valid vectors have the same deterministic argmax; otherwise ABSTAIN. An invalid constituent is ERROR, not an invented distribution or a semantic abstention.
5. `stacked`: regularized multinomial logistic regression over the six concatenated clipped log-probabilities, trained only on common-success calibration rows. The stacker estimates a distribution from correlated inputs; it does not assume that the two calls are independent corroborating sources.

All ensemble arms require both constituent calls. No silent one-call fallback. Tie order is SUPPORTS, REFUTES, NOT_ENOUGH_INFO. Clip log features at 1e-6, standardize using training-fold means/scales only, and include an unpenalized intercept. The training objective is mean negative log-likelihood plus lambda/2 times the sum of squared non-intercept coefficients. Fit with deterministic full-batch gradient descent and a spectral Lipschitz step, bounded iterations, and reported convergence diagnostics.

## Selection boundary

Only the original calibration split (150 rows, 73 connected claim/document components before failures) may fit or select the stacker. The API rejects any other split. Five folds are assigned by SHA-256 of `relationship-fusion-v1:` plus component identifier modulo five, without consulting labels. Regularization grid: 0.01, 0.1, 1.0, 10.0. Choose greatest pooled out-of-fold operational macro-F1, break ties by lower out-of-fold negative log-likelihood, then larger lambda. Refit the chosen lambda on all valid calibration rows. Preserve fold membership, out-of-fold scores, chosen hyperparameter, fitted coefficients, optimizer diagnostics, and input hashes. These cross-validation scores are selection diagnostics, not independent evaluation estimates.

Prediction functions must accept probabilities without gold labels. Evaluation labels must not affect fitting, arm definitions, thresholds, ranking, graph construction, or candidate selection. Altered evaluation gold must leave predictions and graph audits unchanged. No evaluation-derived winner is promoted into production. No additional hyperparameters or variants will be added after inspecting this experiment's evaluation outcomes without a labeled amendment.

## Endpoints and comparison

Primary descriptive endpoint: stacked minus each original arm in operational three-class macro-F1 on all 339 evaluation rows, counting ERROR/ABSTAIN as missed gold labels. Also report common-success comparisons on the shared valid-response population.

Graph endpoints: correct and incorrect typed edges; precision; recall with denominator all gold SUPPORTS/REFUTES rows; coverage with denominator all examples; per-relation precision/recall; confusion; operational errors and semantic abstentions. Never credit abstention as correct NOT_ENOUGH_INFO.

For every arm report precision and correct/incorrect edge counts at the same accepted-edge counts, using descending proposed-edge probability and stable identifier tie-breaking. Compare each pair at the smaller available edge count, and report fixed budgets 25, 50, 75, 100, 125, 150, 175, 200 where available. This is a score-only descriptive comparison, not selection of a production threshold. Report pooled and per-predicate comparisons. Expose ties at the selection boundary; exact-K tie-breaking must not be presented as a probability threshold policy.

Use 2,000 paired component-bootstrap draws, seed 20260918, for macro-F1 and pooled matched-volume edge-precision differences. Resample whole evaluation components and keep paired decisions. Matched-volume intervals condition on the original selected sets (do not imply reranking or refitting uncertainty); report unequal accepted denominators within a draw and any undefined draws. Intervals are exploratory, unadjusted for multiplicity, and do not incorporate model deployment changes, hyperparameter reselection, or distribution shift.

## Graph and provenance

Materialize experimental assertions with the existing reversible graph store and exercise controlled source withdrawal, persistence, and audit verification. Combined outputs remain recorded-inference derivatives, never live observations. Hash the policy/model artifact together with both constituent request hashes, and keep a journal resolving that hash to the exact inputs and fitted transformation. A combined call identifier must not be mistaken for a vendor call. Graph publication is descriptive; it provides no semantic-risk certificate and does not enable production acceptance.

## Resources and verification

Report zero fresh HTTP calls, local fitting cost separately, and actual recorded usage for the constituent calls. Two-formulation inference has a two-call cost, even though replay has no new provider charge. Do not interpret ensemble agreement as independent evidence.

Tests must cover: frozen evidence integrity; group-disjoint folds; split and gold leakage prevention; optimizer loss/gradient/probability behavior; raw failure preservation; deterministic replay; metric denominators and absent classes; paired resampling and matched coverage; provenance binding; graph withdrawal and audit; unchanged original 60 tests. CI must run without credentials and reproduce the new checked-in results within declared floating-point tolerance, with exact agreement for decisions and integer counts.

## Reporting

Commit a machine-readable results artifact, fitted selection/model artifact, per-example decision journal, generated baseline-comparison table, and written research note. Describe whether any improvement is aggregate accuracy, a precision/recall tradeoff, or a matched-volume gain. Preserve null outcomes and limitations. Merge only after review of the actual diff and successful checks.
