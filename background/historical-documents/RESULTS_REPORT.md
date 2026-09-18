# Implementation and research results — 2026-09-17

> This report records the earlier specialist-model and compiler work. It contains no measured Jev improvement. The subsequently requested [Jev-focused study](results/jev/README.md) has its own frozen protocol, real API responses, evaluation and repeatability evidence.

All five implementation stages were executed: evaluation repair, verified local inference, controlled evidence/identity/calibration experiments, actual compiler transactions, and advanced policy controls. The strongest measured findings are that complete evidence improves this SciFact classification task, task-specific identity training beats the lexical baseline on DBLP–ACM, and calibration improves probability scores. Extra context alone is inconclusive; identity transfer fails on the original fixtures. Advanced graph-policy results are synthetic mechanism evidence.

These results supersede the earlier publication headline claims. The original benchmark JSON files remain byte-for-byte unchanged. Their interfaces, labels, uncertain-example scoring, and undocumented model execution make their headline accuracies unsuitable as a before/after comparison with the new runs. The [original audit](../new-theory/BASELINE_AUDIT.md) preserves that diagnosis.

## What changed

The evaluator now validates a declared complete label space, probabilities, errors, and coverage. Brier is the **sum over all classes**, ranging from 0 to 2; log loss clips the gold probability at `1e-15`. Reports include macro-F1, balanced accuracy, confusion, reliability-bin counts, operational accuracy, and conditional accuracy. Uncertain fixture labels do not receive semantic correctness credit. Execution modes distinguish real computation, deterministic mocks, and unavailable models.

NLI receives the actual claim and separate evidence, with the checkpoint's declared contradiction/entailment/neutral mapping. A missing model fails explicitly. ER uses a newly trained binary identity head over record pairs rather than treating passage-ranking scores as identity probabilities. Every neural result records model revision or checkpoint hashes, logits, canonical probabilities, input serialization, and measured timing. Local execution used no paid API calls; local hardware, downloads, and electricity were not priced.

The compiler now changes an actual in-memory graph. It validates typed actions, evidence snapshots, decision dependencies, selected labels, declarative constraints and certificate bindings before atomic graph/provenance publication. It checks graph versions and request fingerprints, preserves exact retry idempotency, and rejects invalid batches without partial writes. Regression tests exercise tampered mutations, altered requests and provenance, nonfinite inputs, rollback, and version conflicts. Hashes provide internal consistency, not authenticated evidence or proof that an asserted fact is true.

## Protocol and data

| Task | Train | Calibration | Held-out evaluation | Unit and controls |
|---|---:|---:|---:|---|
| SciFact cited-abstract classification | 459 | 150 | 339 | Connected claims/documents/duplicate abstracts; 247 evaluation groups |
| DBLP–ACM identity matching | 4,592 | 390 | 413 | Positive identity components; no identity reused across held-out pairs |

