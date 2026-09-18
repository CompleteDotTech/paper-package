# Experiments that could falsify the new theory

This is the original prospective experiment plan. At its creation, execution comprised an offline reanalysis of saved JSON results and a deterministic compiler probe. The subsequently authorized stages have now been implemented and run in the sibling repository, including local training and real inference. See [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) for outcomes and scope; retain the proposed tests below as the original research record.

## 1. Establish a trustworthy observation pipeline

Freeze a run manifest with source commit, data hashes, split IDs, label definitions, package versions, model identifier/revision, output label mapping, input serialization version, seed, device, and `execution_mode = real | mock | unavailable`. Record raw logits or scores, canonical probabilities, execution errors, measured latency, and actual resource use. A mock must have its own name. An unavailable model must not appear as a measured specialist.

Use a decision record with distinct fields for semantic class, action/abstention, and execution status. An error never receives semantic correctness credit. Report service success rate separately from model quality on successful responses; also report operational accuracy with errors counted as failures. Do not conceal differential failure rates by dropping examples.

Use proper scores over the declared outcome space:

`Brier = (1/N) sum_i sum_k (p_ik - 1[y_i=k])^2` (unhalved multiclass convention).

For a binary task, state whether the reported value is the one-coordinate convention `(p_positive-y)^2` or the two-coordinate sum, which is twice as large. Use log loss with documented numerical clipping. Top-prediction confidence error is not a substitute for multiclass Brier. Add macro-F1, balanced accuracy, confusion matrices, and reliability plots with bin counts; a small Brier value alone does not establish calibration.

Meaningful fixtures: a probability vector with wrong class order; negative/NaN/non-normalized probability; known positive/negative/neutral examples; `ERROR` on an uncertain example; confident negative support; and a missing correct entity among choices. These verify the semantic contract rather than reproduce implementation details.

## 2. Establish data and baseline controls

Treat the existing 50/100 examples as development fixtures. Document their origin and adjudicate ambiguous labels. They do not provide documented official SciFact claim/document IDs. Use the official dataset's documented protocol for a separate scientific-claim experiment, preserving claim/evidence identity and reporting rationale/retrieval evaluation when relevant. [SciFact](https://aclanthology.org/2020.emnlp-main.609/).

For ER, collect traceable identity pairs with enough negative and ambiguous examples to measure false merges. Split by underlying entity/alias family; for relational experiments, keep shared evidence documents and near duplicates together. Reserve untouched evaluation units. Use development data for calibration, routing, rule weights, and policy selection; do not tune on the saved results and call those same results a new test.

Run majority/prior, lexical, real task-aligned model, and any available stronger-model baselines on identical canonical requests. Mocks remain diagnostic controls. Report both a representative class distribution and a balanced challenge set; avoid comparing accuracies across different prevalences.

Start with one verified local model per task. Larger models and external services are optional comparison arms after the harness works. Track measured device time and token/API costs separately; local inference has zero API fees, not zero total cost.

## 3. Controlled experiment matrix

| ID | Intervention | Hold fixed | Primary observation | Falsification condition |
|---|---|---|---|---|
| E0 | Canonical labels, honest errors, verified execution | Saved predictions where interpretable | Recomputed baseline and service availability | Any publication comparison still mixes task definitions or mocks |
| E1 | Correct NLI label mapping and premise/hypothesis inputs | Checkpoint, examples | Macro-F1, class recall, proper scores | No out-of-sample predictive benefit after wiring checks |
| E2 | Full/rationale-preserving evidence | E1 model and task | Late-clause robustness, rationale recall | Gain relies on dropping contrary passages |
| E3 | ER context, identity training, hard negatives | Entity-disjoint splits, budget | False merges, macro-F1, cluster quality | No improvement over lexical baseline on difficult negatives |
| E4 | Calibrated task/policy probabilities | Frozen raw predictions | Log loss/Brier; accuracy of risk estimates used for thresholds | Only calibration-split benefit; do not expect binary ranking gains from scalar temperature |
| E5 | Source-group evidence aggregation | Same unique documents | Duplicate invariance, independent-source sensitivity | Repetition still raises confidence or valid corroboration is lost |
| E6 | Typed commit certificates and transaction validation | Cached canonical decisions | Wrong/invalid committed mutations; atomicity | Confident refutations create facts, or failed batches partially persist |
| E7 | Joint decoding with hard/soft constraints | Same unary scores | Graph F1, false merges, rule violations | Gains vanish on entity-disjoint graphs or depend on wrong hard rules |
| E8 | Dependency/impact-based risk and selective routing | Cost and coverage | Corruption-risk/coverage/cost frontier | Apparent safety gain is entirely reduced coverage |

