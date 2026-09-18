# Claim-to-evidence map

All paths below are relative to this extension. Counts, labels and seed-based fixtures are in `results.json`; `run.py` recomputes them and `report.py` generates the manuscript and figures. Targets were frozen in `PROTOCOL.md` before implementation. H1 and H3 failures are intentionally retained.

| Claim | Machine-readable source | Independent or falsifying checks | Scope |
|---|---|---|---|
| Marginal LP width reduction is 4.96%, not the required 10% | `H1.relative_width_reduction`, mean-width fields | All joint masses, endpoints, LP witnesses, marginal/pairwise feasibility, two-event analytic regression tests | Supplied probabilities; numerical rather than exact-arithmetic verification |
| Shared 0.8 source must not justify 0.95 admission through two aliases | `H1.controls.shared_source` | Independent point 0.96 contrasted with [0.8,1] envelope | Correct marginals still required |
| Invariant repair answers match all-optima enumeration | `H2.fixtures`, `oracle_failures`, `unique_retention_failures` | Independent subset enumeration, all three-vertex graphs with binary priorities, tied pairs and dense staging | Supplied conflicts/priorities; false-priority control survives |
| Weighted review worsens the primary replay outcome 50 to 63 | `H3.baseline_primary`, `proposed_primary`, `panels` | Development-only fit, no evaluation gold in policy features, uniform-order control, paired source-group bootstrap | Reused captured decisions, synthetic query exposure, idealized review |
| Balanced-tree DP work falls 97.63%; reconstruction reduces counted combined saving to 48.81% | `H4.balanced` | Full-tree DP, exhaustive small-tree oracle, selected-set feasibility, path control, atomic invalid updates | Fixed trees and integer weight edits, not dynamic topology or latency |
| Indexed grounded closure reduces sparse dependency inspections 94.28% | `H5.local` | Cold full-scan oracle, source-removed cycles, alternate grounding, dense control, explicit counter initialization | Bounded cold recomputation, not a DRed or distributed benchmark |
| No fresh Jev calls | `fresh_service_calls`, source hashes, benchmark network blockers | Archived raw-response verification, `original-inventory.json` | No new semantic accuracy claim |
| Five new repository experiment combinations, not world-first algorithms | `NOVELTY.md`, baseline commit, existing protocols | Cited primary prior work and explicit overlap table | Targeted audit cannot prove universal novelty |

`artifact-manifest.json` binds extension source, protocol, results, figures and logs. `manuscript/paper-current.build.json` separately binds the shared mutable manuscript, renderer and PDF. The immutable original 161-file inventory is verified without rewriting its source artifacts.
