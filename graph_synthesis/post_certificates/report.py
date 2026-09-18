"""Generate the post-certificate report, five evidence-derived figures, and additive paper text."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "post-certificates-20260923"
import matplotlib.pyplot as plt

from .run import ROOT, HERE

START = "<!-- POST_CERTIFICATES_RESEARCH_START -->"
END = "<!-- POST_CERTIFICATES_RESEARCH_END -->"
ANCHOR = "<!-- CERTIFICATES_RESEARCH_END -->"


def outcome(row):
    return "Met" if row["primary_target_met"] else "Not met"


def pct(value):
    return f"{100*value:.2f}%"


def insert(text, body):
    text = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\s*", "", text, flags=re.S)
    if text.count(ANCHOR) != 1:
        raise ValueError("Expected exactly one certificate-section anchor")
    before, after = text.split(ANCHOR, 1)
    return before + ANCHOR + "\n\n" + START + "\n\n" + body.strip() + "\n\n" + END + "\n\n" + after.lstrip()


def save(fig, stem):
    folder = HERE / "figures"
    folder.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(folder / f"{stem}.svg", bbox_inches="tight", metadata={"Date": None})
    fig.savefig(folder / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def figures(r):
    h1, h2, h3, h4, h5 = [r[f"H{i}"] for i in range(1, 6)]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    names = ["Feature risk", "Random effects", "Stacked"]
    vals = [h1["scores"]["feature"]["brier"], h1["scores"]["random_effects"]["brier"], h1["scores"]["stacked"]["brier"]]
    ax.bar(names, vals)
    ax.set_ylabel("Brier score (lower is better)")
    ax.set_title("H1 — Source-contamination forecast Brier")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.4f}", ha="center", va="bottom")
    save(fig, "01_stacked_risk")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    names = ["Marginals only", "Lexicographic 3", "Greedy 3"]
    vals = [h2["means"]["marginal"], h2["means"]["lexicographic"], h2["means"]["greedy"]]
    ax.bar(names, vals)
    ax.set_ylabel("Mean certified interval width")
    ax.set_title("H2 — Dependence-constraint acquisition")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.4f}", ha="center", va="bottom")
    save(fig, "02_constraint_acquisition")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    xs = [row["residual_vertices"] for row in h3["large"]]
    expected = [row["expected"] for row in h3["large"]]
    observed = [row["result_utility"] for row in h3["large"]]
    ax.plot(xs, expected, marker="o", label="Analytic optimum")
    ax.plot(xs, observed, marker="x", linestyle="--", label="Separator-conditioned solver")
    ax.set_xlabel("Residual cycle vertices")
    ax.set_ylabel("Maximum supplied-priority utility")
    ax.set_title("H3 — Large near-bipartite exact optimization")
    ax.legend()
    save(fig, "03_near_bipartite")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    vals = [h4["baseline_solve_calls_frozen"], h4["index_solve_calls"]]
    ax.bar(["Repeated queries", "Margin index"], vals)
    ax.set_ylabel("Top-level optimization invocations")
    ax.set_title("H4 — Reusable singleton-query margins")
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom")
    save(fig, "04_query_index")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    point_false = sum(int(row["point_result"]["lower"] >= .95 and row["actual"] < .95) for row in h5["controls"])
    interval_false = sum(int(row["interval_result"]["lower"] >= .95 and row["actual"] < .95) for row in h5["controls"])
    vals = [point_false, interval_false]
    ax.bar(["Biased point marginal", "Interval marginal"], vals)
    ax.set_ylabel("False admissions at 0.95")
    ax.set_title("H5 — Designed marginal-misspecification controls")
    for i, v in enumerate(vals):
        ax.text(i, v, str(v), ha="center", va="bottom")
    save(fig, "05_interval_marginals")


def write_summary(r):
    rows = [
        ["H1", "Exposure-stratified source-risk stacking", outcome(r["H1"]), "stacked_brier", r["H1"]["scores"]["stacked"]["brier"]],
        ["H2", "Greedy dependence-constraint acquisition", outcome(r["H2"]), "mean_final_width", r["H2"]["means"]["greedy"]],
        ["H3", "Separator-conditioned near-bipartite solver", outcome(r["H3"]), "small_failures", r["H3"]["small_failures"]],
        ["H4", "Reusable repair-margin query index", outcome(r["H4"]), "solve_call_saving", r["H4"]["saving"]],
        ["H5", "Interval-marginal dependence certificates", outcome(r["H5"]), "false_admissions_prevented", r["H5"]["false_admissions_prevented"]],
    ]
    with (HERE / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["hypothesis", "mechanism", "outcome", "primary_metric", "value"])
        writer.writerows(rows)


def render(r):
    a, b, c, d, e = [r[f"H{i}"] for i in range(1, 6)]
    h3_large = ", ".join(f"{x['residual_vertices']}→{x['result_utility']}/{x['expected']}" for x in c["large"])
    return f"""# Five post-certificate improvements for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

