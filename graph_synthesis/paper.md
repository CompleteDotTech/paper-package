# From Typed Decisions to Repairable Evidence Graphs
## An uncertainty-aware assessment of identity resolution, relation verification, and graph repair

**Timothy Wayne Gregg**  
**Research manuscript draft — 17 September 2026, America/New_York**  
Companion to the original Jev study at commit `5b511c88c011524ad6adb71f1d5fa22f3dc941e0`. Visual revision based on repository snapshot `c3db4b81bed46b497143b30d1e26c73937ee3d67`.

**Status.** This manuscript reports executed software tests and a post-hoc analysis of existing model observations. It is an author-review draft, not an independently reviewed or submitted publication. It does not report fresh Jev inference, new human annotation, or a KARMA replication. Affiliations, funding, conflicts, final authorship approval, release permissions, and submission venue have not been confirmed. AI assistance was used for implementation, analysis, and drafting; the named author must review and approve the final work.

## Abstract

**September 18 update:** A subsequent [fresh full Jev run and updated manuscript](../manuscript/paper-current.md) reports 3,404 main-run calls plus a 48-case live synthetic challenge. The fresh entity macro-F1 interval includes zero, weakening the original interval-based finding. The analysis below remains explicitly based on the original frozen observations; its figures have not been relabeled as fresh results. See also the [completed falsification addendum](../experiments/falsification/PAPER_ADDENDUM.md).

A well-formed semantic decision is not yet a reliable graph update. We investigate the transition from bounded model judgments to evidence-preserving, repairable graphs using an immutable Jev research package. We implement explicit relationship contracts, source- and decision-bound assertions, durable versioned transactions, reversible identity views, and dependency-aware retraction. We reconstruct the original observations and compile the two retained formulations into four graph stores. On 413 DBLP–ACM pairs, the selected formulation produces 349 correct and two incorrect same-identity assertions, versus 350 and eight for the baseline. On 339 SciFact claim–abstract pairs, it produces 110 correct and eight incorrect support assertions, versus 122 and eighteen. However, at equal accepted counts, the identity comparison is four versus two errors and the support comparison is nine versus eight; both exploratory paired precision-difference intervals include zero. No operating threshold qualifies for the illustrative 1% conditional false-positive target. The selected relation graph has 241 isolated candidate nodes versus 180 for baseline. At the returned score endpoint of 1.0, its 73 accepted support/refutation actions still contain five errors. Existing probability-combination experiments show no resolved macro-F1 gain. Controlled source withdrawal, durable reopen, and audit checks pass for all four stores. These results establish executable graph acceptance and repair mechanisms, not general autonomous graph synthesis. The strongest practical finding is that improvements in accepted-edge precision must be interpreted jointly with coverage, relationship semantics, and the dependency structure of committed assertions.

**Keywords:** knowledge graphs; entity resolution; evidence provenance; graph synthesis; typed decisions; selective prediction; reproducibility; truth maintenance.

## 1. Introduction

A graph-building system must decide not only whether a model output is plausible, but also what that output permits the system to assert. The judgments that two records describe one entity, that an abstract supports a claim, and that a proposed relation belongs to an ontology are different decisions. Treating them as interchangeable confidence scores obscures both their error consequences and the conditions under which a graph update should be reversed.

The preceding Jev study compared request formulations for bibliographic identity matching and supplied claim–abstract classification [1]. It provided evidence of improved entity macro-F1 on one custom split, but no resolved overall relation-classification gain. It explicitly excluded candidate discovery, cluster-level validation, and end-to-end graph construction. This work addresses an implementation gap within that boundary: can the saved decisions be bound to actual graph assertions, analyzed at useful acceptance coverage, and withdrawn without destroying source history?

Our contributions are a small durable graph compiler, an exact-input adapter for the recorded Jev formulations, and an executed graph-level reanalysis. We distinguish four evidence categories throughout: original model observations, newly computed descriptive statistics, controlled lifecycle interventions, and synthetic software tests. We do not combine these categories into a single semantic-accuracy claim. In particular, passing a constraint test establishes behavior under that test, not the truth of a biomedical statement.

We organize the assessment around four questions: does an apparent precision gain persist at equal accepted volume; which error types are prevented or deferred; what happens to candidate coverage and graph structure; and what evidence supports confidence-based acceptance and later repair? The figures are designed to answer those questions rather than illustrate an assumed advantage.

The resulting artifact supports a bounded evidence-graph pilot. It does not implement an unrestricted document-to-ontology system. That distinction is central to both the comparison with KARMA and the interpretation of the numerical results.

## 2. Related work and positioning

KARMA v2 describes a multi-agent enrichment pipeline spanning entity discovery, relationship extraction, schema alignment, conflict handling, and integration. It permits multiple relationship labels, sends unsupported schema additions for review, and evaluates graph statistics alongside model-based and human assessments [2, Sections 3.7–3.10 and 4.3]. Its full-pipeline evaluation and our fixed-candidate replay therefore answer different questions. We neither execute KARMA nor transfer its reported scores into our tables.