SciFact uses official training data for priors, lexical selection and calibration, with official development claims held out for evaluation. Whole training claims overlapping evaluation documents/duplicate abstracts were purged (272 claims). This is classification of **supplied cited abstracts**, not document retrieval or an official leaderboard test. One repeated citation in the source was deduplicated; the 340-row intermediate is retained in [archive](results/research/archive/nli_results_340_duplicate_citation.json), and the 339-row analysis reused unchanged logits with verified inputs. Source: [SciFact dataset and task](https://github.com/allenai/scifact).

DBLP–ACM comes from pinned Ditto serialized records. Original pairs are regrouped by positive identity components, cross-split negatives are removed, contradictory serialized identities are quarantined (92 incident pairs), and deterministic disjoint matching constructs calibration/evaluation pairs. This changes prevalence: evaluation has 350 same and 63 different pairs, unlike the negative-majority training split. Accuracy therefore needs macro-F1, negative-class error rates, and the separately reported balanced slice. Annotation-defined identity groups are used for splitting only and never as model features. Source: [Ditto data at the pinned revision](https://github.com/megagonlabs/ditto/tree/52985564a93fb11308439516d3e17a033d43ec8f/data/er_magellan/Structured/DBLP-ACM).

Three ER arms share the pinned DeBERTa base, seed `20260917`, a fresh binary identity head, AdamW at `2e-5`, two epochs, batch size 8 and maximum length 256. Each epoch processes 4,592 examples. The no-hard-negative arm replaces 379 high-title-similarity negative pairs with training-only easy negatives, preserving class counts and optimizer budget. NLI weights remain unchanged, with maximum length 512. Scalar temperatures fit calibration log loss only; held-out labels do not fit temperatures. This follows the calibration approach described by [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).

## Real NLI evidence and calibration experiments

| Arm | Accuracy | Macro-F1 | Sum Brier | Log loss |
|---|---:|---:|---:|---:|
| Training prior | 38.35% | 0.1848 | 0.6469 | 1.0665 |
| First 80 characters | 40.41% | 0.3199 | 1.1453 | 4.0595 |
| Full abstract | 47.20% | 0.4166 | 0.9496 | 2.4649 |
| Full abstract, calibrated | 47.20% | 0.4166 | 0.6136 | 1.0201 |
| Lexically selected evidence | 48.97% | 0.4420 | 0.9094 | 2.3790 |
| Selected evidence, calibrated | 48.97% | 0.4420 | 0.6043 | 1.0066 |

Full evidence improves accuracy by **6.78 percentage points** over the 80-character arm, with a paired group-bootstrap 95% interval of **[1.47, 12.23]**. A generic wrong-hypothesis control reaches 38.05%. Full uncalibrated probabilities are substantially worse than the training prior on Brier despite higher accuracy. Calibration improves full-evidence Brier by 0.3360 without changing argmax accuracy.

Selection adds 1.77 accuracy points over full evidence, but its interval **[0.00, 3.96] includes zero**. Its Brier improvement is measurable in this run. Selection eliminates truncation without improving complete rationale-sentence retention: recall is 92.35% versus 92.62% with the full abstract. These results do not establish that selection preserves every decisive or opposing clause. [Full NLI report](results/research/NLI_RESULTS.md), [predictions and manifest](results/research/nli_results.json).

## Real identity experiments

| Arm | Accuracy | Macro-F1 | Sum Brier | False merges / 63 negatives | Missed matches / 350 positives |
|---|---:|---:|---:|---:|---:|
| Lexical logistic | 95.64% | 0.9198 | 0.0734 | 5 | 13 |
| Title-only model | 97.82% | 0.9587 | 0.0423 | 3 | 6 |
| Full-context model | 98.06% | 0.9639 | 0.0321 | 1 | 7 |
| No-hard-negative model | 98.31% | 0.9666 | 0.0305 | 5 | 2 |

Full context beats the lexical baseline by **2.42 accuracy points**, paired 95% interval **[0.72, 4.36]**. Full versus title-only changes accuracy by just 0.24 points, interval **[-1.45, 1.94]**; a context benefit remains unresolved. Removing hard negatives increases false merges from 1 to 5, while reducing missed matches from 7 to 2. The full-minus-no-hard false-merge-rate difference is -6.35 points, interval **[-12.70, -1.59]**, based on only 63 negative pairs. There is no demonstrated overall accuracy gain from hard negatives.

Calibrating the full-context model lowers Brier from 0.0321 to 0.0275. The training-prior baseline gets only 15.25% accuracy because train/evaluation prevalence differs; it is retained as a warning about the split distribution, not evidence of an easy neural victory. A saved-tokenizer audit found identical encodings across 21,580 real pair inputs and 14 Unicode probes despite a misleading generic Transformers tokenizer warning. [ER report](results/research/ER_RESULTS.md), [predictions and training manifests](results/research/er_results.json), [tokenizer audit](results/research/tokenizer_roundtrip_audit.json).

All intervals are exploratory, unadjusted for multiple comparisons, and conditional on one checkpoint/training seed and these fixed splits. They do not measure variation across training runs or new domains.

## Original fixtures expose a transfer failure

| Development diagnostic | Neural model | Constant control | Lexical control |
|---|---:|---:|---:|
| Relation support, 50 examples | 68.00% | 40.00% always-unknown | 56.00% fixed overlap/negation rule |
| ER, 88 binary-labeled examples | 51.14% | 86.36% always-same | 13.64% DBLP-trained lexical logistic |

All 600 model/control responses succeeded. The 12 uncertain ER examples are excluded from semantic metrics; the neural model nevertheless assigns at least 0.9 confidence to 9 of them, which is reported descriptively without correctness credit. These hand-curated examples are development fixtures without independent label adjudication. They show that the bibliographic identity model should **not** be assumed to transfer to names, organizations, proteins, or compounds. They do not estimate a population-level biomedical accuracy. [Fixture report](results/research/FIXTURE_DIAGNOSTICS.md).

## Compiler and advanced mechanisms

The compiler compares the same seven synthetic scored candidates. At three committed edges for each policy, typed interpretation reduces false commits from two to one; it still commits one semantically wrong fact. The confidence-only comparator deliberately ignores decision polarity and is a diagnostic baseline. Eleven graph-state scenarios pass, including stale versions, constraints, injected application failure, and retry conflicts. These small scenarios verify implementation behavior, not a statistical graph-quality improvement. [Compiler report](results/research/COMPILER_RESULTS.md).

E5/E7/E8 use 300 independent synthetic evaluation episodes per condition, paired episode bootstrap intervals, and separate routing development episodes. Their mechanisms are implemented in [research policies](pgc/research/policies.py), separate from the default compiler. In particular, there is no automatic production integration of joint clustering or query routing.

| Mechanism | Positive control | Failure or limitation |
|---|---|---|
| Group repeated evidence by origin | One-coordinate Brier 0.2542 → 0.1485 versus naive repeated evidence | Wrongly grouping independent origins loses information; origin groups are assumed known |
| Joint identity partitioning | Noisy-bridge pairwise F1 0.913 versus union-find 0.571 | A wrong hard rule lowers a perfect control from 1.000 to 0.800; exact solver is bounded to eight entities |
| Account for all dependencies | At 50% episode coverage with matched mutation counts, independent/unshared conditional corruption falls from about 0.419 to 0.379 versus a single-score gate | Union accounting does not consistently outrank products; conservative risk thresholds can reject nearly everything |
| Route by expected decision value | At five queries per 20 decisions, weighted error 4.232 versus confidence routing 5.348 | Under shifted specialist competence, error reverses to 10.276 versus 6.222 |

The evidence-aggregation Brier above uses **one binary coordinate**, half the full-sum convention used in neural reports. Dependency experiments use known simulated marginal error probabilities, not calibrated neural estimates. Matching both episode coverage and accepted mutation counts prevents lower work volume from masquerading as a safety gain. Routing matches evaluation query budgets but additionally uses 6,000 development queries per condition; that fitting cost is separately disclosed. [Advanced report and intervals](results/research/advanced_experiments.md).

## Hypothesis disposition

| Experiment | Disposition in this execution |
|---|---|
| E0: honest observation pipeline | Implemented and checked; original headline comparisons superseded |
| E1: complete semantic space and correct NLI wiring | Implemented; real three-way execution and wrong-input controls completed |
| E2: preserve evidence | Full-over-prefix gain supported here; selection accuracy gain unresolved |
| E3: identity training/context/hard negatives | Training beats lexical here; extra context unresolved; hard negatives trade recall for fewer false merges; domain transfer fails |
| E4: calibration | Held-out probability scores improve here; no formal deployment risk bound |
| E5: independent evidence accounting | Synthetic controls support the mechanism under correct origin grouping |
| E6: typed transactions | Behavioral invariants pass; semantic correctness remains fallible |
| E7: joint inference | Synthetic noisy-bridge gain; wrong hard rules cause damage |
| E8: dependency risk and routing | Assumption-dependent synthetic gains; no universal policy winner or real-data graph-risk guarantee |

## Reproducibility and practical limits

[README commands](README.md#reproduce-the-experiments) reproduce data preparation, real inference/training, synthetic experiments, artifact checks and plots. [The data manifest](results/research/data_manifest.json) records source hashes and split IDs; result files preserve exact model/dependency versions and source-file hashes at execution. Later reporting/validation changes are distinguished from original inference in the artifacts. The starting Git commit alone is insufficient to reconstruct this uncommitted implementation; retain the source tree with the artifacts.

The [artifact verifier](results/research/validation.json) passes all **30 checks** of saved-record consistency, split isolation and preserved historic inputs without rerunning models. All **90 unit tests pass**, exercising scoring failures and actual graph state, and `git diff --check` is clean. A [real NLI-to-compiler smoke run](results/research/real_compiler_smoke.json) checks the adapter/transaction integration on manually supplied examples; it is not held-out research evidence. [Repeated inference from reused ER checkpoints](results/research/checkpoint_reuse_verification.json) reproduces all eight arms' predictions within `1e-7` probability tolerance. [Accuracy figures](results/research/figures/observed_accuracy.svg) and [reliability/coverage figures](results/research/figures/reliability_and_coverage.svg) are standalone exports from saved JSON.

Remaining scientific work is a new phase: obtain adjudicated domain-specific identity data, repeat training across seeds and datasets, and evaluate complete real graph episodes at matched useful coverage and total cost. These results do not establish publication novelty, biomedical generalization, a formal accepted-transaction risk guarantee, or a production-durable graph service. In-memory transactions do not survive process loss; entity merges/schema migrations and generic node/type/property specialist models are not implemented. Unsupported operations fail explicitly.