The dependence-aware certificate study left an asymmetric frontier: its source-random-effects forecast improved Brier by only 6.39% and missed its frozen target, while its dependence bounds, flow certificates, repair-invariant queries and local delta maintenance passed controlled tests. This pre-execution-frozen follow-up tests five responses to those remaining boundaries. The outcomes are: H1 **{outcome(a).lower()}**, H2 **{outcome(b).lower()}**, H3 **{outcome(c).lower()}**, H4 **{outcome(d).lower()}**, and H5 **{outcome(e).lower()}**. No fresh Jev calls are made. H1 reuses previously inspected saved responses; H2–H5 are controlled algorithmic experiments. These results are not new semantic-accuracy evidence and are not a comparison against KARMA or another external graph system.

## 1. Frozen methodology and novelty boundary

The protocol was committed as `{r['protocol_commit']}` against merged baseline `{r['baseline_commit']}` before implementation or execution. It fixes generators, thresholds, comparators and seed {r['seed']}. Existing package studies already contain relation-level stacking, fixed pairwise-dependence sensitivity analyses, bipartite flow, repair ambiguity and exact-marginal credal bounds. The five experiments here test different package-level integrations: source-group forecast stacking, active dependence-constraint acquisition, verified small-separator conditioning beyond bipartite graphs, reusable singleton repair margins and interval-valued marginal premises. This is a repository-scoped experiment distinction, not a worldwide novelty claim.

**Fresh Jev service calls: {r['fresh_service_calls']}.** No production graph policy is changed. The controlled structural fixtures do not establish real-world source truth, reviewer behavior, calibrated Jev probabilities or end-to-end database latency. A pass means only that the frozen target for the stated evidence population was met.

| Hypothesis | Frozen primary requirement | Result | Evidence class |
|---|---|---|---|
| H1: exposure-stratified source-risk stacking | Beat random-effects Brier by >=3%, do not regress feature-risk Brier, absolute bias <=0.03 | {outcome(a)} | Previously inspected saved-response source forecasts |
| H2: active dependence constraints | Zero containment/widening failures; mean width <=75% marginal-only and <=90% lexicographic same-budget | {outcome(b)} | Supplied finite joint distributions |
| H3: near-bipartite separator solver | Exact small oracles; solve all 512/1024/2048 residual cases; safe controls | {outcome(c)} | Supplied weighted conflict graphs |
| H4: repair-margin query index | Zero query/witness mismatches and >=70% fewer frozen-count optimization invocations | {outcome(d)} | Repeated controlled singleton queries |
| H5: interval marginals | Zero containment failures; prevent 20/20 designed false admissions; fail closed on malformed inputs | {outcome(e)} | Supplied joint distributions and uncertainty intervals |

## 2. H1 — Exposure-stratified source-risk stacking

The certificate result suggested that within-source dependence contains information but did not outperform the richer feature-risk forecast. H1 therefore combines the two forecasts without using evaluation labels for fitting. Leave-one-source-group-out development predictions select convex weights separately for singleton and multi-edge exposure strata when each stratum has at least eight folds; otherwise the global development weight is used.

Development selected feature weights: global **{a['weights']['global']:.1f}**, singleton **{a['weights']['singleton']:.1f}**, multi-edge **{a['weights']['multi']:.1f}**. Development fold counts are {a['fold_counts']['all']} total, {a['fold_counts']['singleton']} singleton and {a['fold_counts']['multi']} multi-edge. Evaluation scoring uses the identical {a['test_counts']['groups']} nonempty source groups as the comparators ({a['test_counts']['singleton']} singleton, {a['test_counts']['multi']} multi-edge).

