# Visual guide to the graph-synthesis evidence

The revised [manuscript](paper.md) integrates ten measured figures. This is a reporting and diagnostic extension over existing observations, not fresh inference, a new independent benchmark, or a demonstrated improvement in model accuracy. The [original manuscript](../manuscript/paper.md) and its 161-file evidence inventory remain frozen.

## Questions each figure answers

| Figure file | Assessment question | Important boundary |
|---|---|---|
| [01: candidate outcomes](figures/01_edge_outcomes.svg) | What becomes a correct edge, unsupported edge, wrong-polarity edge, no-info result, abstention, or failure? | Each of the 339 rows has exactly one outcome; no-info is not automatically correct. |
| [02: precision–recall](figures/02_precision_recall.svg) | Is precision rising because fewer correct edges are retained? | 209 gold typed edges; unequal acceptance counts; zoomed axes. |
| [03: matched effects](figures/03_matched_precision.svg) | Does a difference persist at equal edge volume, with uncertainty? | All six exploratory paired intervals contain or touch zero; not an equivalence test. |
| [04: budget curves](figures/04_budget_precision.svg) | How do formulations compare at the same accepted count? | Frozen score ranking can split ties; never select a deployment optimum from this plot. |
| [05: components](figures/05_component_sizes.svg) | Is the graph useful only in small disconnected pieces? | Retains isolates; descriptive topology, not query correctness. |
| [06: reliability](figures/06_edge_reliability.svg) | Do accepted-edge probabilities match observed correctness? | Ten fixed bins, counts shown; dependent evaluation rows, no binomial certification. |
| [07: recorded usage](figures/07_recorded_input_cost.svg) | What historical input usage accompanies a correct retained edge? | Not dollars, marginal cost, or end-to-end deployment efficiency. |
| [08: withdrawal](figures/08_withdrawal.svg) | Does source withdrawal remove active assertions without erasing history? | Four constructed interventions, not observed natural retractions. |
| [09: real neighborhood](figures/09_observed_neighborhood.svg) | What do these relationships actually connect? | Real document/claim IDs; dotted candidates are not accepted edges or biomedical predicates. |
| [10: predicate risk](figures/10_predicate_risk_coverage.svg) | Do support and refutation need separate acceptance analysis? | Selective error is not false-positive rate among negatives; empty sets are omitted. |

Figure numbers in the manuscript follow reading order; file numbering is stable for reproduction. Every SVG has a matching 2,592-pixel-wide PNG, readable text, labeled axes where applicable, and a source-linked caption in the manuscript. Shapes, hatches, and explicit labels supplement the default color cycle. The neighborhood is an observed example, not an image-generation illustration.

## Sources and reproducibility

The original [graph-study result](results/graph-study.json.gz) and [relationship-experiment result](../experiments/relationships/reference/results.json.gz) are pinned by SHA-256 in `visualize.py`. The existing `RecordedJev` adapter separately verifies the original plan, requests, responses, and predictions through the frozen inventory. Both studies must identify those same source bytes. No credentials or dataset download are needed to generate the figures.

From the repository root:

```sh
python -m pip install -r graph_synthesis/requirements-figures.txt
python -B -m graph_synthesis.visualize
python -B -m graph_synthesis.visualize --check
python -B -m unittest discover -s graph_synthesis/tests -v
```

Use Python 3.12 and the pinned Matplotlib 3.10.8 for the CI rendering environment. Dependency installation may require networking; generation and tests use only local recorded evidence. `--output /new/path` creates a separate rendering; `--no-png` omits convenience raster images. `--check` verifies all tracked output hashes and rebuilds exact numerical JSON, CSV, and SVG; it does not disguise image mismatches as numerical tolerance. Original replay and relationship-experiment reproduction remain independent CI jobs.

[Exact plot data](figures/data.json), [edge-outcome CSV](figures/edge_outcomes.csv), [matched-effect CSV](figures/matched_precision.csv), [topology CSV](figures/topology.csv), [withdrawal CSV](figures/withdrawal.csv), and [lineage manifest](figures/manifest.json) allow independent audit. JSON includes confidence bins, accepted-budget points and boundary ties, predicate threshold grids, and the selected neighborhood's row IDs. The manifest hashes every generated output and the generator. It is additive: `MANIFEST.json` is not rewritten.

Fifteen new tests check conservation, distinct error types, source tampering, confidence boundaries including p=1, sparse bins, matched null findings, isolate retention, schema-eligible density, recorded two-formulation usage, withdrawal history, authentic neighborhood selection, canonical tables, and static SVG structure. Combined with the 85 existing extension tests, the extension suite has 100 tests. No synthetic software-test count enters semantic accuracy.

## Reading the evidence without overclaiming

Generic Choice commits 187 correct and 37 incorrect evidence edges. Few-shot commits 172 correct and 20 incorrect. The latter increases precision but loses fifteen correct edges. Agreement gating reaches 90% precision at 190 edges, exactly matched by the ranked few-shot baseline's 171 correct and 19 incorrect edges at the same volume. The chosen graph's isolated nodes rise from 180 to 241 of 583. These are selectivity and structure trade-offs, not a demonstrated superiority result.

The probability-combination arms reuse correlated observations from one model, not independent evidence sources. Their historical usage includes both original formulations. The graph constructor's conservation and repair properties are tested; candidate retrieval, large connected identity clusters, complex naturally conflicting sources, independently adjudicated query correctness, and end-to-end costs are not measured here.

KARMA remains a design/full-pipeline comparison in the manuscript, not an executed numerical baseline. Its published correctness metric is not placed beside this study's label-derived precision as though they measured the same task. No low-risk deployment threshold is qualified. The next informative study should freeze the acceptance design and evaluate an untouched, component-disjoint corpus with richer predicates and real graph-level consequences.
