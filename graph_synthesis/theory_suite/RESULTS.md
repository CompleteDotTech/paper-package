# Ten Jev graph-synthesis hypotheses: executed results

This is exploratory reanalysis of archived Jev observations plus controlled systems experiments. **No new Jev service calls were made.** A met target is not a proven general theory. The original study and default compiler are unchanged.

Requested archived model: `jev-1.13.0`. Baseline commit: `2c5184390bfa63740b44fb556a270418a6c1d882`. Seed: 20260918; paired component bootstrap replicates: 500.

## Calibration and evidence separation

Components use shared record IDs or claim/document IDs, not labels. Calibration components touching evaluation are purged. The earlier formulation selection already used the original calibration set: this purge does not retroactively create independent conformal calibration.

| Task | Original calibration | Retained | Purged | Retained components | Evaluation rows / components |
|---|---:|---:|---:|---:|---:|
| relation_support | 150 | 150 | 0 | 73 | 339 / 247 |
| entity_resolution | 390 | 390 | 0 | 390 | 413 / 413 |

## Findings

### T01: Group-conformal mutation contracts

**relation_support:** wrong emitted edges 20 → 14; correct edges 172 → 143; retention 83.14%. Singleton contract accepted 157 edges. Label-set coverage 92.04%; all-label component coverage 89.88%; target met: **True**. Calibration quantile 0.880000 from 73 groups.
**entity_resolution:** wrong emitted edges 2 → 0; correct edges 349 → 304; retention 87.11%. Singleton contract accepted 304 edges. Label-set coverage 85.71%; all-label component coverage 85.71%; target met: **True**. Calibration quantile 0.010000 from 390 groups.
Entity label-set coverage is below the nominal 90% level even though the error/retention target is met. This is a warning against interpreting this retrospective construction as a valid coverage guarantee. Relation singleton precision can also be worse than full-coverage precision: report correct-edge loss, not just fewer errors.

### T02: Correlated verification errors

**relation_support:** 34 double faults versus 7.522 expected under independence. Excess probability 0.0781, descriptive 95% component-bootstrap interval [0.0547724792, 0.1002166706]. Perfect-router accuracy upper bound 89.97%; best observed arm 85.25%. Positive excess: **True**; interval excludes zero: **True**. The oracle uses gold and is not an implementable router.
**entity_resolution:** 2 double faults versus 0.058 expected under independence. Excess probability 0.0047, descriptive 95% component-bootstrap interval [-4.69018e-05, 0.0117899501]. Perfect-router accuracy upper bound 99.52%; best observed arm 99.27%. Positive excess: **True**; interval excludes zero: **False**. The oracle uses gold and is not an implementable router.

### T03: Rare-edge prior sensitivity

**relation_support / baseline_choice:** observed SUPPORTS precision 87.14%; projected precision at 1% prevalence 9.07%. False positives 18 / 201 negative examples. At least 10-point drop: **True**.
**relation_support / fewshot_contract:** observed SUPPORTS precision 93.22%; projected precision at 1% prevalence 16.83%. False positives 8 / 201 negative examples. At least 10-point drop: **True**.
**entity_resolution / baseline_noul:** observed same precision 97.77%; projected precision at 1% prevalence 7.37%. False positives 8 / 63 negative examples. At least 10-point drop: **True**.
**entity_resolution / fewshot_contract:** observed same precision 99.43%; projected precision at 1% prevalence 24.09%. False positives 2 / 63 negative examples. At least 10-point drop: **True**.
These are Bayes-rule sensitivity projections, not deployment measurements. Conditional errors and the negative-class mixture are assumed unchanged; finite-sample uncertainty is not propagated into this grid.

### T04: Composed graph-risk budgets

**relation_support:** fixed gate accepts 130 edges (9 wrong); component budget accepts 130 (9 wrong). Any-error component frequency 8.41%; correct-edge retention 100.00%; target met: **False**. 5 wrong positive edges carry confidence exactly one.
**entity_resolution:** fixed gate accepts 323 edges (0 wrong); component budget accepts 323 (0 wrong). Any-error component frequency 0.00%; correct-edge retention 100.00%; target met: **True**. 0 wrong positive edges carry confidence exactly one.
The budget and fixed gate select the same number of edges on these sparse observed graphs; this does not establish an advantage from composition. The union-bound arithmetic is not the problem: unvalidated Jev scores are not certified conditional error probabilities. A point-estimate pass is not a graph-safety certificate.

### T05: Topology-aware review value

