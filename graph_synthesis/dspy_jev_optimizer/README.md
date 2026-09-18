# DSPy × TypeSafe AI Jev prompt optimizer

Starter experiment for using **DSPy as an outer proposal loop** around **TypeSafe AI Jev as the typed decision/evaluation model**.

> This is additive starter code, not a completed empirical result. It does not change or reinterpret the repository's frozen Jev evidence.

## Architecture

- [GitHub-native Mermaid](architecture.md)
- [Raw Mermaid source](architecture.mmd)
- [High-definition vector render](architecture.svg)

The Mermaid diagram is the canonical architecture. The SVG is a publication-oriented vector companion of the same five-stage loop. No generative image tooling was used.

## What the loop does

1. Evaluate the incumbent Jev question on TRAIN and retain mistakes plus probabilities.
2. Give DSPy the task, fixed label keys, current instructions/criteria, and representative TRAIN failures.
3. DSPy proposes revised Jev `instructions` and `criteria` wording while preserving label keys.
4. Jev evaluates the candidate on VALIDATION.
5. The champion gate defaults to **validation accuracy**. Macro-F1 or a calibration-aware composite can be selected explicitly.
6. Promote only an improving candidate; persist every candidate and metric.
7. Freeze the search budget.
8. Evaluate HIDDEN TEST only after the loop is frozen; never feed that result back into optimization.

TypeSafe's current docs define `Choice` questions with `instructions` and `criteria`, returning a choice plus probabilities/confidence. They also recommend decomposing complex judgments into focused typed questions and composing the answers in code:
- https://docs.typesafe.ai/primitives
- https://docs.typesafe.ai/introduction/quickstart

DSPy documentation: https://dspy.ai/

## Quick start

```bash
cd graph_synthesis/dspy_jev_optimizer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

export TYPESAFE_API_KEY="..."
export OPENAI_API_KEY="..."        # or credentials for your DSPy proposal model
export DSPY_PROPOSER_MODEL="openai/gpt-5.4-nano"

python optimize.py \
  --config baseline-config.json \
  --train sample-train.jsonl \
  --validation sample-validation.jsonl \
  --iterations 12 \
  --selection-metric accuracy \
  --output optimizer-output
```

The optimization command does **not** read the hidden test.

After the budget is frozen:

```bash
python optimize.py \
  --config optimizer-output/optimized-config.json \
  --train sample-train.jsonl \
  --validation sample-validation.jsonl \
  --iterations 0 \
  --test sample-test.jsonl \
  --output final-audit
```

With `--iterations 0`, DSPy is not invoked and no candidate is proposed.

## Metrics

Every evaluation records:

- accuracy
- macro-F1
- multiclass MCC
- multiclass Brier score
- log loss
- 10-bin expected calibration error
- a composite quality score

The default champion gate uses accuracy, matching the highest-accuracy objective. For class imbalance use `--selection-metric macro_f1`. The optional composite is:

```text
0.55 × macro_F1
+ 0.20 × accuracy
+ 0.15 × (1 - multiclass_Brier / 2)
+ 0.10 × normalized_MCC
```

## Guardrails

- Never optimize on HIDDEN TEST.
- Preserve the label schema during a run.
- Cache calls by state + Jev configuration.
- Record malformed/rejected candidates, not only winners.
- Pin proposer/Jev versions and dependencies for a paper-quality experiment.
- Freeze split, metric, search budget, and stopping rule before final evaluation.
- Repeat across multiple search seeds before attributing gains to the method.
- Report null and negative results as well as improvements.

## Next research step

Expand the search space from one `Choice` question to a typed Jev decision graph:

```text
candidate genome
├── Choice / Noul / Score question types
├── number of atomic questions
├── instructions and criteria
├── composition weights
├── decision thresholds
└── abstention / escalation policy
```

That tests **workflow optimization**, not merely prompt wording, and should be treated as a separate preregistered experiment.
