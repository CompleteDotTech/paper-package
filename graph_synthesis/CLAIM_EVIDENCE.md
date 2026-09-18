# Claim-to-evidence map

The paper reports a post-hoc transformation of original observations, not independent model replication. All JSON paths below refer to the decompressed `results/graph-study.json.gz` unless noted. Reproduce with `python -B -m graph_synthesis.study --output ../graph-study.json`; compare parsed JSON with the strict structure and roundoff policy in `verify.compare_json`.

| Claim | Evidence | Boundary |
|---|---|---|
| Original archive unchanged | `results/local-verification.json: archive_files_verified=161, original_files_changed=0`; `recorded.inventory` pins the MANIFEST Git blob; every original file is hashed | New additive files are outside the baseline inventory; six separately hash-verified datasets remain ignored |
| Reconstructed original calls and predictions | Local verification `replay.calls=3405`, `replay.predictions=3644`; `verify.py` executes original raw-response audit and runner | Replay is not fresh inference |
| Exact observation equality with tiny derived roundoff | Local verification `replay.artifacts`; the sole local float difference is explicitly listed | Do not claim entire `results.json` is byte-identical |
| 136 original tests, 60 new tests, zero skips | Local verification `original_tests`, `extension_tests`; CI also runs both suites | 30 randomized DAG controls occur within one test, not 30 extra test methods |
| Fewer entity match errors | `tasks.entity_resolution.*.actions.same.argmax` | Pairwise record decisions on 413 identity-disjoint examples |
| Higher support precision at lower recall | `tasks.relation_support.*.actions.SUPPORTS.argmax` | Supplied document-to-claim judgments, not extracted biomedical predicates |
| Refutation performance | `tasks.relation_support.*.actions.REFUTES.argmax` | No opposite biomedical relation is invented |
| Matched-coverage intervals include zero | `tasks.*.matched_primary_action_count` | 1000 exploratory paired bootstrap draws; no claim of equivalence or confirmatory superiority |
| Graph topology and type relationships | `tasks.*.*.graph.metrics`, including `node_type_counts`, `relation_endpoint_type_counts`, `weak_component_size_histogram`, `isolates` | Storage-convention statistics, not truth or independently measured graph utility |
| Four successful source-withdrawal episodes | `tasks.*.*.graph.lifecycle` | Controlled incident-source withdrawals; no naturally observed retractions |
| No 1% threshold qualified | `tasks.*.*.actions.*.calibration_policy` | SciFact fails independent-unit eligibility; identity fails finite-sample bounds |
| Evidence-bound, polarity-correct acceptance | `core.py`, `recorded.py`; tampering and polarity tests in `tests/` | Hash binding is not source authentication or protection against a malicious database owner |
| Directed, inverse, symmetric, multilabel and scoped relationships | `core.Relation`, `normalize`, `_validate`; named relation tests in `test_core.py` | Qualifiers match literally; no complete interval algebra, ontology induction, SHACL, or OWL engine |
| Reversible identity and dependency repair | `GraphStore.retract`, `view`, `_clusters`; cannot-link, split, independent-proof and randomized-DAG tests | Large real-world identity components and new relation domains remain unmeasured |
| Source and service separation | `fresh_model_calls=0`; execution modes tested in `test_research.py` | Optional fresh-inference adapter was exercised with mocks only |
| KARMA design comparison | `RELATIONSHIPS.md`, paper Reference 2; arXiv:2502.06472v2 Sections 3.7–3.10 and 4.3 | No KARMA execution or score-for-score benchmark win |

## Review and unperformed extensions

Human reviewers should check the model/input interpretation, numerical conclusions, evidence redistribution permissions, and final authorship statements before publication. The automated review consists of explicit negative tests, invariant checks, source/hash auditing, and matched-coverage reanalysis; it is not independent scholarly peer review. Untouched-corpus extraction, independently adjudicated labels, large-cluster inference, fresh temporal replication, production latency/load, and a matched-input KARMA execution remain future experiments, not completed claims.
