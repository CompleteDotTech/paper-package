# Frozen multi-call transfer comparison

This additive protocol is fixed before reading any new benchmark test result.
It extends the question-level comparison to all seven existing multi-call workflows:
`single`, `repeat_vote`, `blind_vote`, `targeted`, `structured`, `contrastive`, and
`selective`. Use unchanged `graph_synthesis.multicall.payloads` and `decisions` to
retain the original workflow logic, demonstration sets and threshold (0.9).

Use the exact baseline few-shot question and **all five** accuracy-selected prompts
from the frozen `relation_support/fewshot_contract` DSPy search. Do not choose a seed
by test performance, make new proposals, inspect test errors for tuning, or reuse
prior Jev responses as fresh observations. The intervention changes only the
primary verifier question, including its uses in the structured and contrastive
input variants. Blinded reviewers, dimension checks and adjudication instructions
stay fixed. This is prompt-transfer evaluation, not optimization of all workflow
components or graph topology.

Evaluate 150 original disjoint calibration examples and all 336 additional-corpus
examples. Report both the original additional-corpus development and test subsets,
as well as the full transfer panel; neither subset is used for this prompt search.
The published nature of these examples limits external generalization claims.

At each row, three repeated primary-verifier calls plus the structured and
contrastive calls batch the baseline and five prompts with the same state. One
common call evaluates the two blinded reviewers and six dimension checks. Six
separate adjudication calls preserve each variant's own candidate/check state.
Thus a complete run has 12 HTTP successes per row (5,832 overall), before retries.
The shared control reviewers reduce nuisance variation; they are not six
independent control replications. Call journals retain complete requests and
responses without authorization headers.

Keep the original workflow decisions, abstentions and escalation rules for all
primary label metrics. For repeat/blind voting, separately record the arithmetic
mean of the three component probability vectors as a normalized forecast. This
forecast is not an independence product and its argmax need not equal the vote.
Abstentions remain abstentions; count them as incorrect in unconditional accuracy
and report coverage and conditional accuracy explicitly.

Fit scalar temperature and temperature-plus-bias on only the 150 calibration
forecasts, with the same fixed bounds/ridge as the question-level protocol. These
are **decision-frozen forecast calibrations**: they do not change the original
votes, abstentions, escalation or adjudication inputs. Report forecast Brier/NLL,
forecast argmax accuracy, and policy-label accuracy as distinct quantities. Do not
claim post-hoc score calibration improved the unchanged workflow decisions.

Use Jev `jev-1.13.0` and eight deterministic row shards. Per shard: two workers,
0.8-second minimum request-start interval, at most 2,000 attempts and 40 million
reported input tokens, bounded retries and immediate authentication stop. Preserve
partial evidence on failure. No missing shard may be silently omitted from a full
comparison. Frozen evidence and the original root manifest are not rewritten.
