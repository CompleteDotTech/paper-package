# What the saved results actually establish

Audited 2026-09-17 against source commit `f812d74c816d9f90162ae5db3be94bdb514b1075`. Source project: [typed-probabilistic-graph-compiler](../typed-probabilistic-graph-compiler/). The source checkout was read without edits. Exact saved-input SHA-256 hashes and recomputed counts appear in [audit_snapshot.json](audit_snapshot.json).

## Recomputed observations

These are descriptions of stored predictions, **not verified neural-model performance**. “Answerable” below excludes gold `uncertain` examples and therefore defines a different task; it is not a replacement headline score.

| Task / saved backend | Published accuracy | Exact label matches, all examples | Answerable subset | Relevant constant baseline |
|---|---:|---:|---:|---|
| Relation / `specialist-nli` | 38% | 19/50 = 38% | 19/30 = 63.33% | Always uncertain: 20/50 = 40%; binary majority: 15/30 = 50% |
| ER / `specialist-er` | 68% | 56/100 = 56% | 56/88 = 63.64% | Always same: 76/100 = 76%; answerable: 76/88 = 86.36% |
| ER / mock or fixed-confidence control, labels as stored | 12% | 0/100 | 0/88 | Outputs are `true/false`, scored against `same/different` |
| ER / same mock or control, diagnostic label translation | Not a new run | 76/100 = 76% | 76/88 = 86.36% | Translation `true -> same`, `false -> different` |
| Jev / relation | 0% | 0/50 | 0/30 | All 50 rows are `ERROR` |
| Jev / ER | 12% | 0/100 | 0/88 | All 100 rows are `ERROR` |

The constant baselines use observed class counts as a descriptive diagnostic. A future deployable majority/prior baseline must fit its choice on training data. The translated ER scores only expose a vocabulary problem; no model was improved or rerun.

