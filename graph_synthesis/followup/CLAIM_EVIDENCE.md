# Claim-to-evidence ledger

| Claim | Evidence location | Permitted interpretation | Excluded interpretation |
|---|---|---|---|
| Guarded calibration primary target fails | `results.json:H1.tasks.relation_support.fewshot_contract` | Guard chooses zero mixture weight; raw probabilities retained | Calibration generally cannot help |
| Edge-aware routing saves 63.52% input tokens with 173 correct / 19 wrong edges | `results.json:H2.tasks.relation_support.runs.rerun` | Fixed original-calibration policy, captured-response replay; two labels differ from all-few-shot | Newly measured latency, lower invoice, independent replication, or universal optimality |
| Stability does not beat matched confidence | `results.json:H3.tasks.relation_support.fewshot_contract` | 18 versus 17 wrong edges at 188 accepted; five stable wrong edges score one | Repeat agreement is independent corroboration |
| Interval/scope guard passes finite oracle | `results.json:H4` | 5,408 supported pairs, no missed or false conflicts; five unknown cases staged | New scientific facts extracted correctly or unrestricted temporal logic solved |
| Lineage bounds resist duplication under correct metadata | `results.json:H5` | 1,536 configurations, zero bound violations; 628 naive false admissions avoided, at cost of 28 high-probability admissions | Raw model confidence is a calibrated probability or shared provenance can be inferred reliably |
| Corrupted metadata defeats the bound | `results.json:H5.negative_control` | Independence and lineage assumptions are necessary | The method validates those assumptions itself |
| Frozen evidence unchanged | `graph_synthesis.verify` and CI logs | 161 original files hash-verified | External scientific peer review |

Primary empirical targets refer to the rerun relation few-shot comparison; entity and baseline-arm results are diagnostics. H1 confidence intervals are descriptive and unadjusted. H2 paired rate-difference intervals are descriptive sensitivity summaries, not a preregistered equivalence test. The engineering target uses aggregate counts, not per-example identity. The primary indicators must not be combined into a discovery percentage.

No new Jev service requests, new independent labels, full-paper extraction benchmark, external-system/KARMA run, human review study or deployment-risk certificate was executed. AI-assisted internal code/evidence review is not independent peer review.