Calibration concerns whether probabilities correspond to empirical outcome frequencies, not just whether labels are well formed [8]. Our reliability diagrams are descriptive classwise diagnostics; the previously executed calibration fits remain a separate experiment.

Our design focus is the acceptance boundary after candidates exist. An appropriate future comparison would first hold candidate records and evidence fixed while varying acceptance and repair policies. A second experiment could compare complete candidate-generation pipelines under matched resource budgets. This two-level design would separate better discovery from more selective commitment and avoid crediting a system merely for declining more candidates.

SciFact supplies scientific claims, abstracts, and evidence annotations [3]. We reuse the preceding study's derived cited-abstract task, not the full retrieval benchmark. The identity records originate in the DBLP–ACM serialization distributed with Ditto [4], but our results are not a retraining or leaderboard comparison with Ditto. The custom splits and original data limitations remain those documented in the archived study [1].

TypeSafe documents bounded typed questions over application state [5]. Our adapter preserves those question meanings and recorded payloads; it does not interpret interface validity as factual validity. W3C SHACL provides a vocabulary for graph validation [6], while PROV-O models provenance relations among entities, activities, and agents [7]. The implementation is inspired by these separations of responsibility but is not a complete SHACL processor, PROV-O serializer, or OWL reasoner. No priority claim is made for provenance, transactional updates, selective classification, or dependency-based truth maintenance.

## 3. Representation and relationship semantics

### 3.1 Assertions, evidence, and accepted views

The stored unit is an assertion with an immutable identifier, subject, predicate, object, qualifier map, evidence identifiers, prerequisite assertion identifiers, and a decision record. A source snapshot contains its source identifier, version, origin, complete supplied text, and an exact nonempty character span. A content hash binds that representation. Hashes detect changes relative to a known snapshot; they do not authenticate the publisher or prove that its content is true.

The decision record binds the exact proposed assertion to a model identifier, request hash, task distribution, selected outcome, execution mode, and policy version. An accepted view groups equivalent relation representations while retaining their separate supporting assertions. Several sources can therefore support one displayed edge without being collapsed into one supposed independent probability. Evidence and prerequisites within an assertion are conjunctive. Alternative proofs are separate assertions, so withdrawal of one proof need not remove an independently supported edge.

For SciFact, an accepted edge is explicitly `Document -> supports|refutes -> Claim`. It reports a document's relationship to a supplied claim. It is not a directly extracted `Drug -> treats -> Disease` assertion. A refutation does not authorize inventing an opposite biomedical relation. Insufficient-information results and failed model responses create no support or refutation edge, although their candidate nodes and original observations remain available.

For entity matching, original record nodes remain distinct in storage. Accepted `same_as` assertions induce a reversible identity view; accepted `different_from` assertions are cannot-link constraints. No original record is deleted or permanently rewired by identity selection.

### 3.2 Predicate constraints

Each predicate has an explicit domain, range, symmetry flag, optional canonical inverse, incompatible predicates, transitivity annotation, and self-relation policy. Asymmetric relations preserve endpoint order. Declared inverse aliases reverse the endpoints and normalize to their canonical predicate. Symmetric relations canonicalize endpoint order, including after identity mapping. Distinct compatible predicates can coexist on one pair; each still requires a separate accepted judgment.

Incompatibility is checked for the same canonical endpoints and exactly equal qualifier maps. Qualifiers can preserve time, population, modality, or other supplied scope, but this implementation does not infer their meaning or detect partial interval overlap. Unknown predicates and malformed declarations fail closed. A domain/range violation, missing endpoint, disallowed self-loop, or inconsistent identity component rejects the transaction.

Only identity views use equivalence closure. A nonidentity predicate marked transitive does not cause automatic edge generation. Adding a derived relation would require its own assertion and explicit prerequisite links. This restriction avoids silently promoting a schema annotation into newly observed evidence.

### 3.3 Acceptance and transactional publication

Acceptance requires an explicit per-predicate outcome contract and threshold. A high `REFUTES` probability cannot authorize a `supports` edge. Probabilities must have exactly the task's labels, finite values within [0,1], and a sum within the frozen validation tolerance. Missing or malformed distributions are not replaced with neutral values. Synthetic decisions require explicit policy opt-in.

The SQLite implementation serializes writers with `BEGIN IMMEDIATE`. It checks an expected graph version and an idempotency key, applies changes to a candidate state, validates the full active state, and publishes state plus journal entry together. Repeating the same idempotency key and payload returns the original event; changing the payload or policy under that key fails. Injected prepublication failures leave the previous state and journal intact.

The journal links successive state and event hashes. This supports integrity checks within the application's trust boundary, not protection from an administrator capable of rewriting the complete database and its hashes. Authorization and external source authentication remain application responsibilities. Complete JSON snapshots simplify inspection but do not establish production scalability.