**relation_support:** review budget 20 of 192 edges. Clean correct-edge neighborhoods: initial 168, uncertainty review 169, topology-aware 169, random mean 168.383. Strict topology advantage: **False**.
**entity_resolution:** review budget 36 of 351 edges. Clean correct-edge neighborhoods: initial 349, uncertainty review 349, topology-aware 349, random mean 349.000. Strict topology advantage: **False**.
This is a perfect equal-cost reviewer counterfactual on the observed sparse candidate graph; no reviewer or additional model was run. Missing candidate edges cannot be repaired by this experiment.

### T06: Calibration-selected decision cascades

**relation_support:** calibration-selected threshold 0; escalations 1 / 339. Macro-F1 0.852728 → 0.852408; difference -0.000320. Hypothetical input tokens 1,213,458 → 262,102; saving 78.40%; joint cost/quality target met: **True**.
**entity_resolution:** calibration-selected threshold 0; escalations 0 / 413. Macro-F1 0.985860 → 0.960452; difference -0.025408. Hypothetical input tokens 627,844 → 174,370; saving 72.23%; joint cost/quality target met: **False**.
For graph synthesis the relation cascade changes wrong emitted edges 20 → 37 and accepted-edge precision 89.58% → 83.48%. Therefore a macro-F1/cost target pass is NOT evidence that it is the better graph policy. Inspect edge metrics as well as classification averages.
All baseline-first input tokens are charged, including those preceding a fallback. These are recorded single-decision token counts, not measured new service latency or invoices.

### T07: Joint identity decoding

**baseline_noul:** 256 synthetic six-node worlds. Greedy → exact: false merges 19 → 2; missed matches 7 → 0. Strict objective improvements in 8 worlds; greedy order sensitivity in 16. Truth-level target met: **True**.
**fewshot_contract:** 256 synthetic six-node worlds. Greedy → exact: false merges 0 → 0; missed matches 0 → 0. Strict objective improvements in 0 worlds; greedy order sensitivity in 0. Truth-level target met: **False**.
Synthetic six-node truths; independent conditional pair-score draws from purged calibration. Not Jev predictions on synthetic texts or a scalable solver. Objective optimality must not be confused with correctness of synthetic pair truth. The fixed small worlds test an architectural mechanism, not full-corpus scalability.

### T08: Dependency-complete semantic caching

50,500 simulated lookups across 500 decisions and 101 epochs.

| Cache key | Hits | Stale hits | Recomputations |
|---|---:|---:|---:|
| input_only | 50000 | 39496 | 500 |
| missing_absent_query_generation | 48399 | 5246 | 2101 |
| global_generation | 0 | 0 | 50500 |
| complete_dependencies | 47899 | 0 | 2601 |

Target met: **True**. Complete fingerprint equals the specified oracle by construction. Correct dependency discovery and actual Jev output reuse remain untested.

### T09: Alternative-proof survival

Actual GraphStore execution of all 16 withdrawal subsets for Q=((s0 AND s1) OR s2) AND s3:
alternative_proofs: 0 false removals, 0 false retentions.
flattened_AND: 4 false removals, 0 false retentions.
flattened_OR: 0 false removals, 10 false retentions.
Target met: **True**. The sufficient-proof clauses are supplied by the fixture; their extraction from scientific text is not tested.

### T10: Observable schema-migration contracts

8 type-valid controlled migrations, including 4 that change finite query answers. Type-only gate accepts all 4 drifting migrations; preview query gate accepts 0; benign false rejections 0. Original database unchanged: **True**. Target met: **True**. Only finite unqualified single-edge queries over existing nodes; not future-data equivalence or semantic truth.

## Scientific interpretation and next validation

Treat Jev as an evidence-bound local decision component, not as a source of automatically valid global graph probabilities. Joint decoding, abstention, routing, caching, lineage, and migration contracts operate at different layers and require separate evaluation. Do not count controlled invariant passes as accuracy improvements or combine the ten endpoints into a single success rate.

T01–T06 reuse the same historical observations and are exploratory. T07 resamples historical scores onto synthetic truths; T08 uses a digest oracle; T09–T10 use hand-specified source logic and schema queries. There are no fresh full-paper extraction results, externally adjudicated new labels, qualified biomedical relation tests, model-drift measurements, or matched KARMA comparisons. A confirmatory follow-up needs a newly collected, source-disjoint corpus; fixed prompts, calibration and cost policies; document-level human edge/qualifier adjudication; repeated fresh service measurements; and multiplicity-aware primary endpoints.

All methods and thresholds are specified in [PROTOCOL.md](PROTOCOL.md). Exact counts, token grids, synthetic cases, source hashes and assumptions are in [results.json](results.json). Reproduce with `python -B -m graph_synthesis.theory_suite.run --check` and `python -B -m unittest discover -s graph_synthesis/theory_suite/tests -v`.
