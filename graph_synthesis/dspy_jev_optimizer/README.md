# DSPy × TypeSafe AI Jev: implemented prompt optimization

A runnable **DSPy proposal → Jev prediction → validation selection** loop for one
`Choice` question. It improves candidate instructions and criterion definitions;
it does not train Jev weights, implement GEPA/MIPROv2, or search graph topology.
Improvement is measured, not guaranteed. The selected winner is the best **observed**
validation candidate under the configured budget, not a global accuracy optimum.

[Mermaid architecture](architecture.md) · [Mermaid source](architecture.mmd) ·
[Vector diagram](architecture.svg) · [Core](core.py) · [SDK adapters](providers.py) ·
[Tests](tests/) · [CI](../../.github/workflows/dspy-jev-optimizer.yml)

## What changed from the starter

The proposer now sees the actual TRAIN states alongside labels, mistakes, and
probability distributions. VALIDATION controls promotion but is never included in
that feedback. `optimize` has no test argument. `evaluate` separately loads a test
set after verifying a frozen run, and compares the baseline and champion on the
same examples. Duplicate IDs, identical states, and optional source/entity groups
are rejected across splits before any model evaluation.

Every run saves its initial configuration, model/SDK identity, source hashes,
dataset fingerprints, budgets, proposals (including rejected and malformed ones),
raw Jev requests/responses, and selected configuration. Baselines are saved even
with zero optimization iterations. Exceptions stop the run rather than silently
turning infrastructure failures into model errors.

The archived research `MANIFEST.json` is restored to its original Git blob
`a8d9f447c266fbedf8837003ceb9639e00778b0e`. This extension has its own
[artifact-manifest.json](artifact-manifest.json); it does not rewrite the
161-file frozen evidence package or claim new research results.

## 1. Run the offline demonstration

From the repository root, using Python 3.12 or newer:

```bash
python -B -m graph_synthesis.dspy_jev_optimizer.optimize demo \
  --output graph_synthesis/dspy_jev_optimizer/runs/demo \
  --cache graph_synthesis/dspy_jev_optimizer/.cache/demo.sqlite3
```

No dependencies, network, or API keys are required for this command. It uses a
scripted proposer and scripted predictions to exercise selection, caching,
freezing, and final evaluation. Its metrics are **synthetic test fixtures, not Jev
accuracy or evidence of an empirical improvement**. Output directories must be new.

## 2. Install and configure the live adapters

```bash
python -m pip install -r graph_synthesis/dspy_jev_optimizer/requirements.txt
```

The directly used SDK versions are pinned to `dspy==3.3.1` and
`typesafe-sdk==0.7.0`. Transitive dependencies are resolved by pip; CI archives
`pip freeze` rather than claiming a complete dependency lock.

Set `TYPESAFE_API_KEY`, `DSPY_PROPOSER_MODEL` (a provider/model identifier supported
by your DSPy installation), and that proposal provider's API credential in your
shell or secret manager. No credentials are stored in the repository. There is no
assumed default proposal model. Do not place keys in command arguments or datasets.
The adapter uses the official TypeSafe API endpoint only.

## 3. Optimize on TRAIN and VALIDATION

```bash
python -B -m graph_synthesis.dspy_jev_optimizer.optimize optimize \
  --config graph_synthesis/dspy_jev_optimizer/baseline-config.json \
  --train graph_synthesis/dspy_jev_optimizer/sample-train.jsonl \
  --validation graph_synthesis/dspy_jev_optimizer/sample-validation.jsonl \
  --jev-model jev-1.13.0 \
  --iterations 12 \
  --max-jev-calls 500 \
  --selection-metric accuracy \
  --patience 4 \
  --output graph_synthesis/dspy_jev_optimizer/runs/experiment-001
```

The supplied three-example splits are wiring examples only. Use independently
labeled, representative data for an actual experiment. `--iterations 0` evaluates
and freezes a baseline without invoking DSPy. `--patience 0` disables early
stopping. Ties retain the incumbent; malformed or duplicate proposals do not spend
Jev evaluation calls. `--failure-sample` selects up to 50 training examples; each
serialized state is capped at 6,000 characters and marked when truncated.

The Jev model must be a versioned ID; `jev-latest` and `jev-preview` are rejected.
The service-returned model must match the requested version. The cache identity
includes the model, SDK version, ordered criteria, prompt, and canonical state.
Old starter JSON caches are intentionally not reused.

`--max-jev-calls` limits uncached logical Jev requests in that command, not dollars.
Each request has at most `--retries + 1` SDK HTTP attempts (default retries: 2);
`--timeout` bounds each SDK HTTP operation. Proposal calls have a 60-second provider
timeout and no configured provider retries. Provider/adapter behavior may still
involve multiple requests. There is no strict wall-clock or dollar-cost cap.
Successful uncached Jev token usage and per-call latency are recorded; failed-call
billing and proposal-model costs are not inferred. `cost_usd` is deliberately null.

