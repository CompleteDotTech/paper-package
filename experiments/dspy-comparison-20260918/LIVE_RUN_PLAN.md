# Authorized five-seed comparison run plan

Status: **one standalone seed completed; the comparable five-seed cohort is pending**. The user approved the existing
OmniRoute DeepSeek route and a **$50 total spending cap** on 2026-09-28.
The earlier instruction to use captures only applied to the prior PR remediation;
this is a new authorized live run. It remains distinct from the published v2
captures in PRs #28–#30.

## Routing and cost basis

- Jev target: pinned `jev-1.13.0`, using the repository TypeSafe Actions secret.
- DSPy proposer: `openai/ollamacloud/deepseek-v4.1-flash` through the dedicated,
  model-restricted OmniRoute gateway key. The key is held in GitHub Actions as
  `OMNIROUTE_DEEPSEEK_API_KEY`; the workflow pins the HTTPS gateway base URL.
  Neither key value is committed or printed.
- Registered upper bound: 65,000 logical Jev requests and 160 accepted proposal
  slots across five seeds. The execution amendment permits at most 100 extra
  invalid-answer Jev calls and 100 extra malformed-proposal calls across those
  seeds. At most 100 extra Jev calls across five seeds may also follow logged
  transport timeouts. Automatic Jev SDK retries are disabled for this execution.
