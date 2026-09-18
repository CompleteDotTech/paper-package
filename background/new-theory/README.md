# New theory: preserve uncertainty through graph compilation

**Current work: [improving Jev itself](JEV_IMPROVEMENT_STUDY.md).** The earlier specialist/compiler execution below supplied supporting infrastructure, but did not test Jev's improvement. The current study returns to that decision-layer gate with a fixed Jev version, real API responses, and repeatability checks.

Research notes created 2026-09-17 for [typed-probabilistic-graph-compiler](../typed-probabilistic-graph-compiler/). The initial notes below describe hypotheses grounded in a read-only baseline audit; the source repository was unchanged at that stage. The subsequently authorized implementation and experiment stages are now complete. See [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) and the [executed results report](../typed-probabilistic-graph-compiler/RESULTS_REPORT.md).

**Central hypothesis:** graph quality should improve when the compiler preserves the meaning, evidence, and dependencies of uncertain decisions, then selects mutations according to their consequences. The clearest research target is more correct accepted graph updates at matched coverage and cost.

The baseline needs repair before testing that hypothesis. The saved 68% ER result includes 12 uncertain examples automatically marked correct; exact label matching gives 56%, compared with 76% for always-same. The saved relation specialist scores 38%, compared with a 40% majority-class baseline. Specialist execution mode is missing and the saved outputs are compatible with random fallback behavior. These are audit findings, not new model results. [Details and numerical caveats](BASELINE_AUDIT.md).

## Ranked directions

| Priority | Direction | Expected benefit to test |
|---|---|---|
| Prerequisite | Correct labels, scoring, errors, and execution provenance | A trustworthy baseline and meaningful comparisons |
| 1 | Full support/refute/unknown decisions, correct NLI inputs, preserved evidence | Better relation decisions and minority-class recall |
| 2 | Contextual identity matching with hard negatives | Fewer false entity merges |
| 3 | Typed actions and verifiable transactions | Correct graph behavior from the same model predictions |
| 4 | Task calibration and dependency-aware acceptance | Lower graph error at matched useful coverage |
| 5 | Joint graph inference and independent-source evidence aggregation | Consistent identity clusters without double-counting evidence |
| 6 | Impact-aware retrieval and model escalation | Better graph quality under a fixed inference budget |

These original priorities reflect observed bottlenecks and implementation dependencies, not measured effect sizes. Follow-up experiments found specific gains, null results, and transfer failures; advanced policy gains remain synthetic. Novelty has not been established. The execution report is the current evidence, while the original hypotheses below remain the prospective record.

## Reading map

- [BASELINE_AUDIT.md](BASELINE_AUDIT.md): recomputed metrics, failure modes, source references, and limits of the current claims.
- [HYPOTHESES.md](HYPOTHESES.md): six decision/evidence hypotheses with mechanisms, predictions, and falsification tests.
- [COMPILER_THEORY.md](COMPILER_THEORY.md): four compiler hypotheses covering typed actions, constrained inference, dependency risk, and transaction certificates.
- [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md): ordered ablations, data splits, graph evaluation, statistical checks, and go/no-go criteria.
- [audit_saved_results.py](audit_saved_results.py) and [audit_snapshot.json](audit_snapshot.json): reproducible offline analysis of the 600 stored backend records, with input hashes.
- [probe_compiler_semantics.py](probe_compiler_semantics.py) and [compiler_probe_snapshot.json](compiler_probe_snapshot.json): deterministic offline reproduction of the staging counterexample.

Primary papers and model documentation are linked beside the claims they support. The suggested first experiment is small: establish one verified local backend per task, fix semantic/scoring contracts, then compare the corrected baseline with complete evidence and canonical labels. Compiler experiments should reuse cached decisions so that model improvements and compiler improvements remain distinguishable.
