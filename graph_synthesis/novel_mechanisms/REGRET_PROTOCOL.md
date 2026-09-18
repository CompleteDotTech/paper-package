# Pre-execution replacement hypothesis: robust regret under uncertain priorities

September 18, 2026. Frozen before executing this additional experiment. Integration baseline: main `7e2ce2fce28f29ebc6a2b462d063ea558b656cc1`; original five-mechanism protocol and all outcomes remain unchanged.

## Why this sixth experiment is necessary

After the original protocol was committed and executed, concurrent main-branch work introduced `source_structural` H4, the same broad bipartite flow/cover mechanism as this branch's H4. The original novelty audit against `a62a325` was valid at its stated snapshot, but five untried mechanisms must not be claimed against the newer integrated repository by ignoring that overlap. Keep original H4 as a concurrent replication and add H6 below as the fifth distinct new mechanism alongside H1, H2, H3 and H5. Do not erase the overlap or rewrite the original protocol. The main protocols and a repository search for regret revealed no previous interval-priority minimax-regret experiment. This is repository-scoped novelty, not invention of robust optimization.

## Motivation and new mechanism

All earlier conflict optimizers maximize supplied point priorities, and their high-priority false-assertion controls show that a structurally optimal choice need not be true. Test whether acknowledging priority uncertainty reduces worst-case opportunity loss, without pretending to establish truth. Each assertion has a supplied nonnegative integer interval [lower, upper] and a nominal integer priority inside it. For a conflict-free set S, define regret R(S) = max over interval-consistent priorities w of [max over conflict-free T of w(T) - w(S)]. Choose S minimizing R, then maximize nominal utility, then break ties lexicographically by sorted assertion IDs.

Implementation uses the identity R(S) = max_T [upper(T minus S) - lower(S minus T)]. Supply a maximizing rival T and an interval-endpoint scenario as a checkable witness. The maximizations commute because both domains are finite/extreme-point reducible; for fixed S,T, each coefficient is -1, 0 or 1, so the extreme point is immediate. Enumeration is explicitly bounded at 12 vertices and 1,000,000 S,T comparisons. Any cap exhaustion returns staged with no purported optimum or partial proposal. This is an opt-in research function and performs no graph writes.

## Frozen experiment and primary criterion

Seed 20260923. Generate 128 eight-vertex graphs. Alternate edge probabilities 0.15, 0.35, 0.55 and 0.75 by case index. Nominal priorities are uniform integers 1-9. Independently sample lower in [0, nominal] and upper in [nominal, nominal+9]. Use the actual previous point-priority solver as the baseline. Independently enumerate all 2^8 endpoint scenarios, calculate every feasible set's utility in each scenario, and find the worst regret of each set. This oracle must not call the proposed regret formula or its subset-sum helper.

Primary conjunction: zero consistency, witness, optimal-regret or oracle tie-break mismatches; no worst-case regret regression against the previous nominal solver; and strictly lower worst-case regret in at least 10% of the 128 fixtures. Report all cases, baseline/proposed sets, regret, nominal utility, intervals, rivals, witnesses, input hashes and the entire primary conjunction. No retuning after outcomes. Count improvements in worst-case supplied-priority regret, not accuracy, significance, semantic truth or dollars.

Fixed control: conflicting a and b with nominal priorities 9 and 8, intervals a=[0,10], b=[8,8]. Nominal a has worst regret 8; robust b has worst regret 2, at the cost of one nominal utility unit. Include zero-width intervals (regret minimum zero and nominal optimum), empty/disconnected graphs, equal priorities, duplicate/reversed edges, permutation invariance, malformed bounds, unknown/self edges, cap exhaustion and nonmutation tests. Preserve a control where actual priorities lie outside supplied intervals: no robust guarantee applies there. Also report nominal utility losses on random cases instead of hiding the tradeoff.

## Evidence, integration and reporting

Zero fresh Jev calls. This is controlled algorithmic evidence with supplied uncertainty intervals, not a source of those intervals. No new calibration or semantic reliability claim. Preserve original H1-H5 results and original protocol, identify H4 as concurrent replication, add H6 code, results, tests, one SVG/PNG figure, standalone report and an additive manuscript section. Integrate latest main rather than overwrite concurrent studies. Run all new and existing tests, original archive verification, exact offline replay, figure/manuscript regeneration and cross-platform checks before merging.

Foundations: Mastin, Jaillet and Chin, Randomized Minmax Regret for Combinatorial Optimization Under Uncertainty (https://arxiv.org/abs/1401.7043); Gilbert and Spanjaard, A double oracle approach for minmax regret optimization problems with interval data (https://arxiv.org/abs/1602.01764). This experiment uses deterministic bounded enumeration, not those papers' randomized strategies or double-oracle algorithms.