The ER evaluator [unconditionally credits all uncertain gold cases](../typed-probabilistic-graph-compiler/pgc/experiments/benchmark_entity_resolution_100.py#L135), including execution errors. That supplies 12 percentage points to every backend. The claimed 5.7x advantage over mock therefore does not establish a specialization advantage. On the unambiguous subset, the stored specialist is substantially below always-same.

The relation evaluator [maps the three gold labels to true/false/uncertain](../typed-probabilistic-graph-compiler/pgc/experiments/scifact_benchmark.py#L240), but the benchmarked NOUL backends only return `true/false`. The 20 uncertain cases are unreachable. This is a task/interface mismatch, not evidence that those cases are inherently impossible.

## Calibration claims are not supported by the published score

Both evaluators use `(probability_of_predicted_label - correctness_indicator)^2`: [relation](../typed-probabilistic-graph-compiler/pgc/experiments/scifact_benchmark.py#L101), [ER](../typed-probabilistic-graph-compiler/pgc/experiments/benchmark_entity_resolution_100.py#L46). This can coincide with a one-coordinate binary Brier when labels/correctness are valid and exhaustive. It is not the reported tasks' proper three-class Brier, and automatic correctness on uncertain ER examples further distorts it.

On answerable rows with valid canonical binary distributions, the offline audit computes:

| Saved output | One-coordinate binary Brier | Rows scored |
|---|---:|---:|
| Relation specialist | 0.252344 | 30 |
| ER specialist | 0.206103 | 88 |
| ER mock, after diagnostic label translation | 0.142139 | 88 |
| ER fixed 0.85 control, after diagnostic translation | 0.117955 | 88 |

For reference, a constant 0.5 forecast has binary Brier 0.25. The empirical-prior constant forecast on these answerable ER labels has descriptive Brier `(76/88)*(12/88) = 0.117769`. These are same-task diagnostics only. Excluding uncertainty changes the estimand, and lower Brier does not by itself isolate calibration from predictive discrimination. There is no recoverable three-class probability vector in the saved files; the audit does not fabricate one.

## Backend identity and timing are unverified

The specialist constructors catch dependency/model-loading failures, print a warning, and automatically use random fallbacks under the same backend names without saving execution mode: [NLI](../typed-probabilistic-graph-compiler/pgc/decision/specialist_nli.py#L38), [ER](../typed-probabilistic-graph-compiler/pgc/decision/specialist_er.py#L37). Their fallback NOUL methods draw the positive probability uniformly from 0.3 to 0.9 and report a synthetic latency uniformly from 50 to 150 ms.

All 50 stored NLI and all 100 stored ER specialist rows fit those probability/latency ranges. The JSONs omit execution mode, checkpoint revision, backend version, hardware, and measured wall-clock provenance. **This is consistent with fallback execution but does not prove it.** Consequently the approximately 100 ms latency and purported specialist performance cannot be attributed confidently to neural inference. All Jev rows are errors; saved records omit the error text, so their precise cause cannot be established from those records alone.

There is also a useful null calculation. Under the implemented fallback distribution, `P(predicted positive)=2/3`. For the relation label counts its expected all-example accuracy is `(15*(2/3)+15*(1/3))/50 = 30%`. For ER, expected exact accuracy is `(76*(2/3)+12*(1/3))/100 = 54.67%`, or 66.67% with the existing 12 uncertain cases automatically credited. Thus 68% is close to that fallback's permissively scored expectation; no learned semantic skill is necessary to produce a score of that scale. This calculation is a diagnostic prediction under the fallback hypothesis, not proof of the execution path.

## Concrete bottlenecks motivating new hypotheses

| Observation | Evidence | Consequence |
|---|---|---|
| NLI receives generic question as hypothesis; each evidence passage is truncated to 80 characters | [request construction](../typed-probabilistic-graph-compiler/pgc/experiments/scifact_benchmark.py#L207), [adapter](../typed-probabilistic-graph-compiler/pgc/decision/specialist_nli.py#L87) | A real checkpoint would not receive a conventional evidence/claim pair |
| NLI reads index 2 as entailment and clips a score before testing its range | [score conversion](../typed-probabilistic-graph-compiler/pgc/decision/specialist_nli.py#L92) | The declared checkpoint labels index 2 neutral, index 1 entailment; score interpretation must be repaired. [Checkpoint configuration](https://huggingface.co/cross-encoder/nli-deberta-v3-large/blob/main/config.json) |
| ER uses mention strings only; no current fixture supplies context | [ER request](../typed-probabilistic-graph-compiler/pgc/experiments/benchmark_entity_resolution_100.py#L102), [fixture type](../typed-probabilistic-graph-compiler/pgc/experiments/entity_resolution_100.py#L19) | Adding context requires new data as well as a new adapter |
| ER's default identifier has an extra hyphen; the corresponding published model is a passage ranker | [default](../typed-probabilistic-graph-compiler/pgc/decision/specialist_er.py#L25), [published model](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2) | Verify loading and revision; neither relevance nor clipped score establishes identity probability |
| Dataset loaders return literal curated examples | [relation loader](../typed-probabilistic-graph-compiler/pgc/experiments/scifact_50.py#L19), [ER loader](../typed-probabilistic-graph-compiler/pgc/experiments/entity_resolution_100.py#L31) | Official-dataset performance and biomedical source validity are not established |
| Benchmarks call `backend.decide` directly | [relation benchmark](../typed-probabilistic-graph-compiler/pgc/experiments/scifact_benchmark.py#L229), [ER benchmark](../typed-probabilistic-graph-compiler/pgc/experiments/benchmark_entity_resolution_100.py#L121) | Their 600 records do not validate constraints, graph mutation, or atomic transactions |

Compiler inspection and a separate deterministic probe are described in [COMPILER_THEORY.md](COMPILER_THEORY.md). The constraints currently always pass; high confidence can stage a positive mutation even when the selected outcome is negative. Those are independently testable compiler defects, not deductions from benchmark accuracy.

## Reproduce the saved-result audit

From this directory, using Python's standard library only:

```powershell
python -B audit_saved_results.py --output audit_snapshot.json
```

The script reads the sibling project's two JSON files and rewrites only the specified audit output. It neither imports the project's model modules nor invokes backends. It checks duplicate rows, gold-label agreement, and matched backend coverage, and reports every probabilistic score's denominator. For another checkout use `--repo <path>`.

The conclusion is narrower than the publication documents: the repository demonstrates interface scaffolding and supplies inspectable example outputs. It does not yet establish specialist superiority, calibrated graph probabilities, real neural latency, or transaction safety. The theory program therefore targets both credible measurement and better inference/compilation mechanisms.
