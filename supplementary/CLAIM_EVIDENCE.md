# Claim-to-evidence map

This map distinguishes completed measurements from proposed research. Paths are relative to this supplementary directory. The [manuscript](../manuscript/paper.md) is an empirical case-study draft; the saved raw artifacts remain the evidence of record.

| Claim | Evidence | Allowed interpretation | Boundary |
|---|---|---|---|
| The selected entity formulation improves operational macro-F1 on the fixed evaluation split. | `results.json → tasks.entity_resolution.evaluation_comparisons.raw.metrics.macro_f1`; [report](../reproduction/results/jev/run-20260918/RESULTS.md). | Baseline 0.96045198, selected 0.98586020; selected-minus-baseline interval [0.00096011, 0.05396393]. | Exploratory unadjusted paired interval; one split; conditional on selection. |
| False-positive identity predictions decrease. | Same report; entity evaluation confusion in `results.json`. | Eight of 63 negative pairs versus two of 63; true-match misses increase from zero to one among 350 positives. | These are pair predictions, not executed merges or measured cluster damage. |
| The intervention is a bundle. | [Frozen plan](../reproduction/results/jev/run-20260918/plan.json), `question_specs` and task demonstrations. | Noul baseline versus Choice with explicit identity criteria, refined instructions, and six training demonstrations. | Cannot attribute the gain to demonstrations alone; unselected no-demo variants lack held-out measurements. |
| The same intervention does not establish a SciFact classification improvement. | SciFact evaluation comparisons in [report](../reproduction/results/jev/run-20260918/RESULTS.md). | Macro-F1 changes 0.8508 to 0.8527; interval spans zero. | Neither proof of equivalence nor proof the formulation is always worse. |
| The task-level conclusions survive a common-success analysis. | [Sensitivity artifact](../reproduction/results/jev/run-20260918/common_success_sensitivity.json). | Entity uses all 413; SciFact common-success 336 has macro-F1 delta 0.00327, interval [−0.02863, 0.03526]. | Removing failures changes the population and is sensitivity analysis, not a replacement primary metric. |
| Calibration has mixed effects. | [Calibration fit](../reproduction/results/jev/run-20260918/calibration.json) and raw/calibrated evaluation scores in report. | Entity Brier and log loss improve within each arm; SciFact log loss improves but Brier worsens. | Scalar fitting does not prove risk control and does not explain label accuracy gains. |
| Evaluation identity/component isolation was checked. | Plan data manifests and [independent verification](../reproduction/results/jev/run-20260918/verification.json). | 413 identity-disjoint entity pairs; 339 SciFact rows in 247 components; demos and development excluded from held-out components. | Hash identity and positive-label components reflect this dataset's grouping assumptions; split selection changes class mixture. |
| Replay is exact from recorded outputs. | [Replay verification](../reproduction/results/jev/run-20260918/replay_verification.json). | All 3,644 predictions reconstructed with HTTP disabled; saved result and calibration artifacts matched byte-for-byte under the recorded original manifest. | No evidence of fresh-service determinism; routine replay may update the copied manifest's provenance. |
| Selected labels were stable in the fresh panel. | `results.json → repeatability`; raw [call journal](../reproduction/results/jev/run-20260918/calls.jsonl). | Each selected arm has 20/20 examples with the same label across three distinct calls. | Only 20 examples/task, immediate repeat window; probabilities vary; provider internals unobserved. |
| The full run has low measured provider usage. | `results.json → usage`; call journal and manifest. | 3,405 HTTP attempts, 4,792,778 input tokens; $0.2013 at the documented rate. | Estimated charges, not an invoice; not total system cost or comparative efficiency evidence. |
| Numerical contract failures are preserved. | Verification `service_errors`; call journal; prediction journal. | Five requests violate normalization and remain failed. | A typed interface does not ensure every answer meets a stricter probability contract. |
| Original fixtures are diagnostic. | Plan `fixtures` and report fixture rows. | Entity 84/88 to 87/88 eligible; relation 46/50 to 45/50; 12 uncertain entity cases excluded. | Prior development history and no independent adjudication prevent confirmatory use. |
| All planned phases completed. | `results.json → completeness`; verification `phase_counts`. | Every frozen phase observation is present, including repeats and batching controls. | Completeness of this study is not completion of the broader graph-compiler research program. |

The abbreviated `results.json` paths above refer to [the saved machine-readable analysis](../reproduction/results/jev/run-20260918/results.json). A journal citation identifies measured service behavior; source documentation identifies the meaning of API fields, not correctness of that behavior.

## Claims deliberately not supported

- Jev outperforms Ditto, NLI, conventional LLMs, KARMA, or another model family under a matched comparison.
- Demonstrations alone cause the entity improvement.
- Choice is universally better than Noul.
- The entity score is an official DBLP–ACM leaderboard score or representative of all candidate-pair populations.
- SciFact results measure retrieval, rationale extraction, unrestricted relation extraction, world truth, or medical correctness.
- Three fresh calls establish long-term stability, immutable service weights, or bitwise determinism.
- Low recorded charges establish end-to-end graph-construction cost savings.
- A pairwise false-positive rate is a validated automatic-merge policy, cluster consistency guarantee, or transaction-level risk bound.
- Passing implementation tests constitutes independent scientific replication.
- A locally frozen protocol is an externally registered or fully blinded experiment.

## Before submission

The manuscript needs author review and accurate authorship/disclosure metadata, venue-specific framing, attribution and release checks, and a durable artifact identifier. Stronger generalization claims additionally need a new untouched evaluation population, controlled component ablations, relevant model baselines, and independent replication. Those missing measurements cannot be supplied by rewriting the present report. See [submission readiness](SUBMISSION_READINESS.md) for the detailed completion list.
