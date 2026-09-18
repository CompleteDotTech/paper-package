# Five follow-up improvements: execution protocol

Baseline: `1e03d0e7dfbf0b0deb1e39ecf133e66e05be141b` (merged PRs through #12). Written before this follow-up suite is run; prior aggregate findings and both runs already existed and were inspected. This is an exploratory protocol, NOT an independent preregistration. Do not retune the following endpoints after seeing outcomes.

## Motivation and evidence boundary

The ten-theory suite found that a macro-F1-selected cascade could increase wrong graph edges from 20 to 37; confidence-one predictions could be wrong; correlated formulations were not independent witnesses. The fresh rerun found temperature calibration can improve log loss while worsening Brier score, and label stability does not establish accuracy. Earlier graph falsification exposed overlapping-interval conflicts. Alternative-proof survival did not address probability inflation from duplicate/shared evidence.

H1-H3 below use exact captured Jev responses from the original and September 18 rerun, not newly requested inference. H4-H5 execute controlled algorithms against independently specified finite oracles, not Jev on new scientific documents. Service calls in THIS suite: zero. Model: captured `jev-1.13.0`. Never change archived raw evidence or the production compiler.

## H1 — Guarded probability calibration

Hypothesis: calibration-only shrinkage toward the raw distribution prevents the Brier damage of temperature-only fitting while retaining a log-loss improvement across runs. Split original calibration by connected source component using SHA-256 modulo two. Fit temperature on one half, choosing minimum log loss over T in {0.25,0.5,0.75,1,1.5,2,3,4,6,8}. On the other half choose lambda in {0,0.25,0.5,0.75,1} for q=(1-lambda)p+lambda*temperature(p,T), minimizing log loss subject to Brier no worse than raw. Empty/unsupported fits fall back to identity. No fresh-run labels are available to fitting. Evaluate fixed policies on both runs, separately. Primary: rerun relation_support/fewshot_contract strictly lower log loss than raw, Brier no greater than raw (tolerance 1e-12), unchanged labels. Also report temperature-only and all identity/baseline-arm diagnostics. Failure of either scoring criterion falsifies the operational target, not all calibration methods.

## H2 — Graph-edge-aware economical routing

Hypothesis: choosing a baseline-to-few-shot cascade using edge outcomes avoids the hidden graph-quality loss of macro-F1-only selection. Fit on original calibration only. Independent thresholds for baseline positive and negative labels from {0,0.5,0.7,0.85,0.9,0.95,0.99,1,1.000001}; failures always escalate. Select minimum recorded input-token cost satisfying precision at least all-few-shot, correct-edge retention >=98%, and no extra wrong edges on calibration. Always-few-shot is an explicit safe fallback without baseline overhead. Compare raw baseline, all-few-shot, the earlier macro-F1-only cascade, and this fixed graph-aware policy on both evaluations. Charge baseline tokens plus all fallback tokens, including failed calls. Primary rerun relation target: >=20% input-token savings, >=98% correct-edge retention and no more wrong edges than all-few-shot. This is recorded-token counterfactual routing, not newly measured service latency or invoice cost. A target miss is retained.

## H3 — Cross-run stability as a mutation gate

Hypothesis: exact-input, same-arm agreement across the original and rerun is more useful than rerun confidence alone at matched accepted volume. Stage errors/disagreement; accept only identical positive labels. Compare to rerun confidence-ranked top-k with deterministic ID tie breaking and expected random k-subset error count. Primary rerun relation few-shot target: retain >=95% of rerun correct edges and strictly fewer wrong edges than both matched-volume comparators. Record residual shared errors, confidence-one errors, and two-run versus one-run input tokens. A stable wrong judgment is a counterexample to independent corroboration. No inference of multi-day drift or fixed provider weights.

## H4 — Scope- and interval-aware conflict staging

Hypothesis: an opt-in qualifier guard detects overlapping temporal contradictions missed by exact qualifier equality without staging known nonconflicting scopes/intervals. Half-open integer intervals [start,end); None denotes unbounded endpoints. Missing scope is unknown, not universal. Detect opposite polarity on the same triple, plus declared functional-relation collisions; stage unknown/invalid inputs. Compare exact-qualifier, qualifier-blind, and interval/scope-aware guards on exhaustive bounded pairs. The truth oracle enumerates integer instants independently of the overlap implementation. Primary: zero missed conflicts, zero false conflict flags on supported inputs; stage all unknown/malformed cases. Include endpoint contact, unbounded intervals, functional predicates, opposite polarity, distinct scope and self-comparison tests. This is a controlled validation layer, not extraction, biomedical truth validation, or a default compiler change.

## H5 — Duplicate/shared-lineage probability bounds

Hypothesis: deduplicated proof-lineage components prevent unsupported confidence inflation caused by naive noisy-OR of duplicate or overlapping sufficient proofs. Proofs are nonempty conjunctions of supplied independent primitive Bernoulli events. Collapse duplicate proof atom sets; connect proofs sharing atoms. Bound each connected component's OR by max proof probability and min(sum proof probabilities,1); combine disjoint components using independence of their explicitly supplied primitive events. Compare naive noisy-OR and duplicate-only noisy-OR to bounds against exact finite event enumeration. Primary: every exact probability within the bounds, invariance to 1/2/5/20 duplicate copies, no lower-bound admissions at threshold 0.95 when exact probability is below 0.95, and at least one naive false admission prevented. Report loss of correct high-probability admissions and interval widths. Include deliberately corrupted lineage as a negative control. These assumptions are supplied by the synthetic fixture; raw Jev scores are NOT calibrated source reliabilities. No claim that Jev infers correct lineage or probability guarantees.

## Analysis, reproducibility and honesty

Seed 20260918. Where sampling uncertainty is reported, use 1,000 paired connected-component bootstrap draws with both policies evaluated on each draw. Intervals are descriptive 95%, unadjusted, not confirmatory tests; target indicators are engineering criteria, not statistical discoveries. H1-H3 share already inspected data and must not be pooled into independent sample counts or a success percentage. Invalid service responses remain operational failures; probability losses explicitly report valid-only denominators. Components derive from source/record IDs, never gold identity groups. Purge calibration components touching evaluation and log resulting counts and hashes. Prediction/payload matching, raw response parsing, unique IDs, exact source hashes, policy gold separation, input mutation safety, and deterministic replay receive regression tests. Negative/unsupported results must be in the paper and plots.

Pinned SHA-256 inputs:

- Original plan: `7ed8622f2022b263f3d0b9cda413b4caafe50ebcf0589b05b886dbd615987040`
- Original predictions: `2a5778db45583a7fca3f7a385846fb712f395e6b2b2510d914377c5862e959f2`
- Original calls: `4833a5919647b483f67668357e36ba5df334acdee2a628a64c5d7d7ce412ad83`
- Rerun plan: `009a5591488a93c709a6033c3414a4103e5d431d16871369b2c374ebac6c6942`
- Rerun predictions: `9fc0f0a345f6fbbd311759a5143c1d1be62313b72e26acd54e3ae289e040d76f`
- Rerun calls: `0eb3121cb20bd643eb14241079d5368c246ef63e522573b10c845a8927ea91a8`

Independent confirmation still requires new source-disjoint data, human-adjudicated graph truth, fixed policies, appropriate multiplicity control, and matched evidence/cost comparisons against external systems such as KARMA. This follow-up makes no external-system superiority claim.
