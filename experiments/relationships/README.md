# Relationship score-fusion experiments

## Finding

Combining the two saved Jev formulations does **not establish a relationship-quality improvement over the existing few-shot baseline**. Equal probability averaging has a slightly higher operational macro-F1, but its paired interval includes zero. Agreement gating reaches 90% pooled edge precision by accepting fewer edges; the same precision is achieved by the few-shot baseline at the matched 190-edge volume. A calibration-trained stacker performs worse descriptively. No experimental arm is promoted into a production acceptance policy.

This is a completed exploratory post-hoc experiment over authentic frozen responses, not fresh Jev inference, new independent data, or a claim of better open-corpus graph synthesis. The tested edges are `Document -> supports/refutes -> Claim`, not arbitrary domain predicates. The original manuscript and all frozen evidence files remain unchanged.

## Abstract

We evaluate whether two correlated formulations of the same Jev model can produce better evidence-graph edges when their probabilities are combined. We compare the original generic Choice and few-shot formulations with equal-weight averaging, agreement-only acceptance, and a regularized multinomial score stacker. The stacker is selected using component-grouped cross-validation confined to the original calibration data. On 339 previously inspected SciFact examples, averaging changes macro-F1 from 0.852728 for the few-shot formulation to 0.853759, a difference of 0.001031 with an exploratory paired 95% interval of [-0.019901, 0.023213]. Agreement gating removes one incorrect and one correct edge relative to the unfiltered few-shot arm. At matched volume their correct/incorrect edge counts are identical. The fitted stacker reaches macro-F1 0.834220. These findings do not justify replacing the existing formulation. The contribution is an executable, provenance-bound experiment with honest null and negative results, matched-volume comparisons, and graph-lifecycle checks.

## Protocol and selection

The [protocol](PROTOCOL.md) was committed at `51803661e3b8913f1a81cfc394954f0b517e95a0` before the new combination experiments ran. The evaluation set had already been inspected in earlier research, so this is not a blinded confirmatory study. [Implementation and packaging clarifications](AMENDMENTS.md) describe subsequent numerical, provenance, and storage details without changing the arm definitions or selection objective.

The two original arms use unchanged probabilities reconstructed from their raw saved calls by `RecordedJev`. Ensemble arms require both valid constituent responses. An invalid response remains an operational error; disagreement in the agreement-only arm is an explicit abstention, not a correct NOT_ENOUGH_INFO prediction.

The fitted arm uses six clipped log-probabilities, training-fold-only standardization, an unpenalized intercept, and regularized multinomial logistic regression. Five folds are assigned by a label-independent hash of connected claim/document component IDs. The grid is lambda = 0.01, 0.1, 1, 10. Pooled out-of-fold macro-F1 selects lambda 0.01; ties use negative log-likelihood then stronger regularization. Refitting uses 149 common-success calibration rows from 150 original rows. The 73 calibration components do not overlap the 247 evaluation components. The fitted model and selection summaries are in [reference/model.json](reference/model.json).

Evaluation labels enter metrics only. They are not accepted by prediction functions, used to fit the stacker, or used to construct graphs. No variant or hyperparameter was introduced after inspecting this experiment's results to manufacture a gain.

## Results

| Arm | Macro-F1 | Correct edges | Incorrect edges | Edge precision | Edge recall |
|---|---:|---:|---:|---:|---:|
| Original generic Choice | 0.850824 | 187 | 37 | 83.48% | 89.47% |
| Original few-shot contract | 0.852728 | 172 | 20 | 89.58% | 82.30% |
| Equal probability average | 0.853759 | 179 | 27 | 86.89% | 85.65% |
| Agreement-only gate | 0.847081 | 171 | 19 | 90.00% | 81.82% |
| Calibration-trained stacker | 0.834220 | 177 | 35 | 83.49% | 84.69% |

Operational metrics use all 339 examples. The generic and few-shot arms have one and two invalid responses respectively; all ensemble arms have three because they require both inputs. Agreement gating additionally abstains on 33 examples. Common-success results on 336 examples are included in the machine-readable output. Edge precision divides correct typed edges by accepted edges; edge recall divides correct typed edges by all 209 gold SUPPORTS/REFUTES examples. Wrong relation polarity counts as an incorrect edge and a missed gold edge.

The fitted arm changes macro-F1 by -0.018508 relative to few-shot, with interval [-0.051785, 0.012961]. Averaging versus the generic baseline changes macro-F1 by +0.002934, with interval [-0.020706, 0.028364]. The intervals include zero; they do not establish equivalence or an improvement.

