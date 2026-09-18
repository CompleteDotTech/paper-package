# Improving decisions before they become graph mutations

Date: 2026-09-17. Status: research proposals, not measured improvements.

The working hypothesis is that preserving task semantics, evidence, and uncertainty will matter more than immediately increasing model size. The existing results cannot determine which model family is best; see [the baseline audit](BASELINE_AUDIT.md). These proposals start after a reproducible, correctly scored baseline exists. Compiler-level hypotheses are developed separately in [COMPILER_THEORY.md](COMPILER_THEORY.md).

## H1. Preserve the complete decision space

**Observed bottleneck.** The relation benchmark asks a binary question, although its saved gold labels include 20 uncertain cases among 50 examples. A backend restricted to `true/false` cannot score those 20 cases correctly. Its maximum possible three-class exact accuracy is therefore 30/50 = 60%, regardless of model quality. The NLI adapter also feeds a generic question as the hypothesis and treats output index 2 as entailment. The checkpoint configuration instead identifies index 1 as entailment and index 2 as neutral. [Model configuration](https://huggingface.co/cross-encoder/nli-deberta-v3-large/blob/main/config.json).

**Mechanism.** Introduce a task-specific request containing separate `claim`, `evidence`, and `label_space` fields. An NLI adapter receives `(evidence, actual_claim)` and returns the three class scores using the checkpoint's declared label mapping. With raw logits z, compute:

`p(y | evidence, claim) = softmax(z / T)[label_id(y)]`.

Use exactly one documented score-to-probability transformation. If the library already returns probabilities, do not softmax them again. Validate finite values, class names, and normalization. Retain `SUPPORTS`, `REFUTES`, and `NOT_ENOUGH_INFO` in the ledger. A binary support probability can be derived when an operation needs it, but cannot reconstruct the lost refutation/unknown distinction.

Separate three different states: a semantic `NOT_ENOUGH_INFO` prediction, an action `DEFER`, and an execution status `ERROR`. An unavailable model has no semantic prediction. For entity resolution, `uncertain` may mean inadequate annotation or context rather than a third kind of identity; adjudicate that meaning before choosing a three-class training target.

**Prediction.** Correct task inputs and labels improve minority-class recall and proper scoring without changing model weights. Scalar temperature scaling can improve probability quality but preserves argmax classification for T > 0; an accuracy improvement from temperature alone would require a changed action threshold or a bug.

**Test and rejection.** Evaluate label-map repair, input separation, and complete label space as separate ablations using the same verified model. Reject the proposed predictive benefit if these do not improve held-out macro-F1/proper scores; still retain semantic correctness as an interface requirement. Include known entailment, contradiction, and neutral fixtures to diagnose wiring independently of aggregate scores.

## H2. Evidence selection should preserve decisive clauses and opposing evidence

**Observed bottleneck.** The relation harness truncates every evidence passage to 80 characters before inference (`scifact_benchmark.py`, `_run_one`). This can discard a result, qualification, or negation while retaining only a topical introduction. The supplied examples are curated fixtures, so any biomedical generalization also needs evaluation on traceable source data.

**Mechanism.** Replace character truncation with a token budget and sentence-level selection. Retrieve both supporting and contradicting candidates; keep source IDs, offsets, neighboring qualifiers, and source versions. First compare the current input with full provided passages. Only then add retrieval, so retrieval improvements are not confused with repairing destructive truncation.

A useful decomposition is:

`P(correct supported commit) = P(relevant evidence retained) * P(correct supported commit | relevant evidence retained)`

under a policy that requires relevant evidence for a supported commit. This is a bottleneck decomposition, not an independence assumption. Raising classifier accuracy cannot recover an indispensable sentence that never reaches the classifier.

**Prediction.** Complete or rationale-preserving evidence should reduce errors involving late negation, species/population restrictions, and unsupported extrapolation. The official SciFact task includes evidence selection and rationales, making it a useful separate evaluation of this mechanism. [SciFact paper](https://aclanthology.org/2020.emnlp-main.609/).

**Test and rejection.** Compare 80 characters, full supplied passage, fixed token budget, and sentence-selected evidence. Measure retained-rationale recall alongside claim accuracy. Use paired perturbations placing the decisive sentence early/late. Reject a proposed selector if it raises label accuracy by dropping contrary evidence or fails on the late-clause cases. Full passages can also add distractors; improvement is not guaranteed.

## H3. Entity resolution needs identity evidence, context, and hard negatives

**Observed bottleneck.** The ER harness supplies only two mention strings. `ERExample` has a context field, but it is not included in the request. The default model identifier differs from the published `cross-encoder/ms-marco-MiniLM-L12-v2` identifier. That published model is trained for passage ranking, not identity classification. Its relevance score is not automatically a calibrated identity probability. [Model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2).

**Mechanism.** Represent both entities as structured records: name, entity type, stable identifiers where available, aliases, time, organization, species, and surrounding mention context. Supply only legitimately available attributes. Train or adapt a pair classifier on identity labels, with explicit negative examples such as parent organization versus subsidiary, gene versus protein, and similarly named people with conflicting identifiers. Abbreviation expansion should create candidate matches, not establish identity.

For a source entity x and possible matches C, distinguish:

`match(candidate_id)`, `new_entity`, and action `defer`.

Do not interpret a high normalized choice probability as proof of a match when the correct entity is absent from C. Measure candidate recall before ranking. A type incompatibility can block a match only when the schema makes that incompatibility a reliable invariant.

Entity matching as supervised pair classification with serialized attributes is grounded in prior work; the project-specific conjecture is that identity context and graph consequences will outperform lexical similarity here. [Ditto paper](https://vldb.org/pvldb/vol14/p50-li.pdf).

**Prediction.** Context should reduce false merges on difficult negatives, even if it lowers accuracy on an imbalanced collection of easy aliases. Evaluate false-merge cost, per-class F1, and cluster quality, rather than optimizing the proportion of `same` predictions.

**Test and rejection.** Compare always-same, normalized exact match, a lexical matcher, verified ranking model plus learned calibration, and an identity-trained pair model. Add context and hard-negative training separately. Split by underlying entity and alias family. Reject the context hypothesis if gains disappear under entity-disjoint evaluation or do not beat the lexical baseline on difficult negatives.

## H4. Count independent evidence, not repeated text

**Observed opportunity.** The IR already tracks evidence sources and content hashes. This could support evidence dependence analysis, which the current independent decision path does not exploit.

**Mechanism.** Group duplicate or derivative passages by provenance: exact copy, common paper, cited common experiment, or unresolved dependence. Under conditional independence, log likelihood ratios add to prior log odds. Copying one item twice violates that assumption and should not supply two independent likelihood factors.

A practical proposed score is:

`s = b + sum_g w_g * aggregate({h(e, claim) : e in source_group_g})`.

Here h is a learned evidence score, groups approximate shared origins, and w and the within-group aggregation are fitted on development data. This is a scoring architecture, not an automatically valid Bayesian posterior. Calibrate its output after aggregation. Never silently discard contrary evidence in deduplication.

**Prediction.** Duplicate sources will cease to inflate confidence; genuinely independent corroboration can increase confidence when development data support that behavior.

**Test and rejection.** Duplicate one supporting passage 1, 2, 5, and 10 times, then compare with independently sourced corroboration and independent contradiction. Require exact-copy invariance for identical source evidence. Reject the broader source-grouping approach if it suppresses independent evidence or worsens reliability under realistic citation chains. Claims sharing sources must be grouped during evaluation to avoid overstating sample size.

## H5. Spend extra inference only where it can change the action

**Observed bottleneck.** The compiler uses a single confidence threshold of 0.85. It cannot distinguish a low-impact property update from a mistaken merge that contaminates many edges. Several backend batch methods also execute serially, and the compiler currently issues duplicate decisions; fix that call path before measuring routing savings.

**Mechanism.** Choose among `commit`, `reject`, `defer`, and `acquire_more_evidence`. Let p be the probability that a proposed update is correct, Cw its wrong-commit cost, Cm the cost of missing a correct update, and Cd a review cost. A deliberately simple decision model is:

`L(commit) = (1-p) Cw; L(reject) = p Cm; L(defer) = Cd`.

The defer expression assumes review resolves the case; a realistic version adds expected review mistakes and delay. Without defer, commit is preferred when `p > Cw / (Cw + Cm)`. Thus a high-impact merge should demand more evidence than a low-impact reversible annotation.

For an additional query q, define:

`VOI(q) = min_a E[L(a) | current evidence] - E_result[min_a E[L(a) | current evidence, result]] - cost(q)`.

Use extra retrieval or a second model only when an estimate of this value is positive. Estimate it on development data; a model's self-reported confidence is not an oracle. Backend agreement on shared evidence is not independence.

**Prediction.** A specialist-first policy with selective escalation can improve committed-graph utility at fixed cost or coverage. Raw all-example accuracy need not increase.

**Test and rejection.** Compare all-specialist, all-stronger-model, random escalation, confidence escalation, and impact-aware escalation with the same spending/latency budget. Report the full risk-coverage-cost frontier. Reject the routing hypothesis if its advantage disappears at matched coverage or is entirely explained by deferring more examples.

## H6. Calibration belongs to a task and deployment policy

Fit a small calibrator on independent development predictions after fixing model adapters. Temperature scaling is a defensible initial candidate for multiclass logits. Its empirical usefulness is established elsewhere, not yet on this project. [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).

Record calibration version, label space, training split hash, source population, and intended action policy. Recheck calibration after changes to candidate generation, retrieval, model revision, or selection policy. Avoid fitting a flexible per-category calibrator on the current tiny dataset; pooled calibration and category-level diagnostics are a better first experiment.

**Prediction and falsification.** Held-out log loss/Brier should improve, and probabilities should better match the error rates used to set action thresholds. Scalar temperature scaling preserves binary confidence ranking, so it cannot by itself improve binary risk at fixed coverage except through tie handling; claim a better risk-coverage frontier only if ranking or routing changes. Reject a calibrator that only improves its fitting split, worsens important entity categories, or masks systematic errors with low confidence. Report raw and calibrated performance together. Statistical risk-control methods require assumptions about the calibration/test units and loss; they do not establish truth for individual graph facts. [Conformal Risk Control](https://arxiv.org/abs/2208.02814).

## Suggested order

First repair the measurement contract and verify real execution. Then test H1-H3 with modest local baselines. Add H6 before setting commit thresholds. Test evidence dependence (H4) and routing (H5) after source provenance and a real mutation evaluator exist. The compiler theories should be tested with the same cached decision outputs so architectural gains can be attributed separately from improved classifiers.
