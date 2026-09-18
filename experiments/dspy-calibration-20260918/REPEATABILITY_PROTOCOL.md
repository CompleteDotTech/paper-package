# Post-freeze repeatability and original batching layout

This diagnostic extension is fixed before reading amendment-v2 test scores. It makes
no new proposals and does not change any primary prompt, selection rule or calibrator.
Use every completed original formulation's baseline plus all five frozen accuracy
champions. Do not select a favorable seed. Native service variation is separate from
prompt-search variability and must not be credited as DSPy improvement when a prompt
is unchanged.

For each task, rerun the original 20 evaluation `repeatability_ids` three times.
For the original 20 development `batching_ids`, compare a shared request containing
all non-few-shot formulations against individual formulation/seed requests. Few-shot
input retains its six demonstrations and is placed in a separate shared-state bank.
This preserves the original grouping rule while expanding it to baseline plus five
DSPy variants. Each row has 24 configurations overall: 18 ordinary, six few-shot.

There are 120 repeated-evaluation requests, 40 batched development requests, and 480
individual development requests per task: 640 successful requests per task, 1,280
across both tasks, before retries. Requests are limited to two workers and minimum
0.8-second spacing per task, at most 2,000 attempts and the existing token limit.
Authentication failures and distributions outside the amendment-v2 interpretation
stop execution. Original probabilities and raw responses are retained.

Evaluate raw, temperature, and temperature-plus-bias probabilities on the repeatability
panel using only the already-fitted, disjoint primary calibrators. Report seed-wise
means over three service replicates, between-seed dispersion, and within-seed service
dispersion separately. Twenty repeated inputs remain twenty inputs, not 300 new test
examples. These originally selected diagnostic panels are not population estimates.

Record label/probability disagreement across repeats and between batched/individual
requests. Individual request ordering is shuffled deterministically within that phase;
batched and individual phases are not randomized across server load. Therefore
latency comparisons are descriptive, not a controlled hardware-throughput claim.
Report actual input usage per isolated baseline/DSPy prediction and packing savings
for identical configurations/examples. Optimizer overhead, local proposer CPU and CI
runtime are separate from deployment inference costs.

No label-accuracy claim is made from the development batching panel. Every request,
probability, calibration transformation and metric is reconstructed in a network-free
audit. Partial task captures must never be represented as the complete comparison.
