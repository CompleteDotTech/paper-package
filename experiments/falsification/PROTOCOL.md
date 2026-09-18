# Graph-synthesis falsification extension: protocol v1

Base: `e11ca93be83e4f9c73401bcecd3275e18da21901`. Additive research only;
original observations, production policy, frozen MANIFEST, and previous numerical
references remain unchanged. Written before running the new diagnostics, but the
original evaluation labels and earlier results are already public and inspected.
This is **post-hoc exploratory analysis**, not preregistration or independent replication.

## Questions and predeclared panels

1. Do prompt variants fail on the same examples? Count common-success, shared
   errors, wrong-label agreement, and compare observed joint error with the
   product of marginal errors (descriptive, not an independence test).
2. Do accepted neighborhoods remain correct as a whole? Group using connected
   components of ALL candidate endpoints, including unaccepted candidates; report
   contamination, complete gold-positive recovery, and paired component-bootstrap
   intervals. Distinguish error-free but empty graphs from successful synthesis.
3. How sensitive is synthesis to candidate loss? Remove 0/10/25/50/75 percent of
   source IDs using 100 deterministic seed-based orderings, identical across arms
   and nested across loss levels. Drop whole candidates, never change their text
   and reuse their old scores. Report true-edge recall against the ORIGINAL gold
   denominator and the surviving-gold oracle ceiling. These are synthetic
   candidate-availability interventions, not new retrieval or inference results.
4. Does prevalence matter? For each action and baseline, calculate PPV at fixed
   prevalences 1/5/10/25/50/75/90 percent while holding empirical sensitivity and
   FPR constant. Label these conditional projections, not observed domain shifts.
5. How many independent error-free accepted actions would certify illustrative
   1% and 0.1% conditional error targets at one-sided 95% confidence? These are
   planning calculations, not a qualified policy. Score=1 errors stay visible.
6. Can a valid type/transaction guarantee truth? Construct explicit score=1 false
   assertions, overlapping temporal contradictions, copied-source evidence, and
   one wrong identity bridge joining 2/10/100-record clusters. Distinguish
   expected limitation witnesses from invariant failures; do not call injected
   scores Jev outputs. Do not silently change the runtime to hide counterexamples.
7. Does dependency-aware repair work under varied graphs? Test seeded DAGs,
   cascading withdrawals, retries, and reopen against an independent oracle.
8. Supply a fresh-input semantic challenge with public, synthetic, human-review-
   required labels, gold-free exports, exact input hashing, missing/error/abstain
   accounting, and a backend-neutral prediction-journal evaluator. No synthetic
   or missing model predictions may be labeled measured Jev results.

## Comparators and decisions

Use the original generic and few-shot Jev arms unchanged. Include explicit
accept-none and gold-oracle analytical controls where useful; neither is a
competitive model. Use the actual deterministic graph compiler for mechanism
ablations. Do not claim a KARMA, structured LLM, NLI, graph-ML, or fresh Jev run
without authentic outputs and matching inputs. A future benchmark must compare
these systems on the same candidates and independently adjudicated corpus,
with candidate generation, latency, retries, review burden, and cost included.

Report all panel results including unfavorable/null outcomes. Never choose new
thresholds using evaluation labels. Bootstrap percentiles are exploratory,
pointwise, source-component-resampled estimates, not familywise significance or
proof of equivalence. Candidate-loss quantiles describe intervention variation,
not statistical confidence. Empty denominators are null, not perfect scores.

## Provenance

The runner must validate the existing frozen artifacts, label each result as
recorded, synthetic intervention, mechanism witness, or analytical projection,
and emit deterministic JSON plus a written report. Unit tests and CI use no
model API and no secrets. New external model execution remains unperformed
unless separately documented with actual request/response journals.
