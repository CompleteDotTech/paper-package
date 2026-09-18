# Synthetic compiler mechanism results

These are controlled offline examples with predetermined predictions and gold labels. They demonstrate implementation behavior; they do not estimate performance on a real population.

## Frozen-score graph quality

Both policies receive the same seven candidates. The baseline deliberately applies positive edges from high max-class confidence without interpreting polarity. It is a diagnostic comparator, not a historical graph benchmark.

| Comparison | Policy | Commits | False commits | Precision | Positive recall | Coverage |
|---|---|---:|---:|---:|---:|---:|
| same_candidate_pool | confidence_only_positive | 6 | 3 | 0.500 | 0.750 | 0.857 |
| same_candidate_pool | typed_actions | 3 | 1 | 0.667 | 0.500 | 0.429 |
| matched_committed_count | confidence_only_positive | 3 | 2 | 0.333 | 0.250 | 0.429 |
| matched_committed_count | typed_actions | 3 | 1 | 0.667 | 0.500 | 0.429 |

The matched-count baseline takes the three highest max-class confidences using a fixed ID tie-break. The typed policy still commits one semantically false edge and misses correct edges; deterministic verification does not establish truth.

## Actual graph-state scenarios

| Scenario | Status | New commits | Graph/provenance unchanged | Reason |
|---|---|---:|---|---|
| positive_valid | committed | 1 | False | Valid control |
| referential_failure | rejected | 0 | True | Unresolved edge dependency: ab; No valid mutations: Unresolved edge dependency: ab |
| domain_type_failure | rejected | 0 | True | Constraints did not pass: domain |
| unique_property_failure | rejected | 0 | True | Constraints did not pass: unique |
| cardinality_failure | rejected | 0 | True | Constraints did not pass: one |
| self_loop_failure | rejected | 0 | True | Constraints did not pass: no_self_loops |
| unsupported_rule | rejected | 0 | True | Constraints did not pass: unknown |
| stale_version | conflict | 0 | True | Expected v0; current v1 |
| apply_failure | rejected | 0 | True | Injected failure during shadow application |
| idempotent_replay | committed | 0 | True | Existing transaction replayed without applying again |
| retry_payload_conflict | conflict | 0 | True | Idempotency key reused with a different payload |

Every scenario asserts the actual node/edge/provenance/version snapshot. Failure injection occurs after the first shadow mutation; no partial state is published. Retry coverage here counts newly applied mutations, so a correct replay reports zero new commits. The JSON contains frozen inputs, source-score hash, counts, constraint outcomes, and invocation counts.

Reproduce: `python -B -m pgc.experiments.run_compiler_research`.
