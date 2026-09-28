# Repeated DSPy × Jev × calibration: frozen exploratory protocol

## Estimands and boundaries

Compare all eight original Jev formulations on the complete archived panels. Preserve
primitive type, number of questions, label keys, composition and example content.
Only the instruction and existing criterion text can change. Run five independent
DSPy proposal searches per formulation (seeds 17, 29, 43, 71, 101), each with three
candidate rounds. This is 40 independent searches and at most 120 proposals; it is
not an exhaustive search of all possible prompts and does not invoke GEPA/MIPROv2.

Use Jev `jev-1.13.0`. The available CI secret `TYPESAFE_API_KEY` stays in the inference
step. DSPy uses a real locally executed Qwen2.5-1.5B-Instruct Q4_K_M proposer through
llama.cpp b10964, with the binary and model file verified against published SHA-256
hashes. This modest proposal model is a limitation; do not extrapolate its results
to larger proposal models. It needs no second hosted-provider credential. No secret
values, full secret contexts, or provider authorization headers enter artifacts.

## Data

Read the archived original `plan.json` without modifying it. Split its 60 development
examples per task, hash-ordered and class-stratified, into 31 TRAIN and 29 VALIDATION
examples. Reject any overlapping source/identity units or identical input states
between train, validation, original demonstrations, calibration and original test.
Keep the original six demonstrations fixed for the few-shot arms; do not use them
as new feedback cases. The calibration splits have 150 relation and 390 entity rows.

Full evaluation panels: SciFact supplied-evidence classification (339); DBLP–ACM
entity resolution (413); historical relation fixtures (50); historical entity
fixtures (100); additional SciFact corpus (336); relationship challenge (48).
Challenge/fixture metrics are diagnostic and not independent real-world estimates.
The additional corpus is evaluated as a transfer panel for each original formulation;
this alone does NOT rerun all seven multi-call graph workflows with DSPy.

The test panels and earlier results are already public and were previously inspected.
This is an exploratory re-evaluation, not a new untouched external benchmark. No
holdout examples, labels, scores or calibrator results are sent to the proposer.

## Search, selection and freezing

Restart each seed from the exact original formulation. The proposer receives four
training observations sampled from up to eight hardest cases, including state,
gold label and probabilities. States longer than 2,400 characters are truncated
and explicitly marked; Jev always sees the complete input. Candidate instructions
are bounded to 3,500 characters and criteria to 1,500 each. Reject schema changes
and malformed proposals. A candidate replaces the incumbent only on strict
validation-accuracy improvement. Also retain the minimum-validation-NLL candidate
from that SAME candidate pool as a calibration-aware selection ablation. This is
not an independently optimized NLL search. Preserve all proposal traces and rejects.

All five searches finish and are hash-frozen before calibration or holdout inference.
For each formulation jointly evaluate baseline + five accuracy champions + five NLL
champions in a single multi-question request per example; they share identical state
and cannot see each other's outputs. This controls the final-call context between
arms, but differs from historical single-question execution. Do not label the new
numbers byte-identical reproduction or independent Jev measurement replicates.

## Calibration

Evaluate all variants raw, with scalar temperature scaling, and with temperature
plus zero-sum class biases. Fit only on the original disjoint calibration split by
NLL, never on test. Use log-probabilities clipped at 1e-15; log-temperature bounds
[-3,3], bias coordinate bounds [-3,3], bias ridge penalty 0.01. Fall back to identity
when optimization fails or worsens the calibration objective. Temperature alone
preserves argmax and therefore cannot improve classification accuracy. Bias terms
can change decisions; attribute these changes separately.

## Endpoints and uncertainty

Accuracy, macro-F1, MCC, full confusion matrices, per-class counts, Brier score,
NLL, ECE at 5/10/15/20 bins, area under the risk–coverage curve, wrong/correct
positive graph edges, actual calls/tokens and estimated Jev cost. Report every seed,
mean, standard deviation and range; do not cherry-pick the best test seed or pool
five uses of the same test examples as five independent datasets. Summarize paired
source-group uncertainty and calibration deltas separately. Multiple panels,
formulations and calibrators are exploratory comparisons, not confirmatory tests.

No additional question/type/topology optimization, retraining of archived specialist
models, or automatic production policy promotion is claimed. Existing deterministic
graph experiments are rerun by repository CI as regression/replay evidence, not new
semantic accuracy measurements. Keep their coverage separate from live comparisons.

## Execution budgets and reproducibility

At most 10,000 Jev HTTP attempts and 40 million reported input tokens per formulation;
two workers, at least 0.8 seconds between request starts per job; eight jobs maximum.
Retry transient failures at most twice. Authentication failures stop immediately.
Unknown usage on failed requests can mean billed cost exceeds reported successful
usage; estimates are not invoices. Record payloads, model, timestamps, latency,
responses and failure codes, never headers. No cross-seed Jev cache replay is called
a new run. Identical incumbent evaluations may be reused only within one search.

Pin dependencies and preserve their resolved environment. Archive raw compressed
journals and all source/data/configuration hashes. Existing frozen root MANIFEST
and prior research artifacts remain unchanged. A failure or approval requirement
is reported explicitly; missing runs must never be replaced with simulated results.