### 3.4 Retraction and identity repair

Let R0 contain directly withdrawn assertions and assertions using withdrawn evidence. Retraction computes the least fixed point:

`R(k+1) = R(k) union {a : prerequisites(a) intersect R(k) is nonempty}`.

The store deactivates all assertions in that set atomically and records a reason. Historical assertions and source records remain intact. Identity components are recomputed from active identity assertions, allowing an incorrect bridge to be removed without losing the underlying records. Assertions whose interpretation relied on a selected identity must declare that prerequisite to receive cascading invalidation; undeclared dependencies cannot be recovered automatically.

Schema changes use a separate versioned migration operation with reviewer attribution and a reason. The proposed schema must validate all active assertions. This is a reviewed migration mechanism, not autonomous ontology induction or proof that the stated reviewer was authorized.

## 4. Study design

### 4.1 Immutable inputs and inferential status

The input package is pinned to commit `5b511c88c011524ad6adb71f1d5fa22f3dc941e0`. The current baseline inventory contains 161 files, whose bytes and hashes are checked before replay. Six standalone dataset files are acquired or regenerated through the existing downloader, verified against `scripts/datasets.json`, and remain excluded from Git. The manifest itself is pinned by its Git blob hash. New implementation, reports, and this manuscript are additive; the original manuscript and data are unchanged.

The extension is post-hoc and exploratory. The original outcomes were known before its acceptance analyses were designed. We reuse the original baseline and selected `fewshot_contract` formulations and do not perform additional prompt selection. The selected formulation bundles several request changes; this work does not isolate a causal contribution from demonstrations alone [1].

The archived evaluation contains 413 identity-disjoint DBLP–ACM pairs, including 350 matches and 63 nonmatches, and 339 SciFact claim–abstract pairs across 247 connected evaluation components. Separate original calibration sets contain 390 identity pairs and 150 SciFact rows [1]. These are not newly collected, independently blinded populations. The identity split's class mixture and removal of cross-partition pairs restrict deployment extrapolation.

### 4.2 Binding recorded observations to graph actions

The replay adapter verifies the exact input, requested model, task, formulation, demonstrations, response identifiers, probabilities, and recorded error status. It reconstructs each retained prediction from the original service response. A changed claim, record, evidence payload, or question formulation requires a new decision rather than a cache reuse. Evaluation labels are used only by the metric functions, not by graph construction or action ranking. A negative test changes evaluator gold labels and verifies that graph content and audit hashes remain unchanged.

Recorded outputs are marked `recorded`, not `live`. The extension makes zero new service calls. A separate opt-in adapter can use the archived formulation with an explicitly supplied matching Jev backend and a bounded call budget; its new-inference behavior was tested with mocks, not a live provider.

Four SQLite stores are constructed: baseline and selected formulations for each task. The descriptive argmax policy accepts supported outcome labels without a further confidence cutoff; it is intentionally not presented as a qualified deployment policy. All candidate nodes remain, including isolates. The exported states contain source snapshots, assertion decisions, accepted views, and post-withdrawal histories.

### 4.3 Accuracy, coverage, and uncertainty

For each action class, precision is correct accepted actions divided by accepted actions, recall is correct accepted actions divided by all gold positives, coverage is accepted actions divided by all candidate rows, and conditional false-positive rate is incorrect accepted actions divided by gold negatives. These denominators are not interchangeable.

We report a fixed score grid of 0.5, 0.85, 0.9, 0.95, 0.99, and 1.0 without selecting an evaluation-set optimum. For a matched-count comparison, each arm's predicted primary actions are ranked by their returned probability, then row identifier. Both arms retain the smaller available count. Gold labels do not determine the selected actions.

We jointly resample the original SciFact components or identity-disjoint pair units for 1,000 percentile bootstrap draws with seed 20260918. Intervals describe the difference in selected-minus-baseline precision, conditional on the observed scores and fixed selected sets. They do not repeat prompt development, control every reported comparison, or establish robustness to domain or service changes.

### 4.4 Calibration-only qualification illustration

A separate analysis asks whether any fixed-grid threshold qualifies for a 1% conditional false-positive target using calibration labels only. For independent negative units, one-sided exact binomial upper bounds allocate alpha = 0.05/6 to each threshold. Empty accepted sets do not qualify. Repeated SciFact calibration components invalidate an independent-row qualification, so its computed row bounds are diagnostic only and the policy explicitly abstains.

For identity matching, even a qualified bound would depend on representative sampling and independent confirmation. A low false-positive rate among negatives would still not guarantee high precision when true matches are rare. The illustrative target is not a user-approved operating policy or a guarantee of graph-level risk.

### 4.5 Lifecycle and software evaluation

For each graph, we withdraw the evidence snapshot incident to the greatest number of accepted assertions, resolving ties by source hash without consulting gold. We verify the expected incident removals, preservation of assertion history, durable reopen equality, and audit continuity. These are controlled withdrawals of existing sources, not observations of real scientific retractions.