| Forecast | Brier | Clipped log loss | Bias |
|---|---:|---:|---:|
| Existing feature-risk | {a['scores']['feature']['brier']:.6f} | {a['scores']['feature']['log_loss']:.6f} | {a['scores']['feature']['bias']:+.6f} |
| Certificate random effects | {a['scores']['random_effects']['brier']:.6f} | {a['scores']['random_effects']['log_loss']:.6f} | {a['scores']['random_effects']['bias']:+.6f} |
| Exposure-stratified stack | {a['scores']['stacked']['brier']:.6f} | {a['scores']['stacked']['log_loss']:.6f} | {a['scores']['stacked']['bias']:+.6f} |

The stacked-minus-feature paired Brier mean is {a['paired_vs_feature']['point']:+.6f}, with descriptive 95% interval [{a['paired_vs_feature']['95'][0]:+.6f}, {a['paired_vs_feature']['95'][1]:+.6f}]. The stacked-minus-random-effects mean is {a['paired_vs_random']['point']:+.6f}, with 95% interval [{a['paired_vs_random']['95'][0]:+.6f}, {a['paired_vs_random']['95'][1]:+.6f}]. The frozen conjunction is **{outcome(a).lower()}**. These intervals condition on the selected development weights and reuse already inspected evaluation data; they are not independent validation.

![H1. Forecast Brier on the identical nonempty source-group denominator.](figures/01_stacked_risk.png)

## 3. H2 — Greedy acquisition of dependence constraints

Marginal-only dependence bounds are safe but can be wide. H2 treats exact pairwise intersections from each fixture's supplied joint distribution as controlled observations and asks which three would most narrow the conclusion interval. At each step the policy evaluates every not-yet-observed pair and selects the one giving the smallest certified width; the comparator spends the same budget on the first three lexicographic pairs.

Across {b['source_fixture_count']} fixtures, mean width is **{b['means']['marginal']:.6f}** from marginals alone, **{b['means']['lexicographic']:.6f}** after the lexicographic budget and **{b['means']['greedy']:.6f}** after the greedy budget. Truth-containment failures: **{b['containment_failures']}**. Chosen-step widening failures: **{b['widening_failures']}**. The frozen target is **{outcome(b).lower()}**.

This is an oracle value-of-information experiment: it assumes the selected pairwise intersections can be supplied exactly. It does not show that those quantities are observable cheaply, that Jev scores are source reliabilities, or that a production estimator would preserve the same benefit.

![H2. Mean certified width before and after equal three-constraint budgets.](figures/02_constraint_acquisition.png)

## 4. H3 — Separator-conditioned near-bipartite exact optimization

The prior flow certificate handles bipartite components but stages sufficiently large non-bipartite ones. H3 accepts a supplied separator of at most four vertices, verifies that deleting it leaves a bipartite graph, enumerates every independent separator choice and solves each residual branch with the existing certified bipartite solver. An invalid separator is not trusted; it stages.

The 128 small exhaustive fixtures have **{c['small_failures']}** oracle failures and **{c['invariance_failures']}** order/duplicate-invariance failures. Large residual-cycle results are {h3_large}, written as residual vertices → obtained/analytic utility. The current generic solver stages respectively **{', '.join(str(x['prior_staged']) for x in c['large'])}** vertices on those fixtures. Malformed and non-transversal controls stage safely: **{c['controls']['ok']}**. The frozen target is **{outcome(c).lower()}**.

The supplied priorities and conflict edges remain premises. Exact maximum supplied-priority utility does not establish that a selected assertion is factually true.

![H3. Separator-conditioned utility versus the analytic optimum.](figures/03_near_bipartite.png)

## 5. H4 — Reusable repair-margin singleton query index

The certificate query implementation recomputes a base optimum plus forced-in/forced-out alternatives for repeated questions. H4 precomputes each vertex's inclusion and exclusion margin once, then classifies any singleton query at any tested tolerance by comparing those margins with the tolerance threshold.

Across **{d['queries']}** repeated singleton queries, classification mismatches are **{d['mismatches']}** and witness failures are **{d['witness_failures']}**. Under the frozen top-level solve-count accounting, repeated queries require **{d['baseline_solve_calls_frozen']:,}** invocations versus **{d['index_solve_calls']:,}** for index construction, a **{pct(d['saving'])}** reduction. A control using the existing query's realized early-exit count gives a still-separated descriptive reduction of **{pct(d['conservative_saving'])}**. The frozen target is **{outcome(d).lower()}**.

This index is deliberately limited to singleton queries and in-memory top-level optimization calls. It is not a measured SQL/database speedup or a semantic guarantee.

![H4. Frozen-accounting optimization calls for repeated queries versus one reusable index.](figures/04_query_index.png)

## 6. H5 — Interval-marginal dependence certificates

