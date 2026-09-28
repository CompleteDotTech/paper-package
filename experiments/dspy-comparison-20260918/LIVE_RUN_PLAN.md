# Authorized five-seed comparison run plan

Status: **first live attempt failed; no five-seed results yet**. The user approved the existing
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
- Registered upper bound: 65,000 logical Jev requests and 160 proposal calls
  across five seeds. Automatic Jev SDK retries are disabled for this execution.
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
  allowance. All 160 reserves sum to **$11.20**.
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