Separate synthetic tests exercise direction, inverse aliases, symmetry, multi-label compatibility, exact-scope conflicts, provenance tampering, stale versions, schema review, cannot-links, identity splitting, and failure atomicity. Thirty seeded 20-node dependency DAGs compare cascading retraction with an independent set-closure calculation. These controls contribute to software testing, not model-accuracy denominators.

### 4.6 Visual-analysis protocol and denominators

This visual revision was designed after the outcomes were available. It does not preregister a new experiment, introduce a model arm, fit a calibration transform, or select a deployment threshold. `visualize.py` reconstructs evaluation probabilities through the exact-input adapter and cross-checks action counts and operational confusion against the committed graph results. The five-arm comparison reads the separately executed relationship experiment [9]; source hashes, all chart inputs, and figure hashes are recorded in `figures/data.json` and `figures/MANIFEST.json`.

For pooled evidence edges, a correct prediction must match the gold relationship **and its polarity**. Precision divides correct typed edges by accepted typed edges; recall divides them by all 209 gold support/refutation rows; candidate coverage divides accepted typed edges by all 339 rows. A polarity reversal is both an incorrect edge and a missed gold edge. `NOT_ENOUGH_INFO` is a substantive predicted class, `ABSTAIN` is the agreement rule's refusal to label, and `ERROR` is an operational failure. These are separate outcomes even though none commits a support/refutation assertion.

Risk-coverage curves threshold the returned probability of the already predicted action. All equal-score predictions enter together: there is no gold-based ordering, partial tie admission, interpolation to an unobserved zero-risk origin, or assumption that a score of 1 means certainty. Empty accepted sets have undefined precision/risk. These curves are descriptive and must not be optimized on this evaluation set. They differ from the original exact-count bootstrap comparison, which uses deterministic identifier tie-breaking.

Classwise reliability uses all valid responses, including those predicting another class, in ten fixed equal-width bins. Bins are left-closed and right-open, except the final bin includes 1. Empty bins remain missing; marker area is proportional to sample count. Errors stay in operational classification denominators but cannot contribute a nonexistent probability vector. No independent-row error bars are drawn for dependent SciFact observations. Topology plots preserve every candidate node and distinguish component counts from the number of nodes belonging to those components.

## 5. Results

### 5.1 Accepted actions

Table 1 reports the actual assertions before matched-count adjustment. Counts use the original labels, not a new adjudication.

| Task and action | Formulation | Accepted | Correct | Incorrect | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|
| Identity: same | Baseline | 358 | 350 | 8 | 97.77% | 100.00% |
| Identity: same | Selected | 351 | 349 | 2 | 99.43% | 99.71% |
| Evidence: supports | Baseline | 140 | 122 | 18 | 87.14% | 88.41% |
| Evidence: supports | Selected | 118 | 110 | 8 | 93.22% | 79.71% |
| Evidence: refutes | Baseline | 84 | 65 | 19 | 77.38% | 91.55% |
| Evidence: refutes | Selected | 74 | 62 | 12 | 83.78% | 87.32% |

**Table 1.** Argmax action quality. Source: `results/graph-study.json.gz`, per-task `actions.*.argmax` fields.

The selected entity formulation produces fewer incorrect positive identity assertions, with one additional missed match. Its full identity graph includes 351 same and 62 different assertions; three of the total 413 labels are incorrect. The baseline includes 358 same and 55 different assertions, with eight incorrect labels. Overall classification correctness remains 410/413 versus 405/413.

For SciFact, the selected formulation creates 192 support/refutation assertions, of which 172 agree with gold and twenty do not. The baseline creates 224, with 187 correct and thirty-seven incorrect. Thus accepted-label precision rises from 83.48% to 89.58%, but fifteen fewer correct assertions are retained. Overall classification accuracy does not improve: it is 288/339 versus 289/339, with two versus one operational errors. The higher support precision should not be read as a universal relation improvement. Of the baseline's 37 wrong edges, 27 assert a relation for a gold NEI pair and ten reverse support/refutation polarity. The selected arm has thirteen and seven respectively. At the same time, gold-support predictions changed to NEI increase from ten to twenty-two; one additional gold-support row fails operationally. The paired confusion plots in Appendix A retain these omissions instead of scoring all uncommitted candidates as correct rejections.



![Evidence-graph yield for all five existing arms on the same 339 SciFact candidates](figures/01_edge_yield.svg)

**Figure 1.** Evidence-graph yield for all five existing arms on the same 339 SciFact candidates. Incorrect edges are hatched; no-edge outcomes include NEI, failures, and explicit agreement abstentions. A smaller incorrect segment does not imply more correct information was recovered. Source: the frozen relationship experiment [9].



![Typed-edge precision and recall have different denominators](figures/02_precision_recall.svg)

