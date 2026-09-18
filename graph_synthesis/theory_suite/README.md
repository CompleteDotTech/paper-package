# Jev graph-theory experiment suite

This standard-library package executes ten exploratory hypotheses, not ten claims of success. It reads the same pinned requests and responses through `RecordedJev`, which verifies their original hashes. It never changes old data or promotes a policy into the default compiler.

## Reproduce

Run from the repository root, with Python 3.12 or newer:

```bash
python -B -m unittest discover -s graph_synthesis/theory_suite/tests -v
python -B -m graph_synthesis.theory_suite.run --check
```

No external packages, credentials, datasets to download, or network calls are required for this suite. The runner blocks socket construction while executing the experiments. Existing repository-wide replay workflows separately acquire the pinned public datasets needed by the older study.

To deliberately regenerate the new outputs after a reviewed source change:

```bash
python -B -m graph_synthesis.theory_suite.run
```

`--output PATH --report PATH` writes an external JSON/Markdown pair; `--check` compares rather than overwrites. Stable source hashes cover the three imported original modules and all new Python sources/tests. Result values are rounded to ten decimal places for portable comparison; original observations are not rounded or modified. The synthetic identity-world trace digest uses eight-decimal objective gains. No wall-clock timing or environment-dependent timestamps enter the result.

## Files and evidence boundaries

| File | Purpose |
|---|---|
| `PROTOCOL.md` | Pre-execution commitments, fixed thresholds, targets, evidence classes and primary references. This is NOT independent preregistration. |
| `methods.py` | Gold-free inference methods; explicit calibration-only fitting; bounded exact decoding; isolated query preview. |
| `analyses.py` | T01–T06: source grouping, strict score replay, projections and counterfactual policies. |
| `controlled.py` | T07–T10: conditional score resampling, cache simulation and actual GraphStore fixture execution. |
| `run.py` | Offline execution, source hashes and result-derived Markdown reporting. |
| `tests/test_methods.py` | Numerical, leakage, invalid-input, deterministic, retraction and migration checks. |
| `results.json` | Executed counts, selection grids, descriptive intervals, simulation assumptions and source hashes. |
| `RESULTS.md` | Generated interpretation, including null findings and adverse graph outcomes. |

## Meaning of the ten hypotheses

**T01 — Set-valued mutation contracts.** Instead of accepting a single argmax answer, compute a calibrated label set and emit only a singleton positive edge. This separates classification from permission to mutate a graph. The error/retention target and nominal prediction-set coverage are different endpoints; neither can replace the other.

**T02 — Residual-dependence ceiling.** Two prompts against the same model may share the same difficult mistakes. Measuring double faults shows whether redundant checking resembles independent evidence. A gold-informed perfect router is only an upper bound on what any router between the two recorded answers could achieve.

**T03 — Base-rate transport.** An edge verifier measured on an enriched positive-pair benchmark can behave very differently during broad candidate search. The fixed-rate Bayes projection isolates that mechanism without inventing deployment observations. Missing candidates and a changing negative mixture are additional, unmeasured limitations.

**T04 — Composed mutation risk.** Local scores do not automatically certify the probability of any wrong edge in a component. A sum of per-edge error bounds can control family risk only when those inputs are valid conditional bounds. This experiment deliberately tests the raw-score substitution rather than assuming it is justified.

**T05 — Graph-sensitive review value.** A doubtful edge near many others can matter more than an isolated doubtful edge. The experiment fixes a review budget and tests uncertainty times observed local impact. A null result on sparse pair graphs does not establish that topology is useless on dense graphs.

**T06 — Cost/quality routing.** Cheap baseline-first decisions can route uncertainty to a more expensive formulation. Calibration chooses the route, while evaluation measures both classification and graph-edge costs. Similar macro-F1 can conceal substantially more wrong accepted edges; token savings alone are not sufficient.

**T07 — Joint identity consistency.** Pair scores can be decoded as a globally consistent partition rather than accepted greedily. Exact partition optimization is intentionally bounded to at most seven nodes. The experiment tests six-node score-resampled worlds; its optimality is mathematical, while semantic improvement is empirical only within that simulation.

**T08 — Dependency-complete cache validity.** A reusable decision depends on evidence, the model/question/schema/policy and graph queries, including queries that returned nothing. New facts can invalidate an earlier absence result. The digest oracle tests cache bookkeeping, not whether dependency discovery is complete in a real corpus.

**T09 — Alternative sufficient proofs.** Conjunctive requirements inside one proof and disjunctive alternative proofs must be preserved separately. The existing GraphStore can represent this as multiple assertions for one visible edge, including downstream alternatives. Exhaustive withdrawal tests verify the representation with hand-specified truth.

**T10 — Observable schema contracts.** A migration can remain type-valid yet change query answers because symmetry and inverse relationships change meaning. An isolated database preview checks a finite query contract before accepting the migration. It does not prove equivalence for future nodes, qualified queries, or arbitrary paths.

## Interpretation and limits

T01–T06 reuse 752 historical evaluation examples, not new unseen data. Calibration/evaluation source components are checked and overlaps would be purged, but the old formulation was already selected using the original calibration data. Statistical intervals are descriptive, paired by source component, and not corrected for a family of confirmatory hypotheses. T07–T10 are not measurements of new Jev behavior.

No claims of full-document relation extraction, open-world entity discovery, graph completeness, qualified biomedical truth, novel mathematics, or superiority over KARMA are warranted. Keep hypotheses, implementation invariants, simulations, and fresh empirical model evidence separate. A future confirmation requires newly adjudicated source-disjoint data and fixed policies before collecting fresh model outputs.