### Compare at the same edge volume

At 190 accepted edges, both agreement gating and the few-shot baseline retain 171 correct and 19 incorrect edges: precision 90%. At 192 edges, averaging retains 171 correct and 21 incorrect, versus 172 correct and 20 incorrect for few-shot. At 206 edges, averaging and the generic baseline both retain 179 correct and 27 incorrect. Thus the unfiltered precision changes must not be presented as a demonstrated superior precision/coverage tradeoff.

[Generated tables](TABLES.md) report all ten pairwise matched-volume comparisons. The complete results also include per-predicate comparisons, fixed budgets from 25 to 200 where available, boundary ties, confusion matrices, source-use accounting, and graph audits. Ranking uses scores and stable identifiers only. Exact-K tie-breaking is a descriptive procedure, not a probability-threshold risk policy.

Uncertainty uses 2,000 paired bootstrap draws over connected evaluation components. Matched-volume intervals condition on the original ranked sets, so resampled accepted denominators can differ. These intervals do not rerank, refit, repeat selection, correct for multiple comparisons, or account for distribution shift.

## Graph consequences and operational cost

All arm outputs are materialized through the existing evidence-preserving graph store. Correct/incorrect committed assertions agree with the independently counted typed-edge metrics. Controlled source withdrawal, audit verification, and reopening are exercised. Combined decisions retain resolvable provenance to both source calls, their actual probabilities, and the fitted transformation. Their synthetic combined identifier is not a vendor call identifier. Valid graph transactions do not certify factual truth.

There are **zero fresh HTTP calls and zero new Jev usage in this execution**. The existing generic evaluation calls used 258,495 input tokens and the few-shot calls used 1,213,458. Each two-formulation arm depends on 678 recorded calls and 1,471,953 input tokens, compared with 339 calls for either original arm. A live deployment would need both formulations; replay does not make those additional inference requirements disappear. These formulations are correlated judgments, not independent sources of corroborating evidence.

## Reproduce and audit

From the repository root, with the repository's pinned numerical dependency installed:

```bash
python -m pip install -r reproduction/requirements-jev.txt
python -B -m unittest discover -s graph_synthesis/tests -v
python -B experiments/relationships/reproduce.py --output ../relationship-results
```

The output directory must be new or empty and outside the repository. No credentials, model weights, or dataset download are needed for the relationship replay. Dependency installation itself may require network access. The initial local run used Python 3.13.5 and NumPy 2.3.5; CI exercises the repository's pinned dependency with Python 3.12 on Linux and Windows. Environment information is recorded separately rather than mistaken for bitwise-independent replication.

`reference/results.json.gz` stores the complete numerical comparison reference. `reference/model.json` stores the fitted transformation, training IDs, and selection summaries. `reference/REFERENCE.json` identifies the local full outputs and enforces the exact fitted-transform hash and exact decompressed evaluation-journal hash. Full `selection.json`, `expanded-decisions.jsonl`, `decisions.csv.gz`, results, environment, and verification are regenerated and archived by CI. The reference comparator permits floating-point noise at absolute/relative tolerance 1e-8 while requiring exact structures, labels, integer counts, and hashes. The 90-day CI artifact retention is not a permanent archive; all journals remain reproducible from the committed inputs and code.

## Limitations and disposition

Only 150 calibration examples and one previously inspected evaluation population are available. Agreement is not independent evidence. The stacker's calibration-selection advantage does not establish generalization. There is no independent new-corpus test, fresh remote inference, new domain-relation extraction, candidate-retrieval measurement, validated transaction-level risk bound, or direct KARMA run. No production behavior is changed.

The next scientifically informative evaluation would use fresh component-disjoint data and test new evidence or relation-specific decisions rather than retuning these same evaluation outcomes. This PR preserves the present negative findings instead of claiming that an unsuccessful fitting experiment improved relationships.

## Source trail

The experiment is grounded in the [original manuscript](../../manuscript/paper.md), [saved Jev run](../../reproduction/results/jev/run-20260918), [recorded-response adapter](../../graph_synthesis/recorded.py), and [graph lifecycle implementation](../../graph_synthesis/core.py). The new [fusion module](../../graph_synthesis/edge_fusion.py), [runner](../../graph_synthesis/edge_experiment.py), and [tests](../../graph_synthesis/tests/test_edge_fusion.py) define every derived result. This note is an AI-assisted experimental report, not an assertion of independent human peer review.