- [TypeSafe's public Jev price](https://typesafe.ai/) is $0.042 per million input
  tokens with output free. In the previous, different v2 run, 12,829 primary
  attempts consumed 24,465,570 reported input tokens, about 1,907 per attempt.
  At that rate, 65,000 requests would cost about **$5.21**. This is an estimate,
  not a token bound for the new prompts.
- [Ollama's published DeepSeek V4.1 Flash price](https://www.ollama.com/pricing)
  is $0.30 per million input tokens and $1.20 per million output tokens at peak
  rates; off-peak can be lower. With at most 16,384 output tokens, $0.07 per
  proposal covers 120,000 input tokens and model output at peak rates.
  The 120,000-byte serialized proposal-input guard is tighter than that token
  allowance. The 160 initial reserves sum to **$11.20**; the maximum 100 parse
  retries raise that reservation to **$18.20** if all are used.
- The controlled runner limits each seed to an $8 estimate from reported Jev
  usage plus conservative proposal reserves. Seeds are dispatched individually,
  with observed token usage and provider billing reviewed before another seed.
  Five per-seed limits total $40, leaving a $10 buffer under the $50 cap for
  in-flight usage and accounting differences. Do not dispatch another seed if
  cumulative actual spend plus the next seed's $8 allowance would exceed $50.

## Execution and publication gates

1. Run offline regressions and frozen inventory; confirm the dedicated gateway
   route and both named secrets are available without showing their values.
2. Dispatch seed 11 only. Inspect status, `cost-budget.json`, raw logs, usage,
   and billing. Failed or incomplete seeds stay failed; never fill them with
   a baseline-only or archived result.
3. If cost and quality gates hold, run seeds 23, 37, 53, 71 one at a time. Keep
   original run IDs and downloaded artifact SHA-256 receipts. Stop on model drift,
   missing usage, budget exhaustion, malformed response, credential failure or
   unexpected aggregate cost.
4. Independently verify every seed's inventory, merge five seed artifacts in a
   new directory, run the aggregate report, and publish raw traces and complete
   findings with exact limitations. No test-score selection across seeds.

This plan and its price arithmetic do not prove that the gateway has enough
credits or that every run can finish inside the hosted job timeout.

## Failed first attempt and execution amendment

Run [36478661190](https://github.com/CompleteDotTech/paper-package/actions/runs/36478661190)
used the authorized seed 11 and stopped after 60 successful Jev calls and one
DeepSeek proposal attempt. The gateway returned 4,096 completion tokens of
reasoning with an empty answer, so DSPy's JSON adapter raised
`AdapterParseError`. Its artifact records 55,087 Jev input tokens and a
$0.052313654 estimate, including a $0.05 proposal reserve. The failed attempt
is preserved as a failed run and is excluded from study results. For the next
attempt, the same method uses a 16,384-token proposal output ceiling and a
$0.07 reserve per call. This changes only the execution ceiling and accounting;
the frozen data, feedback, search iterations, and acceptance rule stay fixed.

The next retry, [run 36479509726](https://github.com/CompleteDotTech/paper-package/actions/runs/36479509726),
obtained a complete proposal (6,410 input and 6,442 output tokens) but failed
while writing its audit row: LiteLLM's usage object contained a nested wrapper
that `json.dumps` could not serialize. It again completed 60 Jev calls and is
excluded from results. Its guarded estimate was $0.072313654. The audit writer
now records only scalar token counts and a numeric cost. This changes no model
request or study rule.

The third attempt, [run 36479851803](https://github.com/CompleteDotTech/paper-package/actions/runs/36479851803),
completed four proposal calls and 183 accepted Jev responses, then one Jev
response failed validation. Its `request_failed` event contains only the
exception class `ValueError`, so the specific failing check cannot be recovered
from this attempt. The guarded estimate was $0.289215304, including 219,412
Jev input tokens and four $0.07 proposal reserves. It is excluded from results.
For the next attempt, a response with the wrong fixed answer schema or invalid
probabilities is logged and retried against the same request, with at most 20
such extra calls per seed. Every returned response's tokens count toward the
$8 seed cap, including rejected answers. A model-ID mismatch, missing usage, or
other provider error still stops the run. The retry changes no example,
candidate, score, or acceptance rule; the extra physical calls are explicitly
recorded in `cost-budget.json` and the raw event log.

The fourth attempt, [run 36480687828](https://github.com/CompleteDotTech/paper-package/actions/runs/36480687828),
completed six proposals before the seventh returned JSON without the required
`improved_criteria` field. It recorded 281,416 Jev input tokens, seven proposal
attempts, zero invalid-answer retries, and a $0.501819472 guarded estimate.
It is excluded from results. For the next attempt, a DSPy JSON parse failure
may be retried twice for the same frozen feedback and iteration, up to 20 extra
proposal calls per seed. Each failed parse has an audit row, and each retry adds
a $0.07 reserve. Other proposal errors still stop the run. The logical search
still requires exactly eight accepted candidate proposals per objective.

The fifth attempt, [run 36482250053](https://github.com/CompleteDotTech/paper-package/actions/runs/36482250053),
completed all 16 relation-support proposal slots and froze that task's
calibration. During control evaluation, two TypeSafe requests timed out after
the SDK's 30-second timeout. The run recorded 5,815,753 successful Jev input
tokens, five invalid-answer retries, zero proposal parse retries, and a
$1.364261626 guarded estimate. It is excluded from results. The next attempt
permits up to two retries of a timed-out request and 20 extra timeout calls per
seed. Every timeout and retry has an event, and each timed-out call reserves
$0.05 for usage that the provider did not return. A non-timeout provider error
still stops the run. The logical example and scoring remain unchanged.

## Cohort restart after independent review

[Run 36484331133](https://github.com/CompleteDotTech/paper-package/actions/runs/36484331133)
completed seed 11 under source commit `f0fcb78`. Its inventory verifies, with
294 metric rows and 32 accepted proposals; its guarded estimate was
$2.888279926. The artifact ZIP digest is
`ddb51ffb12999165ca55f6aed4459b1c66d636bf0142c9ef0c7768db890c3c16`.
It remains valid standalone evidence, but does not enter the final five-seed
cohort because the dispatcher and provenance checks changed afterward.

[Run 36487767662](https://github.com/CompleteDotTech/paper-package/actions/runs/36487767662)
was canceled when the independent review found the eager dispatch budget flaw.
Its partial artifact and a local snapshot are preserved. It recorded nine
accepted proposals and 368 Jev responses; a conservative upper estimate from
their usage, proposal reserves, and one possible in-flight proposal is
$0.719464858. It is excluded from results. The five earlier failed seed-11
attempts plus the successful standalone seed and this cancellation total about
$5.89 in guarded estimates. Five fresh $8 seed limits add at most $40, leaving
about $4.11 under the authorized $50 cap, subject to review after every seed.

The final cohort reruns all five seeds on one source/data/dependency snapshot.
Target requests are now dispatched in batches of at most four after a $0.05
reserve per request. The actual serialized state, question, and any few-shot
demonstrations must fit 120,000 bytes. Each returned usage settles its reserve;
an unknown usage retains the reserve. The aggregate validator requires the
exact 294-row arm/panel/calibration matrix per seed and rejects mixed protocol,
source, dependency, or data inventories.
