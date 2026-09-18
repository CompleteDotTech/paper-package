# Execution of the new theory

The authorized five-stage follow-up is implemented in [typed-probabilistic-graph-compiler](../typed-probabilistic-graph-compiler/README.md). The [complete results report](../typed-probabilistic-graph-compiler/RESULTS_REPORT.md) links predictions, data manifests, source hashes, code, tests, reproduction commands and plots. Original saved benchmark JSON is preserved.

| Stage | Delivered | Finding |
|---|---|---|
| Evaluation repair | Canonical labels, probability checks, proper scores, honest errors/coverage, no uncertain-example credit | Historic headline comparisons are superseded |
| Verified inference | Pinned real NLI model and three locally trained identity models; no random fallback | Original fixtures now exercise actual local inference |
| Evidence/context/calibration ablations | 339 held-out SciFact pairs; 413 identity-disjoint DBLP–ACM pairs; independent calibration | Full evidence improves accuracy; identity model beats lexical; extra context is inconclusive; calibration improves scores |
| Typed compiler | Actual graph/provenance store, declarative rules, evidence and decision binding, atomic commits, version/retry validation | Controlled invalid writes reject; real support commits and refutation does not |
| Advanced policies | Repeated-source, joint identity, dependency risk, and query-allocation controls with matched work budgets | Synthetic benefits depend on correct assumptions; wrong rules and distribution shift cause failures |

Full evidence reaches 47.20% accuracy versus 40.41% for an 80-character input on this SciFact classification task. Full-context identity training reaches 98.06% versus 95.64% lexical on DBLP–ACM. These are different tasks, not a combined benchmark. The original ER development fixtures reveal poor transfer: 51.14% on 88 binary-labeled examples versus 86.36% for always-same. The 12 uncertain examples receive no semantic credit.

The compiler remains an in-memory research implementation. Internal hashes do not authenticate evidence or prove truth. Advanced policy simulations do not establish real graph-risk guarantees or general model superiority. Context, selection, hard-negative tradeoffs, and calibration limits are reported alongside favorable results.

The next scientific phase would require adjudicated domain-specific identity data, repeated training seeds and complete real graph-episode evaluations. Those are new research extensions; the current execution does not claim them as completed evidence.