**Figure 2.** Typed-edge precision and recall have different denominators. Recall includes all 209 gold support/refutation rows, whether or not an edge was accepted. The selected and agreement formulations trade recall for precision. These are descriptive points, not statistically separated operating frontiers.

### 5.2 Matched accepted counts

| Primary action | Accepted per arm | Baseline correct / incorrect | Selected correct / incorrect | Precision difference | Exploratory 95% interval |
|---|---:|---|---|---:|---|
| Same identity | 351 | 347 / 4 | 349 / 2 | +0.570 percentage points | [0.000, 1.465] points |
| Supports claim | 118 | 109 / 9 | 110 / 8 | +0.847 percentage points | [-2.708, 4.825] points |

**Table 2.** Score-ranked matched-count comparisons. Both intervals include zero. Source: `matched_primary_action_count` for each task.

The unadjusted support-error count falls from eighteen to eight, but this becomes nine versus eight at equal accepted counts. The matched comparison is a useful limitation on a stronger precision claim. It does not prove equivalence, because its uncertainty still permits differences in either direction. Likewise, the identity matched-count interval does not exclude zero despite its favorable point estimate.



![Precision differences at equal primary-action counts, selected minus baseline](figures/07_matched_precision.svg)

**Figure 3.** Precision differences at equal primary-action counts, selected minus baseline. Identity retains 351 same actions per arm and support retains 118. The original exploratory 1,000-draw intervals include zero; the identity lower endpoint is exactly zero. The intervals condition on fixed score-ranked sets, do not rerank each bootstrap draw, and are not multiplicity-adjusted.

A positive full-classification macro-F1 result and an unresolved selected-edge precision difference are not contradictory: they concern different estimands and acceptance sets. The latter must not be substituted for the former, or vice versa.



![Empirical evidence-edge risk against candidate coverage for the two original formulations](figures/04_relation_risk_coverage.svg)

**Figure 4.** Empirical evidence-edge risk against candidate coverage for the two original formulations. Whole returned-score ties are admitted at each point, and NEI/errors stay in the candidate denominator. The curves cross; they do not establish that one formulation dominates at every coverage. End labels show incorrect/accepted edges, not a false-positive rate among negative examples.

### 5.3 Graph relationships and topology

The identity graphs each preserve 826 record nodes and 413 typed edges. Every weak component contains two records, and there are no isolates. The baseline and selected identity views contain 468 and 475 identity components respectively. This topology is a direct consequence of the identity-disjoint evaluation construction, not evidence of successful large-cluster resolution or resistance to noisy bridges in natural data.

The SciFact candidate graph contains 283 document and 300 claim nodes. All accepted edges are directed from document to claim. The baseline has 224 edges, 362 weak components, and 180 isolates; the selected graph has 192 edges, 394 weak components, and 241 isolates. The largest component contains six nodes in both cases. The maximum in-degree is five and the maximum out-degree four. Preserving isolates makes the coverage loss visible rather than improving apparent connectivity by dropping unconnected candidates.

Neither SciFact arm creates a claim with opposing support/refutation labels from different sources. Consequently, the natural-data replay does not stress conflict resolution. Inverse normalization, multiple predicates on one pair, qualifier-sensitive incompatibility, and multi-step identity repair are established only by the synthetic mechanism tests. Structural metrics describe what is stored; they are not additional factual-accuracy measurements.



![Candidate-node coverage by weak-component size](figures/08_component_coverage.svg)

**Figure 5.** Candidate-node coverage by weak-component size. Both arms retain all 583 nodes; each bar is component size multiplied by component count. Isolates increase from 180 to 241, while nodes in two-node components decrease from 312 to 260. Connectivity is a coverage diagnostic, not an independent semantic-quality score.

The standard directed density reported in the raw graph metrics uses all possible ordered node pairs, whereas this evidence graph only permits Document-to-Claim edges. Density therefore depends on the allowed endpoint types and the supplied candidate universe. It is not meaningful to compare its magnitude directly with a homogeneous identity graph or KARMA's enriched biomedical graph. Neither density nor component growth should be a standalone optimization target.



![An actual SciFact candidate component centered on claim 1274](figures/12_changed_component.svg)

**Figure 6.** An actual SciFact candidate component centered on claim 1274. Arrow labels are baseline / selected / gold; S denotes support, NEI denotes no evidence edge, and ERR denotes a failed response. This component is chosen by the highest prediction-disagreement count, then node count, then stable IDs, without using gold. One gold support is lost and one no-edge classification becomes an error. Candidate arrows show the evaluation relationships, not assertions that every arrow was committed.

### 5.4 Qualification and lifecycle

No arm qualifies an operating threshold for the illustrative 1% false-positive target. The identity calibration has only 56 negative examples for the same-identity action. Even zero errors among all 56 gives a one-sided, six-threshold-adjusted upper bound of about 8.19%. Under the same independent-binomial assumptions, 477 zero-error negative units would be needed to make that bound at most 1%. SciFact qualification is refused because its calibration rows repeat dependency components, not because a row-wise number has been mistaken for a valid certificate.