## 4. Audit a frozen winner, separately

```bash
python -B -m graph_synthesis.dspy_jev_optimizer.optimize evaluate \
  --run graph_synthesis/dspy_jev_optimizer/runs/experiment-001 \
  --test graph_synthesis/dspy_jev_optimizer/sample-test.jsonl \
  --max-jev-calls 500
```

This uses the exact frozen model/SDK settings and checks implementation hashes.
It never invokes the proposer. It scores both baseline and champion, writes paired
predictions, and reports their held-out accuracy difference. The same test does
not influence candidate selection. Only one `final/` audit is allowed for each
frozen run; a failed audit remains visibly failed and is not silently restarted.
Hash checks are reproducibility safeguards, not protection against a user editing
files or copying runs. There is no automatic resume or test-reuse bypass.

## Input format and graph-synthesis use

```json
{"id":"paper-17-edge-2","group_id":"paper-17","state":{"claim":"A supports B","evidence":"Source passage"},"label":"supports"}
```

Use the same fixed criterion keys in every split. IDs must be explicit. `state`
contains only information available at inference time; labels and group IDs stay
outside it. `group_id` is optional, but when used must exist on every example in
every split. Put all edges from the same source paper, and all linked duplicates
that could leak answers, in the same group before splitting. Exact hashes cannot
detect paraphrases or hidden entity overlap; dataset curation must handle those.

For the existing graph compiler's uppercase labels, supply a configuration with
`SUPPORTS`, `REFUTES`, and `NOT_ENOUGH_INFO` and consistently labeled JSONL. This
extension deliberately does not change the compiler's default decision policy or
reinterpret archived predictions. Previously published held-out records are not a
new private test set. Prompt changes require new Jev requests; replaying unrelated
saved responses cannot measure their effect.

## Metrics and artifacts

Accuracy is the default promotion objective. `macro_f1` and `composite` are
explicit alternatives. Every completed evaluation also reports multiclass MCC,
Brier score, log loss, a confusion matrix, class counts, and 10-bin ECE. ECE uses
the probability assigned to the selected label, **not** Jev's separate concentration
confidence. Probabilities must be finite, in range, cover exactly the label set,
and sum to one; invalid distributions fail rather than being silently repaired.
The optional composite is:

```text
0.55 × macro-F1 + 0.20 × accuracy
+ 0.15 × (1 − multiclass Brier / 2) + 0.10 × (MCC + 1) / 2
```

| Artifact | Contents |
|---|---|
| `protocol.json` | Frozen split fingerprints, model/SDK/source identities, baseline and budgets |
| `ledger.json` | Baseline, all proposals, rejection reasons, and completed validation metrics |
| `calls.jsonl` | Exact requests, raw responses, cache hits, and typed failure events |
| `optimized-config.json` | Best observed valid configuration |
| `freeze.json` | Hash-bound champion and baseline comparison, stopping reason |
| `final/metrics.json` | Baseline/champion held-out comparison; never used for tuning |
| `final/predictions.json` | Paired baseline/champion predictions for independent analysis |

**Privacy:** Requests, responses, and failure feedback can contain sensitive source
text. Run folders and caches are locally ignored, never uploaded automatically.
DSPy sends the selected training states to the chosen proposal provider; use only
data you are authorized to send there. Review artifacts before publishing them.

## Tests and integrity

```bash
python -B -m graph_synthesis.dspy_jev_optimizer.verify
python -B -m unittest discover -s graph_synthesis/dspy_jev_optimizer/tests -v

# Additional real-SDK contract tests, with mocked HTTP and a dummy LM:
python -m pip install -r graph_synthesis/dspy_jev_optimizer/requirements-test.txt
python -B -m unittest discover -s graph_synthesis/dspy_jev_optimizer/tests -v
```

CI runs the dependency-free suite on Linux and Windows, then requires the real
DSPy/TypeSafe SDK contract tests on Linux. The SDK tests exercise real serialization,
structured outputs, bounded rate-limit retries, and the complete proposal-to-Jev
loop without live inference. Missing SDKs fail CI's contract job rather than being
silently skipped. Test success establishes software behavior, not Jev task accuracy.

## Primary API references

- [TypeSafe primitives](https://docs.typesafe.ai/primitives)
- [TypeSafe Python SDK](https://docs.typesafe.ai/sdk/python/)
- [TypeSafe model versions](https://docs.typesafe.ai/models)
- [TypeSafe SDK source](https://github.com/typesafe-ai/typesafe-sdk-python)
- [DSPy 3.3.1 source](https://github.com/stanfordnlp/dspy/tree/3.3.1)