Run E1 repairs individually as well as together. For the compiler, compare direct application, threshold-only application, typed validation, and joint inference using the same cached backend decisions. Then compare the full improved pipeline to the corrected baseline. This separates adapter repair, prediction improvements, and compiler effects.

## 4. Measure graph behavior directly

Build small executable graph scenarios with known correct final states and injected defects: missing endpoints, incompatible endpoint types, duplicate identifiers, conflicting functional properties, time-scoped facts, and merge triangles where A=B and B=C conflict with A!=C. Include valid near misses so a validator cannot win by rejecting everything.

Replay stale-version writes, repeated requests, failure after the first planned mutation, dependency deletion, and evidence-source replacement. Verify an actual graph snapshot and provenance store before/after each attempt, rather than trusting a `COMMITTED` field or printed message.

Report:

- Semantic precision/recall of committed nodes and edges, with a documented graph-matching procedure.
- False-merge rate and a cluster metric such as pairwise F1, with its denominator specified.
- Invalid mutations applied / attempted invalid mutations, plus valid mutation rejection rate.
- Accepted mutation count, coverage, deferred workload, rollback/replay behavior, and recovery time.
- Probability of any semantic error per transaction and impact-weighted error cost; these differ from per-edge accuracy.

A provenance link demonstrates traceability, not factual support. Schema-valid updates can still be semantically false. Evaluate these properties separately.

## 5. Uncertainty and decision rules for declaring progress

Use paired comparisons on the same held-out units. Bootstrap documents/entities/graph episodes rather than correlated rows. Report intervals and effect sizes; repeated random seeds quantify training variation, not additional independent data. Predeclare one primary metric per hypothesis and account for many comparisons. Use development runs to estimate variance and plan sample size, rather than declaring that 500 examples is automatically sufficient.

Example engineering target, to be agreed before experiments: increase accepted correct graph updates at a fixed 5% maximum probability of corruption per independent graph episode and a fixed cost budget. Here an episode includes a policy's decision to commit or defer; no committed corruption gives loss zero. The 5% is an illustrative design choice, not a safety requirement or an achieved result. Give minimum coverage explicitly so deferring every update cannot satisfy the research objective by itself. Also report error conditional on making a commit; that is a different risk target.

For a *fixed policy*, if n independent representative transactions have zero errors, the exact one-sided 95% binomial upper bound on error probability is `1 - 0.05^(1/n)`. It takes at least 59 zero-error transactions for this bound to be below 5%, and 299 for below 1%. This illustration assumes independent identically distributed transaction outcomes; correlated graph updates are not independent transactions. Choosing the policy using the same observations invalidates this simple interpretation without selection correction.

For a finite set of K policies fixed before calibration, a conservative selection-aware alternative for bounded transaction losses is:

`U_k = min(1, mean_loss_k + sqrt(log(K/delta)/(2n)))`.

Under independent identically distributed calibration units and unchanged deployment distribution, simultaneous Hoeffding bounds give `risk_k <= U_k` for all K policies with probability at least `1-delta`. Here risk is expected bounded loss over the fixed evaluation unit, such as every graph episode. Counting deferred episodes as zero bounds unconditional corruption probability; a separate coverage check does not convert it into an accepted-transaction error bound. Select among policies meeting the chosen risk target and check coverage separately. These bounds may be too loose on small data. They do not survive arbitrary distribution shift or adaptive policy construction on the same calibration set. More specialized methods are a subsequent research direction; conformal risk control is not automatically a guarantee for non-monotone accepted-error ratios. [Conformal Risk Control](https://arxiv.org/abs/2208.02814).

## Deliverable sequence

1. Corrected scoring and one reproducible real-backend run per task, with sensible baselines.
2. Paired H1-H3 input/model ablations and independent calibration evaluation.
3. An executable mutation evaluator and E6 ablations with frozen predictions.
4. E5/E7/E8 dependence, graph inference, and routing experiments with cost/coverage matched.
5. A results table labeling each hypothesis supported, contradicted, or unresolved. Keep null results and failures visible.

The strongest prospective paper claim is specific and testable: **preserving semantic decisions and their dependencies through compilation improves accepted graph quality at matched coverage and budget**. This is a proposed claim, not an established result or a verified novelty claim.
