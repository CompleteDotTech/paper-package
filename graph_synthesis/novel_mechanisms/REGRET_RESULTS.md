# Interval-priority regret: fifth distinct addition after concurrent overlap

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Novelty reconciliation

Concurrent main-branch work independently added bipartite flow optimization. Original H4 is therefore retained as replication rather than counted as a distinct new mechanism. The five distinct additions in this PR are H1 label-shift correction, H2 dependence-robust bounds, H3 protected-fact repair, H5 indexed conflicts, and H6 interval-priority regret. Both original and replacement protocols remain in ancestry. This is repository-scoped novelty, not a new mathematical invention.

The [replacement protocol](REGRET_PROTOCOL.md) was frozen in `7a624f79c3f79b4c23a0879006bbe34412f126d9` before execution against the expanded main baseline `7e2ce2fce28f29ebc6a2b462d063ea558b656cc1`. The original experiments and unfavorable outcomes were not retuned. Fresh Jev service calls: 0.

## Hypothesis and falsification

Point-priority optimization can choose a fragile conflict-free set when priorities are uncertain. Test whether minimizing worst-case regret over supplied integer intervals reduces the maximum gap from an interval-consistent optimal selection. Regret is R(S)=max_w[max_T w(T)-w(S)]. For interval boxes this equals max_T[upper(T minus S)-lower(S minus T)]; the comparator is the actual previous nominal-priority solver. A separate oracle enumerates every endpoint scenario and computes utilities directly, rather than using this identity.

Enumeration is capped at 12 vertices and 1,000,000 candidate/rival comparisons. Exhaustion stages with no partial optimum. Exact ties maximize nominal utility and then use lexicographic assertion IDs. A rival set and endpoint priority assignment witness the returned worst-case gap. No graph writes are performed.

The frozen primary target requires zero oracle, consistency and witness failures, no regret regression, and strictly lower worst-case regret in at least 10% of 128 seeded eight-vertex fixtures. Edge densities alternate 0.15/0.35/0.55/0.75; priorities and intervals are generated under the protocol, seed 20260923.

## Executed results

| Measure | Observed |
|---|---:|
| Primary target | Met |
| Strictly lower worst-case regret | 62/128 (48.44%) |
| Oracle / consistency / witness failures | 0 / 0 / 0 |
| Regret regressions | 0 |
| Cases sacrificing nominal utility | 44/128 |

In the fixed conflicting-pair control, nominal optimization chooses a (priority 9, interval [0,10]) over b (priority 8, interval [8,8]). Its worst-case regret is 8. The robust policy chooses b with regret 2, sacrificing one nominal utility unit. Zero-width intervals restore a zero-regret nominal optimum. The supplied intervals, not Jev probabilities, define the robustness claim.

![H6. Worst-case regret compared with nominal priority optimization.](figures/06_interval_regret.png)

## Limits and negative controls

A smaller worst-case supplied-priority gap is not higher semantic accuracy. The random results explicitly report nominal utility sacrifices. Incorrect or overly narrow uncertainty intervals void the guarantee: actual priorities a=10,b=0 are outside the fixed control intervals and give the robust choice regret 10. Complete interval boxes may also be too pessimistic when priorities are dependent. No useful interval-estimation method, large-graph scalability, service latency or superiority to KARMA is established. Malformed inputs, cap exhaustion, nonmutation, edge-order invariance, equal/zero-width intervals and empty/disconnected graphs are regression-tested.

## Reproduction and attribution

```bash
python -B -m graph_synthesis.novel_mechanisms.regret
python -B -m graph_synthesis.novel_mechanisms.regret --check
python -B -m graph_synthesis.novel_mechanisms.regret --report
```

The first command executes the experiment and writes per-case intervals, baseline/proposed selections, regret, independent oracle results, witnesses and input hashes. The second disables network access and checks exact replay. The third publishes the extra figure, standalone report and additive combined manuscript section. This is a deterministic bounded application of established minimax-regret ideas, not a reproduction of randomized or double-oracle algorithms: [Mastin, Jaillet and Chin](https://arxiv.org/abs/1401.7043); [Gilbert and Spanjaard](https://arxiv.org/abs/1602.01764).
