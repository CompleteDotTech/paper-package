# Additional tests of Jev for graph synthesis

Read the [executed results](RESULTS.md), [research addendum](PAPER_ADDENDUM.md),
[protocol](PROTOCOL.md), and [machine-readable reference](results.json).

This extension adds **65 regression tests**, eight falsification panels, and
**48 public synthetic semantic challenge cases in 12 families**. The existing
123 extension tests and these 65 tests pass together: **188 tests**. The 161
frozen original evidence files are unchanged. These numbers are local execution
results; evaluate the PR-head CI status separately.

The new analyses reuse authentic recorded model outputs, but there are **zero
fresh model calls**. Constructed scores, source removals, and theoretical
prevalence projections are separately labeled. The 48 semantic cases have NOT
been evaluated by Jev or any external baseline. Passing the regression suite
reproduces both strengths and known counterexamples; it does not declare Jev
safe or all stress scenarios successful.

## Reproduce without credentials or model calls

From the repository root, using Python 3.12:

```sh
python -B -m unittest discover -s graph_synthesis/tests -v
python -B -m graph_synthesis.verify --output ../frozen-verification.json
python -B -m graph_synthesis.falsification --check
python -B -m graph_synthesis.falsification --output ../falsification/results.json
python -B -m graph_synthesis.semantic_challenge --export ../challenge-inputs.jsonl
```

The new modules use only the standard library. The preserved full original
replay has its own pinned dependencies and dataset acquisition procedure; see
the existing graph-synthesis reproduction guide. The new workflow has read-only
repository permissions and never exposes model credentials.

## What was added

| Panel | Evidence class | Question |
|---|---|---|
| Shared-error/incorrect-agreement counts | Recorded decisions | Are two formulations independent corroborations? |
| Complete-and-clean candidate components | Recorded decisions | Does improved precision preserve complete neighborhoods? |
| 2,000-draw paired component bootstrap | Exploratory resampling | What is uncertainty at each arm's unchanged operating point? |
| 100-seed source-level candidate removal | Synthetic intervention on recorded decisions | How much can omitted candidates limit recall? |
| 1–90% prevalence projection | Analytical, fixed empirical TPR/FPR | Does high curated prevalence conceal false-positive risk? |
| Score=1 errors and sample-size planning | Recorded + analytical | Does numerical certainty qualify automatic writes? |
| Semantic/temporal/copy/identity witnesses | Constructed, not Jev | What can the deterministic compiler fail to guarantee? |
| 20 seeded dependency DAG repair episodes | Constructed, real runtime | Are cascading retractions, rollback, retries and reopen correct? |

The new bootstrap does **not** match accepted counts. Do not confuse it with
prior matched-budget comparisons, whose intervals included zero. Identity
positive actions here mean `same`; `different` remains a valid decision but is
not counted as a positive identity merge. All candidate nodes participate in
component construction, even when their model decision fails or produces no edge.
Component accounting is regenerated from source, with a digest in results.json.

## Fresh-input semantic challenge

`challenge.json` contains hand-constructed, AI-assisted fixture labels requiring
human review. Its families cover direction, negation, time, population scope,
causality, coreference, multi-hop context, conflicting sources, corrections,
schema typing, prompt injection, and irrelevant context. Its 24 paired groups
allow testing both label-changing edits and invariance controls. Cases are
public: they are not a hidden test set, natural-domain benchmark, or human-
adjudicated independent sample. Pairs share context; do not treat 48 cases as
48 independent statistical trials.

The export removes gold labels, rationale, family, and pair metadata. It hashes
state, allowed outcomes, and the task instruction together. Model runs must use
that exact request and journal their actual inputs and raw responses. Never
reuse a frozen SciFact score for a modified challenge input.

After a separately authorized provider run, supply one JSONL file per model and
formulation. The required success-row shape is:

```json
{
  "id": "case-001",
  "input_hash": "<copy the exact 64-character hash from the exported input>",
  "status": "ok",
  "model": "<provider/model/version/formulation identifier>",
  "request_hash": "<SHA-256 of the actual saved request>",
  "response_hash": "<SHA-256 of the actual saved response>",
  "label": "<actual chosen outcome>",
  "probabilities": {"SUPPORTS": 0.0, "REFUTES": 0.0, "NOT_ENOUGH_INFO": 1.0}
}
```

The probability vector above illustrates the schema, NOT a model prediction.
Use `status: error` with a nonempty `error` string, or `status: abstain`; neither
may contain a fabricated label or probability distribution. Missing rows remain
in denominators. Unknown/duplicate IDs, changed inputs, nonfinite or malformed
probabilities, missing provenance, and mixed model IDs are rejected.

```sh
python -B -m graph_synthesis.semantic_challenge \
  --predictions ../actual-one-arm-journal.jsonl \
  --output ../challenge-evaluation.json
```

The evaluator cannot authenticate a provider from caller-supplied hashes. It
always reports `fresh_execution_verified: false`; inspect matching raw journals
independently before describing results as live. Oracle-generated predictions
exist only inside unit tests as evaluator controls, never as saved Jev evidence.

## External baselines still required

The measured model comparators remain the original generic and few-shot Jev
formulations. The actual graph compiler is a deterministic mechanism comparator;
accept-none and gold-oracle calculations are controls, not competitive models.
A fresh benchmark must additionally execute a matched-input structured LLM plus
validator, NLI/entity matcher, graph-ML alternative where applicable, and a
fidelity-audited KARMA pipeline. KARMA's extraction/schema/conflict workflow is
broader than this fixed-candidate study. No such external baseline was run here.

Primary design references, consulted September 18, 2026:

- TypeSafe AI, [Introduction](https://docs.typesafe.ai/introduction): typed judgments and atomic composition, not an end-to-end graph-generation guarantee.
- Lu et al., [KARMA, arXiv:2502.06472v2](https://arxiv.org/html/2502.06472v2), January 11, 2026: multi-agent extraction, alignment, conflict resolution and graph integration; no direct replication is claimed.
