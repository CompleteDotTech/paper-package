# Claim-to-evidence audit

| Claim | Executed evidence in results.json | Boundary / rejected extrapolation |
|---|---|---|
| Reliability ranking changes 17 wrong edges to 15 at equal K=145 | acceptance.budgets[2], fit, selected IDs, intervals_vs_raw | Misses 20% target; previously inspected data; source balancing ties unweighted fit here |
| Source diversity improves represented-group count but harms primary quality | acceptance.budgets[0]: 69 to 98 groups; correct 92 to 85; contaminated 6 to 15 | Group coverage is not graph-node or candidate recall |
| Robust review optimizes its supplied upper envelope, not empirical truth | H3.oracle_fixtures, joint_distributions, budgets[1] | At budget 20 expected contamination worsens 10.6875 to 12.1875; marginal miscalibration control invalidates guarantees |
| Exact lineage recovers 16 controlled admissions without oracle failures | H4.fixtures, large, recovered_admissions, false_admissions | Supplied independent primitive events, not independent proofs; not new extracted scientific edges |
| Bounded exactness safely falls back | H4.state_limit_control; regression input-limit tests | No point estimate after exhaustion; malformed lineage can produce an incorrect precise probability |
| Cutset conditioning solves 16 large cycles exactly | H5.large, finite fixtures, independent cycle oracle | Components capped at 256; discovered cutset capped at four; no natural-topology prevalence or latency claim |
| Higher structural utility is not factual truth | H5.false_priority_control and H4.corrupt_lineage_control | Wrong priority/identity assumptions survive exact computation |
| No fresh model calls or default policy changes | fresh_service_calls=0; raw-response reconstruction and file diff | Historical 3,024 calls not recounted; no external-system superiority claim |

The protocol was committed before these executions but after earlier results were public. Repeated evaluation remains exploratory. Primary target failures are retained rather than redefined from favorable secondary metrics.