The raw score endpoint provides a direct caution. Among relation actions returned with probability exactly 1.0, the baseline accepts 125 edges with six errors (4.80% empirical risk), and the selected formulation accepts 73 with five (6.85%). These are descriptive subsets, not independently selected risk policies; the endpoint may reflect provider serialization or score saturation rather than literal internal certainty. Nevertheless, the returned number cannot be treated as a guarantee. Classwise reliability diagrams in Appendix A make the valid-response denominators and concentration of scores visible [8].

Each relation graph's controlled withdrawal deactivates five incident assertions; active counts become 219 and 187. Each identity graph loses one active assertion, leaving 412. Historical assertion counts remain 224, 192, 413, and 413 respectively. Durable reopen and journal checks pass for all four stores. The 30 synthetic dependency-DAG controls also produce exactly the reference retraction closure. These results establish the tested repair behavior, not the accuracy of identifying which source should be withdrawn in an operating system.

### 5.5 Relationship-combination controls and inference inputs

The related experiment combines the two original formulations by equal probability averaging, agreement gating, and a calibration-trained multinomial stacker [9]. It is an already executed post-hoc analysis, not a fresh experiment performed for these figures. Selection of the stacker regularization used grouped calibration cross-validation; its evaluation population had already been inspected. No combined arm is promoted into the graph's production acceptance policy.

Averaging changes macro-F1 from 0.852728 to 0.853759: +0.103 percentage points, with a paired interval of [-1.990, 2.321] points. Agreement reaches 90.00% edge precision by retaining 171 correct and nineteen incorrect edges. At that same 190-edge volume, the selected original arm retains exactly the same correct/incorrect counts. The stacker's macro-F1 is 0.834220, a descriptive deterioration with an interval that includes zero. Higher unfiltered precision therefore cannot be presented as a demonstrated relationship-fusion improvement.



![Existing relationship-combination effects relative to the selected original formulation](figures/14_fusion_effects.svg)

**Figure 7.** Existing relationship-combination effects relative to the selected original formulation. Error bars are 2,000-draw, component-paired 95% percentile intervals from [9], not new error bars fitted by the plotting code. All three intervals include zero; neither improvement nor equivalence is established.

A complete graph-synthesis system must account for candidate discovery, evidence retrieval, inference, validation, persistence, and review. Only historical inference inputs are available here. The generic evaluation uses 258,495 input tokens and the selected evaluation 1,213,458; each combination depends on both sets, totaling 1,471,953 input tokens and 678 source calls. Zero new calls during replay does not mean those inference requirements disappear in a live deployment. The scores are correlated formulations of one model, not independent corroborating sources.



![Historical evaluation input tokens versus correct committed evidence edges](figures/15_recorded_input_cost.svg)

**Figure 8.** Historical evaluation input tokens versus correct committed evidence edges. Two-formulation arms require both original request sets. This figure excludes acquisition, retrieval, storage, review, current token prices, and elapsed latency; it is an inference-input trade-off, not a full-system cost claim.

### 5.6 Reproduction and test execution

All 161 original inventory files retain their bytes. Portable replay reconstructs all 3,644 original predictions from 3,405 recorded calls with zero network attempts. It exposes a pre-existing portability defect: the archived runner interprets Windows source-path strings literally on Linux. The wrapper normalizes those keys only in a temporary runtime manifest and restores the archived manifest before analysis.

Calls, predictions, and calibration artifacts are byte-identical after replay. In the local Python 3.13.5 / NumPy 2.3.5 environment, one derived log-loss value differs by approximately 3.47 × 10^-18. The report records this difference explicitly; the entire results file is not claimed to be byte-identical. Derived JSON comparisons permit only the documented absolute tolerance 10^-14 and relative tolerance 10^-12, while requiring exact structure and integer counts.

The original verification reported 136 passing tests; the graph and relationship extension subsequently expanded its test suite. The visual revision adds explicit controls for denominator preservation, tied scores, probability-bin endpoints, error handling, reversed contrast signs, gold-independent component selection, frozen-summary consistency, and figure integrity. Current execution counts and environments are recorded in CI rather than being inferred from older reports. The graph study is separately executed after the tests and its complete machine-readable result is archived. Every chart can be regenerated from committed inputs without model access. SVG assets are versioned; high-resolution PNGs and the illustrated PDF are reproducible exports. Renderer versions may affect appearance or PDF bytes but do not change the numerical source data. Continuous integration repeats the original replay, original tests, extension tests, and comparison against the committed graph results after pinned dataset acquisition. A successful local execution is not substituted for an unobserved CI result; the PR records the actual CI outcome separately.

## 6. Discussion

The extension demonstrates a useful composition boundary: semantic judgments propose acceptance, while deterministic code validates relationship meaning, dependencies, and publication mechanics. Keeping original assertions and evidence separate from canonical views makes later correction possible without erasing the inputs needed to understand a decision.

