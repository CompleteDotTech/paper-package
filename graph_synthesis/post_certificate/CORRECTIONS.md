# Correction record: structural extensions in PR #33

Reviewed September 28, 2026. This record supplements the unchanged
[frozen protocol](PROTOCOL.md) at commit
`8187cc4e4b98e40f3146ce787b71f262b62b3abd`. Original implementation and results
remain inspectable at PR head `26131e887164bc59f0cb29f3512f36f98f967356`.
No frozen fixture population, seed, threshold, comparator or cap was retuned.
No fresh model calls or new scientific documents were used.

## H4: endpoint scenarios and the rejected broader interpretation

The frozen H4 Method explicitly evaluates the worst case across all interval
endpoint vectors. Its original heading and some publication prose described this
as interval minimax without making the finite scenario restriction clear.
Expected residual Bernoulli variance need not be largest at an endpoint, so that
broader continuous-interval claim is withdrawn.

The corrected implementation names the function `select_endpoint_minimax`.
`H4.primary_target_met` continues to mean the original endpoint-scenario
conjunction, with the original 128 fixtures and 16 point controls. Its measured
status is generated from the recorded booleans, separately from
`continuous_interval_claim_supported: false`.

A supplemental negative control has three singleton queries, review budget two,
and intervals `0=[0.1,0.9]`, `1=[0.3,0.4]`, `2=[0.5,0.5]`. Endpoint optimization
selects reviews `(1,2)` and reports worst residual variance `0.09`. The permitted
interior value `p0=0.5` yields `0.25`; reviewing `(0,2)` instead has continuous
worst variance `0.24`. For these singleton queries the continuous maxima follow
directly from `p*(1-p)`, maximized at the allowed point nearest `0.5`.
This falsifies continuous-interval minimax, even when the frozen endpoint target
passes. The control is labeled post-review evidence and does not enter the
original fixture count or threshold.

## Implementation and validation repairs

- H1/H5 reject over-width scopes before allocating exponential tables and check
  cumulative table allocation before construction. The original counted
  elimination-evaluation metric is retained separately from that allocation
  guard; it is not a memory or runtime measurement.
- All graph sizes use actual deterministic min-fill ordering. Numeric vertex
  distance is no longer substituted for induced width. H1 large chains now use
  the promised independent prefix dynamic-programming oracle, replacing the
  earlier closed-form-only check.
- H2 validates graph dependencies, computes topological order, and rejects cycles.
  Accepted transactions still compare their returned state with independent full
  recomputation. Each rejection control additionally requires the expected
  exception; unchanged input alone is insufficient. A mutation regression proves
  the benchmark fails when these exceptions are suppressed.
- Report outcomes derive from each `primary_target_met` field. Failed targets
  remain failed in CSV, abstract, outcome table and current-results snippet.
  Standard CSV quoting preserves the five-column schema.
- Manual validation preserves protocol ancestry/bytes and rejects any changed
  deterministic manuscript Markdown or HTML after rendering. It does not publish
  commits or perform model calls.

The corrected [results](results.json), [report](RESULTS.md), figures and cumulative
manuscript are regenerated from the unchanged frozen seed. Inspect individual
outcomes and limitations; separate target passes are not a semantic-success rate.

## Corrected measured outcome

The frozen H2 conjunction is **not met**: only 63 of 64 selected evaluation-failure
controls actually raise. One selected primitive has no affected derived node, so
the old control passed without injecting a failure. It remains in the original
denominator; no replacement fixture was selected. All 640 accepted transactions
match recomputation, stale/malformed controls each pass 64/64, and the local
evaluation reduction remains 90.1092529296875%. These favorable endpoints do not
rescue the failed conjunction. The exact failed control is retained in results.

H1, H3 and H5 retain their controlled target passes. H4 retains its finite endpoint
conjunction (45/128 strict endpoint gains); continuous interval minimax remains
unsupported and explicitly falsified by the supplemental control.