Previous dependence-safe methods remain conditional on exact atom marginals. H5 instead supplies each atom with a lower and upper probability and optimizes over all Boolean-world distributions whose marginals lie inside those intervals. Reported endpoints use independently checked, outward-padded dual bounds rather than treating numerical primal optima as certificates. Exact point marginals are a special case. Invalid, infeasible or over-cap inputs return a non-certifying [0,1] stage.

Across 128 arbitrary-joint fixtures, truth-containment failures are **{e['containment_failures']}**. Mean point-bound width is **{e['means']['point_width']:.6f}** and mean interval-marginal width is **{e['means']['interval_width']:.6f}**, exposing the cost of premise uncertainty rather than hiding it. On 20 deliberately biased singleton point estimates, the interval policy prevents **{e['false_admissions_prevented']}/20** designed false admissions. Malformed inputs returning a certifying interval: **{e['malformed_certifying']}**. The frozen target is **{outcome(e).lower()}**.

The interval itself is still a supplied assumption. If the real marginal falls outside it, the certificate can again be wrong. This test converts one known premise-error mode into explicit uncertainty; it does not validate how such intervals should be estimated from real sources.

![H5. False admissions on designed marginal-misspecification controls.](figures/05_interval_marginals.png)

## 7. Interpretation and falsification boundary

The five experiments are intentionally heterogeneous. H1 asks whether two already observed forecast signals combine on reused response data. H2 asks whether a constrained information budget can reduce dependence uncertainty on finite controlled worlds. H3 and H4 test exact structural reuse. H5 asks whether uncertainty in the probability premises can be represented rather than ignored. Their pass/fail outcomes must not be pooled into a semantic success percentage.

The strongest remaining scientific boundary is unchanged: freeze a policy before observing a new source-disjoint, independently adjudicated corpus and compare full graph quality, downstream queries, provenance errors, reviewer mistakes, resource budgets and staging against appropriate external baselines. None of the controlled algorithmic passes can substitute for that prospective semantic evaluation.

## 8. Reproduction

```bash
python -m pip install -r graph_synthesis/post_certificates/requirements.txt
python -B -m graph_synthesis.post_certificates.run
python -B -m unittest discover -s graph_synthesis/post_certificates/tests -v
python -B -m graph_synthesis.post_certificates.run --check
python -B -m graph_synthesis.post_certificates.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
```

The machine-readable results retain the controlled fixtures, selected pair constraints, optimization witnesses, development-only weights, uncertainty intervals and falsifying controls. The five PNG/SVG pairs and summary table are generated from those recorded results. Earlier study artifacts are not rewritten.
"""


def update_paper(r):
    def rebase(match):
        url = match.group(1)
        if "://" in url or url.startswith("#"):
            return "](" + url + ")"
        path = (HERE / url).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Link outside repository")
        return "](../" + path.relative_to(ROOT).as_posix() + ")"

    full = re.sub(r"\]\(([^)]+)\)", rebase, render(r))
    paper = ROOT / "manuscript/paper-current.md"
    paper.write_text(insert(paper.read_text(encoding="utf-8"), full), encoding="utf-8", newline="\n")

    outcomes = "; ".join(f"H{i} {outcome(r[f'H{i}']).lower()}" for i in range(1, 6))
    note = (
        "## Five post-certificate improvements after PR #20\n\n"
        "[Executed report](graph_synthesis/post_certificates/RESULTS.md), "
        "[frozen protocol](graph_synthesis/post_certificates/PROTOCOL.md), "
        "[five figures](graph_synthesis/post_certificates/figures/) and "
        "[complete updated paper](manuscript/paper-current.pdf). "
        + outcomes
        + ". H1 reuses previously inspected saved responses; H2-H5 are controlled algorithms. "
          "The suite tests source-risk stacking, active dependence constraints, verified near-bipartite separators, "
          "reusable singleton repair margins and interval-valued probability premises. "
          "No fresh Jev calls, independent semantic-accuracy claim, worldwide novelty claim or production-policy change."
    )
    current = ROOT / "CURRENT_RESULTS.md"
    current.write_text(insert(current.read_text(encoding="utf-8"), note), encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--update-paper", action="store_true")
    args = parser.parse_args()
    r = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    (HERE / "RESULTS.md").write_text(render(r), encoding="utf-8", newline="\n")
    write_summary(r)
    if args.figures:
        figures(r)
    if args.update_paper:
        update_paper(r)


if __name__ == "__main__":
    main()