The empirical lesson is more qualified. The entity formulation remains a promising component, but natural graph topology is too simple to demonstrate cluster-level behavior. The relation formulation is more selective: it creates fewer wrong edges and fewer right edges. Matching accepted counts substantially reduces its apparent advantage. A graph-synthesis evaluation should therefore report accepted-edge precision, coverage, and downstream effects together rather than optimize a single classifier score or connectivity statistic.

An initial application could maintain publication identity hypotheses and a claim–source evidence graph. Such a system can expose uncertain or conflicting information without automatically promoting it into a canonical statement about the world. A production version would need independently validated candidate retrieval, richer scope modeling, explicit authorization, operational monitoring, and a suitable storage design. The current full-snapshot SQLite implementation is intentionally inspectable rather than scalable.

The optional pairwise identity selector illustrates another boundary. Scores for several candidate identities are not assumed to be a normalized exclusive distribution. The selector requires both an acceptance threshold and a separation margin, and otherwise defers. This behavior is implemented and tested, but the present natural dataset does not measure multi-candidate selection accuracy. Those tests must not be substituted for a new candidate-ranking benchmark.

### 6.1 What the evidence supports for graph synthesis

| Capability | Evidence available here | Interpretation |
|---|---|---|
| Pairwise identity decisions | 413 supplied, identity-disjoint pairs | Promising bounded component; realistic competing candidates and bridge errors remain unmeasured |
| Document-to-claim edges | 339 supplied pairs, 247 evaluation components | Useful evidence-graph representation; precision must be reported with recall and coverage |
| Confidence gating | Frozen score curves and original calibration-only checks | No qualified operating threshold; returned score 1 still permits observed mistakes |
| Relationship contracts and repair | Durable graph replay plus controlled/synthetic tests | Tested mechanism behavior, not proof of semantic truth or automatic source adjudication |
| Relation fusion | Existing five-arm comparison with paired intervals | No resolved gain; additional inference dependencies must be counted |
| Open-corpus graph generation or superiority to KARMA | Not executed | Requires a different, independently adjudicated full-pipeline evaluation |

This assessment does not assign an arbitrary overall readiness score. The missing candidate-retrieval and cluster-level evidence cannot be compensated for by passing more schema tests or by making the existing graph look denser.

## 7. Limitations and next evaluation

The analysis reuses public labels and a known outcome set. It inherits the original study's custom splits, possible benchmark exposure, bundled formulation changes, and selection-conditioned inference. The bootstrap intervals are exploratory; matched-count filtering is not an independently validated policy. The source-withdrawal episodes are interventions we constructed, and the synthetic tests cannot establish general semantic reliability.

No raw-document extraction, unseen ontology discovery, open-corpus retrieval, or fresh Jev service performance is measured. The graph evidence does not justify a numerical superiority claim against KARMA, a specialist matcher, or a conventional constrained-output model. Historical service usage excludes retrieval, extraction, storage, review, and repair costs, and this extension makes no new cost-efficiency claim.

The next semantic study should freeze the acceptance design before examining an untouched corpus. It should include realistic candidate prevalence, difficult negatives, several candidate identities per mention, connected identity components, multi-label predicates, conflicting sources, and explicitly annotated scope. Compare backends with identical candidates and evidence first, then compare complete pipelines. Evaluate at matched accepted coverage and matched total resource budgets. Independently adjudicated downstream query correctness and damage from identity errors would provide stronger graph-level evidence than another isolated-pair score.

## 8. Conclusion

The executed work turns saved Jev decisions into auditable, durable evidence graphs and demonstrates controlled source withdrawal and dependency-aware repair. It also shows why classifier improvements cannot be promoted automatically into broad graph-synthesis claims. At equal accepted action counts, neither primary precision comparison excludes zero, and no threshold qualifies for the illustrative deployment target. The artifact is a tested foundation for a bounded graph pilot and a more discriminating next experiment, not a completed autonomous knowledge-graph system.

## Reproducibility and evidence availability

Code, protocol, relationship analysis, test sources, result tables, and full compressed JSON are included in `graph_synthesis/`. `CLAIM_EVIDENCE.md` maps numerical and implementation claims to their exact fields or tests. `README.md` provides portable replay and graph-export commands. The original archive is retained unchanged. Dataset and code redistribution rights remain subject to the original package notices; this extension supplies no new determination of third-party rights. No API credentials or model weights are included.

## Appendix A. Diagnostic figures

These diagnostics use the same frozen populations as the main text; they are not additional independent experiments. The figure gallery includes the precise binning, denominators, and source-field notes, with machine-readable values in `figures/data.json`.


![Same-identity acceptance risk versus all 413 candidate pairs](figures/03_identity_risk_coverage.svg)

**Figure A1.** Same-identity acceptance risk versus all 413 candidate pairs. All tied scores enter together; different_from assertions are excluded from this particular action curve. A zero-error observed subset is not a 1% population-risk certificate.



