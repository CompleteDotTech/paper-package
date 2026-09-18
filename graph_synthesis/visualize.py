"""Reproducible visual assessment of frozen graph decisions; no model/network calls.

Figures are descriptive reanalyses, not new semantic experiments or fitted policies.
Original observations are hash-checked by RecordedJev. Summary sources and every
committed SVG are bound in a separate manifest; the frozen inventory is untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .recorded import BASELINES, LABELS, RecordedJev
from .study import action_metrics, accepted_ids, read_scores
from .verify import compare_json

ROOT = Path(__file__).resolve().parents[1]
GRAPH = "graph_synthesis/results/graph-study.json.gz"
FUSION = "experiments/relationships/reference/results.json.gz"
ARMS = ("baseline_choice", "fewshot_contract", "mean_pool", "agreement_gate", "stacked")
NAMES = dict(zip(ARMS, ("Generic Choice", "Selected formulation", "Probability average", "Agreement gate", "Calibration stacker")))
NAMES["baseline_noul"] = "Noul baseline"
EDGE_LABELS = {"SUPPORTS", "REFUTES"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gzip(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def risk_curve(rows: list[dict], labels: set[str]) -> list[dict]:
    """Threshold the ORIGINAL predicted action score, admitting whole tie blocks.

    Candidate coverage includes operational failures and non-edge predictions in
    its denominator. An empty accepted set has undefined risk, not zero risk.
    """
    groups: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        if row["label"] in labels:
            score = row["score"]
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("Invalid action score")
            groups[score].append(row)
    accepted = wrong = 0
    curve = []
    for threshold in sorted(groups, reverse=True):
        block = groups[threshold]
        accepted += len(block)
        wrong += sum(row["gold"] != row["label"] for row in block)
        curve.append({"threshold": threshold, "tie_block": len(block), "accepted": accepted,
                      "incorrect": wrong, "coverage": accepted / len(rows), "risk": wrong / accepted})
    return curve


def reliability(rows: list[dict], label: str, bins: int = 10) -> list[dict]:
    """Classwise raw-probability bins; use every valid row, not argmax-only rows."""
    if bins < 1:
        raise ValueError("At least one bin is required")
    groups: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for row in rows:
        if row["decision"].error:
            continue
        p = row["decision"].probabilities[label]
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Invalid class probability")
        groups[min(int(p * bins), bins - 1)].append((p, int(row["gold"] == label)))
    return [{"bin": b, "lower": b / bins, "upper": (b + 1) / bins, "n": len(groups[b]),
             "mean_probability": sum(p for p, _ in groups[b]) / len(groups[b]) if groups[b] else None,
             "observed_fraction": sum(y for _, y in groups[b]) / len(groups[b]) if groups[b] else None}
            for b in range(bins)]


def component_example(left: list[dict], right: list[dict]) -> dict:
    """Select by disagreement count, then size, then IDs; never by gold correctness."""
    by_right = {row["id"]: row for row in right}
    adjacency: dict[str, set[str]] = defaultdict(set)
    edges = []
    for row in left:
        other = by_right[row["id"]]
        s, o = "document:" + row["row"]["document_id"], "claim:" + row["row"]["claim_id"]
        adjacency[s].add(o); adjacency[o].add(s)
        # Gold attached for audit AFTER the selection rule; it never ranks components.
        edges.append({"id": row["id"], "subject": s, "object": o, "baseline": row["label"],
                      "selected": other["label"], "gold": row["gold"]})
    seen: set[str] = set()
    components = []
    for start in sorted(adjacency):
        if start in seen:
            continue
        stack, nodes = [start], set()
        while stack:
            node = stack.pop()
            if node in nodes:
                continue
            nodes.add(node); stack.extend(adjacency[node] - nodes)
        seen |= nodes
        selected = [edge for edge in edges if edge["subject"] in nodes]
        differences = sum(e["baseline"] != e["selected"] for e in selected)
        components.append((differences, len(nodes), sorted(nodes), selected))
    if not components:
        return {"nodes": [], "edges": [], "changed_decisions": 0}
    changes, _, nodes, selected = sorted(components, key=lambda c: (-c[0], -c[1], c[2]))[0]
    return {"nodes": nodes, "edges": sorted(selected, key=lambda e: e["id"]), "changed_decisions": changes,
            "selection": "All candidate components, ranked by changed decisions descending, node count descending, then sorted node IDs. Gold is not used."}


def effect_vs_selected(comparisons: dict, arm: str) -> dict:
    for key, sign in (("fewshot_contract__vs__" + arm, 1), (arm + "__vs__fewshot_contract", -1)):
        if key in comparisons:
            row = comparisons[key]
            lo, hi = row["macro_f1_bootstrap"]["interval"]
            return {"arm": arm, "delta": sign * row["macro_f1_delta"],
                    "interval": [lo, hi] if sign == 1 else [-hi, -lo],
                    "draws": row["macro_f1_bootstrap"]["draws"]}
    raise ValueError("Missing paired contrast for " + arm)


def build_data(root: Path = ROOT) -> dict:
    backend = RecordedJev(root)
    graph, fusion = load_gzip(root / GRAPH), load_gzip(root / FUSION)
    if graph["input_sha256"] != backend.hashes:
        raise ValueError("Graph summary does not bind the original observations")
    data: dict[str, Any] = {
        "schema_version": 1, "fresh_model_calls": 0,
        "status": "Post-hoc descriptive visualization; no new inference, model fit, threshold selection, or KARMA run.",
        "inputs_sha256": {GRAPH: sha256(root / GRAPH), FUSION: sha256(root / FUSION),
                           **{f"reproduction/results/jev/run-20260918/{k}": v for k, v in backend.hashes.items()}},
        "tasks": {}, "fusion": {"arms": {}, "effects_vs_selected": []},
    }
    all_rows = {}
    for task in LABELS:
        task_data = {"arms": {}, "matched": graph["tasks"][task]["matched_primary_action_count"]}
        all_rows[task] = {}
        for arm in (BASELINES[task], "fewshot_contract"):
            rows = read_scores(backend, task, arm, "evaluation")
            all_rows[task][arm] = rows
            saved = graph["tasks"][task][arm]
            if len(rows) != saved["eligible"] or sum(r["label"] == "ERROR" for r in rows) != saved["errors"]:
                raise ValueError("Changed eligibility/error accounting")
            actions = {}
            for label in LABELS[task]:
                if label == "NOT_ENOUGH_INFO":
                    continue
                m = action_metrics(rows, accepted_ids(rows, label, 0), label)
                compare_json(saved["actions"][label]["argmax"], m)
                actions[label] = m
            confusion = dict(sorted(Counter(r["gold"] + " -> " + r["label"] for r in rows).items()))
            if confusion != saved["confusion"]:
                raise ValueError("Confusion counts differ from graph study")
            labels = EDGE_LABELS if task == "relation_support" else {"same"}
            task_data["arms"][arm] = {
                "n": len(rows), "groups": len({r["group"] for r in rows}), "errors": saved["errors"],
                "gold_counts": dict(sorted(Counter(r["gold"] for r in rows).items())),
                "confusion": confusion, "actions": actions, "risk_curve": risk_curve(rows, labels),
                "reliability": {label: reliability(rows, label) for label in labels},
                "graph": saved["graph"], "recorded_usage": saved["recorded_evaluation_usage"],
            }
        data["tasks"][task] = task_data
    relation = all_rows["relation_support"]
    data["component_example"] = component_example(relation["baseline_choice"], relation["fewshot_contract"])
    for arm in ARMS:
        saved = fusion["arms"][arm]
        op = saved["operational"]
        if op["n"] != 339 or op["edges"]["accepted"] != op["edges"]["correct"] + op["edges"]["incorrect"]:
            raise ValueError("Invalid fusion denominator or edge partition")
        if arm in relation:
            g = data["tasks"]["relation_support"]["arms"][arm]["graph"]
            if (g["committed_label_correct"], g["committed_label_incorrect"]) != (op["edges"]["correct"], op["edges"]["incorrect"]):
                raise ValueError("Fusion and graph summaries disagree")
        data["fusion"]["arms"][arm] = {"operational": op, "recorded_usage": saved["recorded_usage"],
                                               "budget_curve": saved["budget_curve"]}
    for arm in ("mean_pool", "agreement_gate", "stacked"):
        data["fusion"]["effects_vs_selected"].append(effect_vs_selected(fusion["comparisons"], arm))
    return data


CAPTIONS = {
    "01_edge_yield": "All 339 SciFact candidates remain in each bar. Correct and incorrect SUPPORTS/REFUTES edges are separated from no-edge outcomes. No edge includes NOT_ENOUGH_INFO, operational failure, and (for the agreement arm) abstention; it does not mean correct rejection. Source: fusion.arms.*.operational. Existing experiment, not fresh inference.",
    "02_precision_recall": "Typed-edge precision versus recall for the five frozen experimental arms. Recall uses all 209 gold SUPPORTS/REFUTES rows, not accepted predictions. Wrong polarity is both an incorrect edge and a missed gold edge. Axes run from 0 to 100%; the arrows only locate labels. No confidence region or superiority claim is implied.",
    "03_identity_risk_coverage": "Identity same-action risk (incorrect accepted same labels / accepted same labels) versus accepted candidates / all 413 candidates. Each point admits a complete equal-score tie block. The curve is descriptive evaluation-set evidence, not a calibrated policy; different_from constraints are outside this curve.",
    "04_relation_risk_coverage": "Pooled SUPPORTS/REFUTES wrong-edge risk versus accepted candidates / all 339 candidates. Whole score ties are admitted; no exact-K splitting or synthetic origin point is used. NEI and errors remain in the coverage denominator. Risk is not false-positive rate among negatives. No threshold is selected from this curve.",
    "05_confusion_baseline": "Generic Choice operational confusion on 339 SciFact candidates. Cells show counts and within-gold-row percentages. ERROR is a separate output column and remains in the denominator. All gold counts are printed; color intensity is normalized within each gold row.",
    "06_confusion_selected": "Selected formulation operational confusion, using exactly the baseline plot's gold order, columns and normalization. A predicted NEI is not the same as abstention or an operational error. In particular, true support can be omitted without becoming a wrong committed edge.",
    "07_matched_precision": "Selected-minus-baseline precision at equal accepted PRIMARY-action counts: 351 same-identity actions and 118 SUPPORTS actions. Points and intervals come from the existing 1,000-draw paired percentile bootstrap (seed 20260918). SciFact resamples components; identity resamples disjoint pair units. Both intervals include zero. This is not the pooled-edge fusion comparison.",
    "08_component_coverage": "SciFact nodes grouped by the size of their accepted-edge weak component. Each bar equals component size times component count. Both arms retain all 583 candidate nodes, including isolates (size 1); totals therefore have the same denominator. More connected nodes do not establish more correct facts.",
    "09_identity_reliability": "Classwise raw P(same) reliability on every valid identity response. Fixed ten equal-width bins, [lower, upper), with 1 included in the last bin; empty bins are omitted, not zero-filled. Marker area is proportional to bin count. The diagonal denotes equality of binned means, not certification of low graph risk.",
    "10_support_reliability": "Raw P(SUPPORTS) against gold support frequency on every valid SciFact response, including rows predicted as other labels. Same bins and marker sizing as the identity reliability plot. Failures are excluded ONLY from probability diagnostics, not operational metrics. Repeated components make this descriptive, not an independent-binomial confidence assessment.",
    "11_refute_reliability": "Raw P(REFUTES) classwise reliability with fixed bins and sample-size-proportional marker area. The plot describes source-to-claim classification, not factual probabilities of biomedical relations. It is not a new temperature-scaling experiment.",
    "12_changed_component": "An actual supplied-candidate SciFact component, selected deterministically by the largest number of changed predictions, then node count, then IDs, without gold-based selection. Nodes are original document/claim identifiers. Each arrow lists baseline / selected / gold. Dashed arrows mark changed predictions; a no-edge prediction does not delete its nodes. This deliberately selected disagreement example is not representative evidence of average quality.",
    "13_source_withdrawal": "Controlled withdrawal of the most incident source snapshot in each existing graph. Bars show active and deactivated assertions after withdrawal; their totals equal preserved historical assertions. Identity includes same_as AND different_from assertions. Reopen/audit checks are software outcomes, not independently observed scientific retractions.",
    "14_fusion_effects": "Existing component-paired macro-F1 differences relative to the selected formulation, with 2,000-draw 95% percentile intervals from the relationship experiment. Intervals are unadjusted, conditional on frozen selection, and include zero. No fresh model fit or experiment is performed by the figure generator.",
    "15_recorded_input_cost": "Historical evaluation input tokens needed by each formulation versus correctly retained SciFact edges. Two-formulation arms require both sets of requests. Counts exclude retrieval, extraction, storage, review, current prices and fresh measurements; they are not an end-to-end cost or latency benchmark. Three ensemble points share an input-token coordinate.",
}


def render(data: dict, output: Path, formats: tuple[str, ...] = ("svg", "png")) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    import numpy as np

    if not formats or set(formats) - {"svg", "png", "pdf"}:
        raise ValueError("Formats must be svg, png, or pdf")
    output.mkdir(parents=True, exist_ok=True)

    def canvas(title, xlabel="", ylabel="", size=(9.0, 5.1)):
        fig, ax = plt.subplots(figsize=size, layout="constrained")
        ax.set_title(title, loc="left", fontsize=14, pad=16)
        ax.set_xlabel(xlabel, fontsize=11); ax.set_ylabel(ylabel, fontsize=11)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=10)
        return fig, ax

    def save(fig, name):
        # Stable SVG IDs and no timestamp; preserve real text instead of glyph paths.
        with matplotlib.rc_context({"svg.fonttype": "none", "svg.hashsalt": name}):
            for extension in formats:
                metadata = {"Date": None} if extension == "svg" else ({"CreationDate": None, "ModDate": None} if extension == "pdf" else None)
                fig.savefig(output / f"{name}.{extension}", dpi=240, metadata=metadata)
        plt.close(fig)

    rel = data["tasks"]["relation_support"]["arms"]
    fusion = data["fusion"]["arms"]
    fig, ax = canvas("What enters the evidence graph?", "SciFact candidate rows (n = 339)")
    y = np.arange(len(ARMS))
    correct = np.array([fusion[a]["operational"]["edges"]["correct"] for a in ARMS])
    wrong = np.array([fusion[a]["operational"]["edges"]["incorrect"] for a in ARMS])
    noedge = 339 - correct - wrong
    for values, start, label, hatch in ((correct, 0, "Correct edge", None), (wrong, correct, "Incorrect edge", "///"), (noedge, correct + wrong, "No edge", "..")):
        bars = ax.barh(y, values, left=start, label=label, hatch=hatch, alpha=.62)
        ax.bar_label(bars, labels=[str(v) for v in values], label_type="center", fontsize=10)
    ax.set_yticks(y, [NAMES[a] for a in ARMS]); ax.invert_yaxis(); ax.set_xlim(0, 339)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncols=3, fontsize=9)
    ax.set_title(ax.get_title(loc="left"), loc="left", fontsize=14, pad=44)
    save(fig, "01_edge_yield")

    fig, ax = canvas("Better precision can mean fewer correct edges", "Typed-edge recall: correct / 209 gold edges", "Typed-edge precision: correct / accepted")
    offsets = {"baseline_choice": (-180, -65), "fewshot_contract": (-230, 5), "mean_pool": (-225, -30), "agreement_gate": (-215, 37), "stacked": (-150, -100)}
    for arm in ARMS:
        m = fusion[arm]["operational"]["edges"]
        ax.plot(m["recall"], m["precision"], marker="o", markersize=7, linestyle="none")
        ax.annotate(NAMES[arm], (m["recall"], m["precision"]), xytext=offsets[arm], textcoords="offset points", fontsize=10, arrowprops={"arrowstyle": "-", "lw": .8})
    ax.set(xlim=(0, 1.02), ylim=(0, 1.03)); ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1))
    save(fig, "02_precision_recall")

    for task, name, title in (("entity_resolution", "03_identity_risk_coverage", "Identity links: error risk versus accepted coverage"), ("relation_support", "04_relation_risk_coverage", "Evidence edges: error risk versus accepted coverage")):
        fig, ax = canvas(title, "Accepted actions / all supplied candidate rows", "Incorrect accepted actions / accepted actions")
        for arm, values in data["tasks"][task]["arms"].items():
            curve = values["risk_curve"]
            if curve:
                ax.plot([r["coverage"] for r in curve], [r["risk"] for r in curve], ".-", linewidth=1.4, markersize=3, label=NAMES[arm])
                end = curve[-1]
                ax.annotate(f'{end["incorrect"]}/{end["accepted"]}', (end["coverage"], end["risk"]), xytext=(6, 6), textcoords="offset points", fontsize=9)
        ax.set(xlim=(0, 1), ylim=(0, max(.03, max((r["risk"] for v in data["tasks"][task]["arms"].values() for r in v["risk_curve"]), default=0) * 1.25)))
        ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.legend(fontsize=9)
        save(fig, name)

    for arm, name in (("baseline_choice", "05_confusion_baseline"), ("fewshot_contract", "06_confusion_selected")):
        golds, predictions = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"], ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO", "ERROR"]
        values = rel[arm]
        counts = np.array([[values["confusion"].get(g + " -> " + p, 0) for p in predictions] for g in golds])
        rates = counts / counts.sum(axis=1, keepdims=True)
        fig, ax = canvas(NAMES[arm] + ": operational confusion", "Recorded prediction", "Gold label", size=(9, 4.6))
        ax.imshow(rates, vmin=0, vmax=1, alpha=.3, aspect="auto")
        for i in range(3):
            for j in range(4):
                ax.text(j, i, f"{counts[i,j]}\n({rates[i,j]:.1%})", ha="center", va="center", fontsize=11)
        ax.set_xticks(range(4), ["Supports", "Refutes", "NEI", "Error"])
        ax.set_yticks(range(3), [f"{g.replace('NOT_ENOUGH_INFO','NEI')} (n={counts[i].sum()})" for i, g in enumerate(golds)])
        save(fig, name)

    fig, ax = canvas("Matched action counts narrow the apparent gain", "Selected minus baseline precision (percentage points)", size=(9, 3.9))
    for i, (task, label) in enumerate((("entity_resolution", "Same identity (351 each)"), ("relation_support", "Supports claim (118 each)"))):
        m = data["tasks"][task]["matched"]
        point = 100 * (m["selected"]["precision"] - m["baseline"]["precision"])
        lo, hi = [100 * v for v in m["paired_precision_difference"]["interval"]]
        ax.errorbar(point, i, xerr=[[point-lo], [hi-point]], fmt="o", capsize=5, label=label)
        ax.text(hi + .15, i, f"{point:+.3f} [{lo:.3f}, {hi:.3f}]", va="center", fontsize=9)
    ax.axvline(0, linestyle="--", linewidth=1); ax.set_yticks([0, 1], ["Same identity", "Supports claim"]); ax.set(xlim=(-3.5, 9), ylim=(-.6, 1.6)); ax.invert_yaxis()
    save(fig, "07_matched_precision")

    fig, ax = canvas("Selectivity leaves more candidate nodes isolated", "Accepted-edge weak-component size", "Candidate nodes in components of this size")
    sizes = np.arange(1, 7)
    for i, arm in enumerate(("baseline_choice", "fewshot_contract")):
        histogram = rel[arm]["graph"]["metrics"]["weak_component_size_histogram"]
        mass = [int(s) * histogram.get(str(s), 0) for s in sizes]
        bars = ax.bar(sizes + (i - .5) * .36, mass, width=.36, label=NAMES[arm], hatch=None if i == 0 else "//", alpha=.7)
        ax.bar_label(bars, padding=3, fontsize=9)
    ax.set_xticks(sizes, ["1\n(isolates)", "2", "3", "4", "5", "6"]); ax.set_ylim(0, 370); ax.legend(fontsize=9)
    save(fig, "08_component_coverage")

    for task, label, name in (("entity_resolution", "same", "09_identity_reliability"), ("relation_support", "SUPPORTS", "10_support_reliability"), ("relation_support", "REFUTES", "11_refute_reliability")):
        fig, ax = canvas(f"Does raw P({label}) track observed frequency?", "Mean raw probability within bin", "Gold-positive fraction within bin", size=(7.2, 5.1))
        ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Reference equality")
        for arm, values in data["tasks"][task]["arms"].items():
            bins = [b for b in values["reliability"][label] if b["n"]]
            ax.scatter([b["mean_probability"] for b in bins], [b["observed_fraction"] for b in bins], s=[2*b["n"] for b in bins], alpha=.5, label=f'{NAMES[arm]} (valid n={sum(b["n"] for b in bins)})')
        ax.set(xlim=(-.03, 1.03), ylim=(-.03, 1.03)); ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.legend(loc="lower right", fontsize=8, markerscale=.55)
        save(fig, name)

    example = data["component_example"]
    fig, ax = canvas("A real disagreement component, not a hypothetical graph", size=(10, max(5, len(example["edges"]) * .68)))
    docs = [n for n in example["nodes"] if n.startswith("document:")]
    claims = [n for n in example["nodes"] if n.startswith("claim:")]
    pos = {n: (x, float(y)) for x, nodes in ((0, docs), (1, claims)) for n, y in zip(nodes, ([.5] if len(nodes) == 1 else np.linspace(.1, .9, len(nodes))))}
    abbreviate = lambda s: {"SUPPORTS": "S", "REFUTES": "R", "NOT_ENOUGH_INFO": "NEI", "ERROR": "ERR"}[s]
    for x, nodes, marker in ((0, docs, "s"), (1, claims, "o")):
        ax.scatter([pos[n][0] for n in nodes], [pos[n][1] for n in nodes], marker=marker, s=110)
        for n in nodes:
            ax.annotate(n.replace("document:", "Doc ").replace("claim:", "Claim "), pos[n], xytext=(-8 if x == 0 else 8, 0), textcoords="offset points", ha="right" if x == 0 else "left", va="center", fontsize=9)
    for i, edge in enumerate(example["edges"]):
        a, b = pos[edge["subject"]], pos[edge["object"]]
        ax.annotate("", b, a, arrowprops={"arrowstyle": "->", "linestyle": "--" if edge["baseline"] != edge["selected"] else "-", "alpha": .5, "shrinkA": 8, "shrinkB": 8})
        t = .38 + .18 * (i % 2)
        ax.text(t, a[1]*(1-t)+b[1]*t+.025, " / ".join(abbreviate(edge[k]) for k in ("baseline", "selected", "gold")), ha="center", fontsize=10)
    ax.text(.5, -.07, "Arrow labels: baseline / selected / gold     S: supports   R: refutes   NEI: no edge", ha="center", fontsize=9)
    ax.set(xlim=(-.36, 1.3), ylim=(-.13, 1.04)); ax.axis("off")
    save(fig, "12_changed_component")

    fig, ax = canvas("Withdrawal changes the active view, not its history", "Preserved assertions after controlled source withdrawal")
    labels, active, inactive = [], [], []
    for task in ("entity_resolution", "relation_support"):
        for arm, values in data["tasks"][task]["arms"].items():
            lifecycle = values["graph"]["lifecycle"]
            labels.append(("Identity: " if task == "entity_resolution" else "Evidence: ") + ("baseline" if arm.startswith("baseline") else "selected"))
            active.append(lifecycle["active_after_withdrawal"]); inactive.append(lifecycle["actual_retractions"])
    y = np.arange(len(labels))
    bars = ax.barh(y, active, label="Active", alpha=.65); ax.bar_label(bars, padding=-35, fontsize=10)
    bars = ax.barh(y, inactive, left=active, label="Deactivated; retained in history", hatch="///", alpha=.65); ax.bar_label(bars, labels=[f"-{n}" for n in inactive], padding=4, fontsize=10)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlim(0, 445); ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.01), ncols=2, fontsize=9)
    ax.set_title(ax.get_title(loc="left"), loc="left", fontsize=14, pad=44)
    save(fig, "13_source_withdrawal")

    fig, ax = canvas("Combining formulations has no resolved macro-F1 gain", "Macro-F1 difference versus selected formulation (percentage points)", size=(9, 4.1))
    effects = data["fusion"]["effects_vs_selected"]
    for i, e in enumerate(effects):
        point, lo, hi = 100*e["delta"], 100*e["interval"][0], 100*e["interval"][1]
        ax.errorbar(point, i, xerr=[[point-lo], [hi-point]], fmt="o", capsize=5)
        ax.text(hi+.15, i, f"{point:+.3f}", va="center", fontsize=10)
    ax.axvline(0, linestyle="--", linewidth=1); ax.set_yticks(range(len(effects)), [NAMES[e["arm"]] for e in effects]); ax.set(xlim=(-6, 4), ylim=(-.6, len(effects)-.4)); ax.invert_yaxis()
    save(fig, "14_fusion_effects")

    fig, ax = canvas("Historical inference inputs are not free in deployment", "Recorded input tokens (millions)", "Correctly retained evidence edges")
    for i, arm in enumerate(ARMS):
        usage = fusion[arm]["recorded_usage"]
        x = usage["input_tokens"] / 1e6
        y = fusion[arm]["operational"]["edges"]["correct"]
        ax.plot(x, y, "o")
        ax.annotate(NAMES[arm], (x, y), xytext=((12, 15) if i == 0 else (-120, -25) if i == 1 else (12, [15, 10, 25, -22, 0][i])), textcoords="offset points", fontsize=9, arrowprops={"arrowstyle": "-", "lw": .6})
    ax.set(xlim=(0, 2.25), ylim=(0, 210))
    save(fig, "15_recorded_input_cost")


def write_outputs(data: dict, output: Path, formats: tuple[str, ...] = ("svg", "png")) -> None:
    render(data, output, formats)
    (output / "data.json").write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    rows = []
    for arm in ARMS:
        op = data["fusion"]["arms"][arm]["operational"]
        rows.append({"arm": arm, "candidates": op["n"], **op["edges"], "macro_f1": op["macro_f1"], "errors": op["errors"], "abstentions": op["abstentions"]})
    with (output / "edge_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    lines = ["# Graph-synthesis visual assessment", "", "Generated from frozen observations and executed summaries by `python -B -m graph_synthesis.visualize`. No fresh inference or threshold selection. Read the [revised manuscript](../paper.md).", "", "SVG is the committed, scalable source; optional PNG (240 dpi) and PDF exports use the same figure data. `data.json` contains complete chart inputs and source SHA-256 hashes; `edge_summary.csv` exposes the main denominators. Each figure has its own plot and can be read independently.", ""]
    for i, (name, caption) in enumerate(CAPTIONS.items(), 1):
        lines += [f"## {name.replace('_', ' ')}", "", f"![Figure {i}: {name.replace('_', ' ')}]({name}.svg)", "", caption, ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    paths = ["data.json", "edge_summary.csv", "README.md"] + [n + ".svg" for n in CAPTIONS if "svg" in formats]
    manifest = {"generator_sha256": sha256(Path(__file__)), "inputs_sha256": data["inputs_sha256"],
                "files_sha256": {name: sha256(output / name) for name in paths}}
    (output / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_outputs(root: Path, output: Path) -> dict:
    fresh = build_data(root)
    saved = json.loads((output / "data.json").read_text(encoding="utf-8"))
    differences = compare_json(saved, fresh)
    manifest = json.loads((output / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["generator_sha256"] != sha256(Path(__file__)) or manifest["inputs_sha256"] != fresh["inputs_sha256"]:
        raise ValueError("Stale generator/input provenance; regenerate figures")
    for name, expected in manifest["files_sha256"].items():
        path = output / name
        if not path.resolve().is_relative_to(output.resolve()) or path.is_symlink() or sha256(path) != expected:
            raise ValueError("Changed or unsafe generated figure artifact: " + name)
    if set(manifest["files_sha256"]) != {"data.json", "edge_summary.csv", "README.md", *(n + ".svg" for n in CAPTIONS)}:
        raise ValueError("Incomplete figure inventory")
    return {"figures_verified": len(CAPTIONS), "new_model_calls": 0, "roundoff": differences}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "graph_synthesis/figures")
    parser.add_argument("--formats", default="svg,png")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(json.dumps(check_outputs(args.repository, args.output), indent=2))
    else:
        write_outputs(build_data(args.repository), args.output, tuple(args.formats.split(",")))
        print(json.dumps({"figures": len(CAPTIONS), "output": str(args.output), "new_model_calls": 0}))


if __name__ == "__main__":
    main()
