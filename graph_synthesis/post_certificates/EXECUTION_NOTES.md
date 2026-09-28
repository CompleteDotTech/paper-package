# Execution notes

The protocol was frozen in commit `f923e8d41ca5953d9793fadcc3730cfe9fc70b3a` before implementation or execution.

The first complete execution on September 18, 2026 produced H1 not met and H2-H5 met. During pre-PR review, H5's interval-marginal implementation was found to label outward-padded numerical **primal** LP optima as certified endpoints. That is not a sufficient numerical certificate because a feasible primal point does not by itself provide the required outer bound.

Commit `29debb5fc8df3fd4bc62f1505e50788a78ed8f3d` corrected only the numerical verification layer: HiGHS equality/inequality dual multipliers are projected to the required inequality sign, reduced-cost deficit is conservatively corrected using the unit simplex mass, and an outward padding term is subtracted before the lower dual bound is accepted. The max endpoint is obtained from the verified dual lower bound of the negated objective. Primal feasibility and dual-vs-primal consistency are checked; failures stage as non-certifying [0,1].

No hypothesis, seed, generator, comparator, threshold, evidence population or pass/fail rule was changed. The corrected frozen suite was rerun from scratch and retained the same target outcomes and headline metrics. The pre-correction generated artifacts were superseded and are not the evidence cited by the final report.

A concurrent, unrelated commit landed on the original research branch after the corrected generated commit. The final PR branch was therefore forked exactly from corrected evidence commit `cfd7026746aaf9a41501d59bb8f4448a84c356ac` so unrelated work is neither overwritten nor included.
