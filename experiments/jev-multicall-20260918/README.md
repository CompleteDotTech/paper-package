# Additional calls and information tests

Read [REPORT.md](REPORT.md), [edge-outcomes.csv](edge-outcomes.csv), [seven figures](figures/), and the [current full paper](../../manuscript/paper-current.md) / [PDF](../../manuscript/paper-current.pdf).

This is a fresh 3,024-call Jev experiment on 336 previously unused SciFact candidates in 189 source groups. The 73 development and 263 test cases are group-disjoint and exclude earlier Jev demonstration/development/calibration/evaluation groups. Public training data is not a private or vendor-training-independent benchmark.

The signed protocol/plan/source commit `2eb44a1` preceded live execution. Calls use Jev 1.13.0. All seven policies and all failures are retained. No test-driven tuning occurred. A clearly labeled common-valid diagnostic was added after observing failures and does not replace operational endpoints.

## Key result

At the same 145 accepted test edges: single 17 errors; repeated vote 17; blind vote 18; targeted checks 19; indexed evidence 19; contrastive examples 17; selective routing 20. More calls did not establish an accuracy advantage. Contrastive examples used 64.70% fewer test tokens but recovered fewer correct edges at the natural operating point; equivalence/noninferiority is not established.

## Artifacts

- `PROTOCOL.md`, `plan.json`, `plan-receipt.json`, `source_snapshot/`: frozen inputs, questions, grouping, limits and implementation.
- `calls.jsonl`: exact payloads and raw service responses, timestamps, hashes, usage, failure and model metadata. Identical-payload repeats have distinct journal sites.
- `predictions.json`, `execution.json`: deterministic seven-arm reconstruction and actual whole-run accounting.
- `results.json`, `edge-outcomes.csv`: all outcomes, source-group intervals, matched-volume selections, costs and error dependence.
- `verification.json`: request reconstruction, raw response validation, source-group isolation and network-disabled replay. CRLF/LF differences are normalized only for generated replay text; original byte hashes are restored before analysis comparison. Counts, labels and structure must match exactly; floating tolerance is 1e-14 absolute / 1e-12 relative.
- `graph-example.json`: first multi-candidate test component by sorted group ID, without selection on outcome quality.
- `figures/`: seven SVG/PNG chart pairs with a source-results hash and figure inventory.
- `artifact-manifest.json`: byte hashes of all run artifacts except itself.

## Offline reproduction

From repository root using Python 3.12:

```sh
python -m pip install -r graph_synthesis/requirements-figures.txt
python -B -m unittest graph_synthesis.tests.test_multicall graph_synthesis.tests.test_multicall_analysis -v
python -B -m graph_synthesis.analyze_multicall --directory experiments/jev-multicall-20260918 --verify
python -B -m graph_synthesis.report_multicall --directory experiments/jev-multicall-20260918
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

Verification/reports require no credentials, downloads or inference. The runtime refuses changed frozen source hashes. Live execution requires explicit `--live` and a process-only `TYPESAFE_API_KEY`; never replace this completed evidence directory to rerun an experiment. PDF rendering also requires WeasyPrint's native font/Pango libraries. Figure content/data is portable; PDF and image bytes may depend on platform/fonts.

Main guardrails: four workers, no retries, maximum 3,500 attempts and 20 million conservatively charged input tokens; actual usage 6,858,163 input tokens, 31 failed calls, no unknown-usage calls. Per-policy costs reuse shared calls; their sum is not actual total spending. Selective routing is a retrospective cost/decision policy over all executed branches, not a separately timed deployment.

The original 161-file archive, prior PR #10–#13 research and all unfavorable results are preserved. No production policy is changed.
