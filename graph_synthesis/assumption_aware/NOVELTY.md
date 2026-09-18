# Novelty and prior-art audit

Audit date: September 18, 2026. Repository baseline: `a62a3257645d8e35cd4e45be53bfa9511d27724b`.

## Claim permitted

Five additional hypothesis/benchmark combinations were implemented for this paper package after examining its executed graph-synthesis, theory, follow-up, adaptive, risk-control and reliability studies. They respond specifically to observed limitations of PR #17. This is a repository-scoped research extension, not a world-first algorithm claim. Neither a repository search nor a finite literature search can establish that no one has ever attempted these ideas.

The audit examined the current results index; `graph_synthesis/README.md`, `EVIDENCE_PAPER.md`, `PROTOCOL.md`; the `followup`, `adaptive`, `risk_control` and `reliability` protocols, results and method implementations; graph compiler/retraction tests; and the multicall study's report and saved-evidence loader. Searches for dependence/Frechet envelopes, repair invariance, query exposure, ancestor propagation and grounded closure supplemented that review. Search absence alone is not treated as proof of novelty.

| New combination | Closest existing repository approach | Difference tested here | Established prior-art overlap |
|---|---|---|---|
| H1: bounded joint-distribution lineage envelopes | PR #17 exact lineage with supplied independent primitive events | Unknown dependence and optional supplied pair intersections; tested against arbitrary joint distributions and conservative marginal bounds | Linear-program probabilistic satisfiability and union bounds |
| H2: invariant OR/AND answers over maximum-priority repairs | PR #17 deterministic maximum-priority consistent selection | Certify only answers shared by all optimal repairs; preserve disjunction without choosing an arbitrary member | Consistent query answering and prioritized repair |
| H3: exposure-weighted single-view review | PR #17 single-view group-contamination ranking | Fixed synthetic downstream-exposure weights multiply the same risk-based marginal gain at equal budget | Utility-oriented knowledge-graph auditing |
| H4: ancestor-local tree message changes | PR #17 cache reused only for unchanged connected components | Single-node weight deltas inside one connected, fixed tree; explicitly charge reconstruction | Tree dynamic programming and cached aggregate propagation |
| H5: grounded positive-rule closure after withdrawal | Existing cascading invalid-prerequisite retraction and PR #17 conflict-component maintenance | Recompute only from external grounding, preserve alternative supports, reject circular self-support; compare indexed agenda with cold full scanning | Least-fixed-point Datalog materialisation and recursive maintenance |

The earlier cascading-retraction recurrence invalidates assertions depending on invalid prerequisites. It does not by itself provide this test of alternative positive Horn supports and unseeded recursive components. Conversely, this extension's H5 does not implement dependency-local DRed deletion, distributed persistence or full database transaction semantics.

## Primary sources checked

The references below were verified through author archives, arXiv abstracts or publisher pages. Search terms included probabilistic entailment/linear-program bounds, consistent answers over preferred repairs, utility/query-oriented KG auditing, dynamic programming for tree independent sets, and recursive Datalog materialisation/deletion. This was a targeted overlap audit, not a systematic review with exhaustive database coverage.

1. Hansen, P., and Perron, S. *Merging the local and global approaches to probabilistic satisfiability*. International Journal of Approximate Reasoning 47(2), 125–140, 2008. DOI: [10.1016/j.ijar.2007.03.001](https://doi.org/10.1016/j.ijar.2007.03.001). The author report is [GERAD G-2004-48](https://www.gerad.ca/fr/papers/G-2004-48). Local/global probability bounds and LP formulations precede this work.
2. Kaski, P., Mannila, H., and Mohapatra, C. K. *Optimal Union Probability Interval Is NP-Hard*. 2026 preprint, [arXiv:2605.03556](https://arxiv.org/abs/2605.03556). It is relevant to the boundedness and complexity disclaimer, not an external benchmark reproduced here.
3. Staworko, S., Chomicki, J., and Marcinkowski, J. *Prioritized Repairing and Consistent Query Answering in Relational Databases*. [arXiv:0908.0464](https://arxiv.org/abs/0908.0464). Invariance across preferred repairs is established; this extension's particular weight/cap/oracle integration is narrower.
4. Pardal, N., Cifuentes, S., Pin, E., Martinez, M. V., and Abriola, S. *Computational Complexity of Preferred Subset Repairs on Data-Graphs*. 2024, [arXiv:2402.09265](https://arxiv.org/abs/2402.09265). Preferred weighted graph repair is not new terminology invented by this extension.
5. Marchesin, S., Silvello, G., and Alonso, O. *Utility-Oriented Knowledge Graph Accuracy Estimation with Limited Annotations: A Case Study on DBpedia*. HCOMP 12(1), 105–114, 2024. DOI: [10.1609/hcomp.v12i1.31605](https://doi.org/10.1609/hcomp.v12i1.31605). This source includes actual annotation work; the present H3 uses a synthetic exposure workload and must not be equated with that empirical setting.
6. Gupta, C., Latypov, R., Maus, Y., Pai, S., Särkkä, S., Studený, J., Suomela, J., Uitto, J., and Vahidi, H. *Fast Dynamic Programming in Trees in the MPC Model*. 2023, [arXiv:2305.03693](https://arxiv.org/abs/2305.03693). Maximum-weight independent sets and tree aggregate propagation are established. Their massively parallel model is not benchmarked or claimed equivalent to this in-memory update prototype.
7. Hu, P., Motik, B., and Horrocks, I. *Optimised Maintenance of Datalog Materialisations*. AAAI 32(1), 2018. DOI: [10.1609/aaai.v32i1.11554](https://doi.org/10.1609/aaai.v32i1.11554). Recursive maintenance and counting limitations have extensive prior work. The H5 strong baseline is cold full scanning, not a reproduced DRed/B/F implementation.

The [bibliography](references.bib) contains these sources. External algorithms were not executed, so the paper makes no speed or accuracy superiority claim over them or over KARMA. The research conclusions come from the saved internal experiments and their controls, not from a purported absence of prior work.