![Baseline operational SciFact confusion](figures/05_confusion_baseline.svg)

**Figure A2.** Baseline operational SciFact confusion. Each cell shows its count and percentage within the gold row, including an explicit ERROR column. Gold support, refutation and NEI denominators are 138, 71 and 130.



![Selected-formulation confusion with identical axes, row normalization and denominators](figures/06_confusion_selected.svg)

**Figure A3.** Selected-formulation confusion with identical axes, row normalization and denominators. More correct NEI labels occur alongside more missed gold-support edges; a classifier and an accepted-edge metric need not improve together.



![Classwise raw P(same) reliability across all 413 valid responses per arm](figures/09_identity_reliability.svg)

**Figure A4.** Classwise raw P(same) reliability across all 413 valid responses per arm. Marker area is proportional to bin count. Fixed bins retain empty cells as missing; the diagonal is a reference, not a fitted calibration function.



![Classwise raw P(SUPPORTS) reliability, including responses whose predicted class is not support](figures/10_support_reliability.svg)

**Figure A5.** Classwise raw P(SUPPORTS) reliability, including responses whose predicted class is not support. Probability diagnostics have 338 baseline and 337 selected valid rows; operational metrics still have 339. Scores are not treated as independent calibrated Bernoulli probabilities.



![Classwise raw P(REFUTES), using the same ten fixed bins and valid-response counts](figures/11_refute_reliability.svg)

**Figure A6.** Classwise raw P(REFUTES), using the same ten fixed bins and valid-response counts. Sparse bins and repeated SciFact components limit inferential interpretation. No probability refitting is performed.



![Assertions active and deactivated after the controlled source-withdrawal episode](figures/13_source_withdrawal.svg)

**Figure A7.** Assertions active and deactivated after the controlled source-withdrawal episode. All historical assertions remain stored. Identity totals include both same_as and different_from; source-to-claim graph totals include supports and refutes. Audit and durable-reopen checks concern software behavior, not factual validity.

## References

[1] Gregg, Timothy Wayne. *Improving Typed Entity Decisions with Jev: A Reproducible Same-Model Case Study*. Original research package, commit `5b511c88c011524ad6adb71f1d5fa22f3dc941e0`, 2026. `../manuscript/paper.md`; original methods and data supplements in `../supplementary/`.

[2] Lu, Yuxing; Wu, Wei; Zhao, Xukai; Peng, Rui; and Wang, Jinzhuo. *KARMA: Leveraging Multi-Agent LLMs for Automated Knowledge Graph Enrichment*. arXiv:2502.06472v2, 11 January 2026. https://arxiv.org/html/2502.06472v2.

[3] Wadden, David; Lin, Shanchuan; Lo, Kyle; Wang, Lucy Lu; van Zuylen, Madeleine; Cohan, Arman; and Hajishirzi, Hannaneh. *Fact or Fiction: Verifying Scientific Claims*. EMNLP, 7534–7550, 2020. https://doi.org/10.18653/v1/2020.emnlp-main.609.

[4] Li, Yuliang; Li, Jinfeng; Suhara, Yoshihiko; Doan, AnHai; and Tan, Wang-Chiew. *Deep Entity Matching with Pre-Trained Language Models*. Proceedings of the VLDB Endowment, 14(1), 50–60, 2020. https://doi.org/10.14778/3421424.3421431. The PDF reference block uses 2021; the original package bibliography records the publisher-metadata distinction.

[5] TypeSafe AI. *API Reference*. Official vendor documentation, accessed 17 September 2026, America/New_York. https://docs.typesafe.ai/api. Interface documentation is not independent evidence of task accuracy.

[6] W3C. *Shapes Constraint Language (SHACL)*. W3C Recommendation, 20 July 2017. https://www.w3.org/TR/shacl/.

[7] W3C. *PROV-O: The PROV Ontology*. W3C Recommendation, 30 April 2013. https://www.w3.org/TR/prov-o/.


[8] Guo, Chuan; Pleiss, Geoff; Sun, Yu; and Weinberger, Kilian Q. *On Calibration of Modern Neural Networks*. ICML, PMLR 70:1321–1330, 2017. https://proceedings.mlr.press/v70/guo17a.html.

[9] Gregg, Timothy Wayne. *Relationship-edge improvement experiments: executed frozen-response comparison*. Repository report, 2026. `../experiments/relationships/README.md`; protocol, fitted model, and compressed reference results accompany the report. This internal experiment is not an independent external replication.

## Complementary evidence analysis

The [ten-figure evidence paper](EVIDENCE_PAPER.md), [visual analysis](VISUAL_ANALYSIS.md), and [claim-to-evidence mapping](EVIDENCE_CLAIM_EVIDENCE.md) preserve the independently developed analysis from main. Its figures and exact source data reside in `evidence_figures/`, with a separate generator and verification workflow.
