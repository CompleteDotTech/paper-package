"""Reproducible, offline graph-study figures; never changes frozen evidence.

Numerical transformations use the standard library. Matplotlib is imported only
when rendering. All views are post-hoc diagnostics, not new model experiments.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile

from .recorded import RecordedJev
from .study import read_scores

INPUTS = {
    "graph_synthesis/results/graph-study.json.gz": "c0a1684930623c238aa45051ebfef170c2e8d25f2460c82a6f2323e18a3b1939",
    "experiments/relationships/reference/results.json.gz": "46077c7c8aa9ac71ffd1f0ac0ddb2f63af43940cdfba3f613430e4044f4543c2",
}
ARMS = ("baseline_choice", "fewshot_contract", "mean_pool", "agreement_gate", "stacked")
NAMES = dict(zip(ARMS, ("Generic Choice", "Few-shot contract", "Probability average", "Agreement gate", "Calibration stacker")))
FIGURES = (
    "01_edge_outcomes", "02_precision_recall", "03_matched_precision",
    "04_budget_precision", "05_component_sizes", "06_edge_reliability",
    "07_recorded_input_cost", "08_withdrawal", "09_observed_neighborhood",
    "10_predicate_risk_coverage",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def load_reference(root: Path, relative: str) -> dict:
    raw = (root / relative).read_bytes()
    if digest(raw) != INPUTS[relative]:
        raise ValueError("Reference hash mismatch: " + relative)
    return json.loads(gzip.decompress(raw))


def dispositions(op: dict) -> dict:
    """Partition every evaluation row; wrong polarity is not a correct edge."""
    c = op["confusion"]
    labels = ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO")
    row = {
        "correct_edge": c["SUPPORTS"]["SUPPORTS"] + c["REFUTES"]["REFUTES"],
        "unsupported_edge": c["NOT_ENOUGH_INFO"]["SUPPORTS"] + c["NOT_ENOUGH_INFO"]["REFUTES"],
        "wrong_polarity": c["SUPPORTS"]["REFUTES"] + c["REFUTES"]["SUPPORTS"],
        "no_information": sum(c[g]["NOT_ENOUGH_INFO"] for g in labels),
        "abstain": sum(c[g]["ABSTAIN"] for g in labels),
        "error": sum(c[g]["ERROR"] for g in labels),
    }
    e = op["edges"]
    if sum(row.values()) != op["n"] or row["correct_edge"] != e["correct"]:
        raise ValueError("Disposition counts do not conserve evaluation rows")
    if row["unsupported_edge"] + row["wrong_polarity"] != e["incorrect"]:
        raise ValueError("Typed edge errors disagree with confusion matrix")
    if e["accepted"] != e["correct"] + e["incorrect"]:
        raise ValueError("Accepted edge counts do not conserve")
    return row


def reliability(rows: list[dict], bins: int = 10) -> list[dict]:
    """Fixed equal-width bins of accepted-edge winning-label confidence.

    The rightmost bin includes 1. Empty bins are omitted, not set to zero.
    Operational failures and NOT_ENOUGH_INFO are not accepted edges.
    """
    if bins < 1:
        raise ValueError("bins must be positive")
    buckets = [[] for _ in range(bins)]
    for row in rows:
        if row["label"] not in ("SUPPORTS", "REFUTES"):
            continue
        score = row["score"]
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid confidence")
        buckets[min(int(score * bins), bins - 1)].append(row)
    return [{"bin": i, "lower": i/bins, "upper": (i+1)/bins, "n": len(bucket),
             "correct": sum(x["label"] == x["gold"] for x in bucket),
             "mean_confidence": math.fsum(x["score"] for x in bucket)/len(bucket),
             "accuracy": sum(x["label"] == x["gold"] for x in bucket)/len(bucket)}
            for i, bucket in enumerate(buckets) if bucket]


def collect(root: Path) -> dict:
    graph = load_reference(root, list(INPUTS)[0])
    fusion = load_reference(root, list(INPUTS)[1])
    backend = RecordedJev(root)
    if graph["input_sha256"] != backend.hashes or fusion["source_hashes"] != backend.hashes:
        raise ValueError("Studies do not share the verified frozen inputs")
    if fusion["evaluation_rows"] != 339 or fusion["fresh_http_calls"] != 0 or graph["fresh_model_calls"] != 0:
        raise ValueError("Unexpected experiment population or live inference")
    data = {"schema_version": 1, "source_sha256": {**INPUTS, **backend.hashes},
            "evaluation_rows": fusion["evaluation_rows"], "gold_typed_edges": 209,
            "interpretation": "Post-hoc fixed-candidate diagnostics; no new inference or deployment qualification.",
            "arms": [], "matched": [], "topology": [], "reliability": [],
            "withdrawals": [], "predicate_frontiers": [], "neighborhood": {}}
    for arm in ARMS:
        item = fusion["arms"][arm]
        op, usage = item["operational"], item["recorded_usage"]
        e = op["edges"]
        partition = dispositions(op)
        gold_edges = sum(sum(op["confusion"][g].values()) for g in ("SUPPORTS", "REFUTES"))
        if gold_edges != data["gold_typed_edges"] or op["n"] != data["evaluation_rows"]:
            raise ValueError("Inconsistent evaluation denominators")
        if not math.isclose(e["precision"], e["correct"]/e["accepted"], abs_tol=1e-12):
            raise ValueError("Precision denominator mismatch")
        if not math.isclose(e["recall"], e["correct"]/gold_edges, abs_tol=1e-12):
            raise ValueError("Recall denominator mismatch")
        if item["graph"]["committed_label_correct"] != e["correct"] or item["graph"]["committed_label_incorrect"] != e["incorrect"]:
            raise ValueError("Graph and independently counted edge outcomes disagree")
        data["arms"].append({"arm": arm, "name": NAMES[arm], **e, **partition,
                             "recorded_calls": usage["calls"], "recorded_input_tokens": usage["input_tokens"],
                             "input_tokens_per_correct_edge": usage["input_tokens"]/e["correct"],
                             "budget_curve": item["budget_curve"]})
    for task, title in (("entity_resolution", "Same identity"), ("relation_support", "Support link")):
        m = graph["tasks"][task]["matched_primary_action_count"]
        b = m["paired_precision_difference"]
        data["matched"].append({"name": title + ": selected - generic", "k": m["accepted_per_arm"],
                                "delta": m["selected"]["precision"] - m["baseline"]["precision"],
                                "interval": b["interval"], "draws": b["draws"], "units": b["units"],
                                "left_correct": m["baseline"]["true"], "right_correct": m["selected"]["true"]})
    for left, right in (("baseline_choice", "fewshot_contract"), ("fewshot_contract", "mean_pool"),
                        ("fewshot_contract", "agreement_gate"), ("fewshot_contract", "stacked")):
        m = fusion["comparisons"][left + "__vs__" + right]["matched_edges"]
        data["matched"].append({"name": NAMES[right] + " - " + NAMES[left], "k": m["k"],
                                "delta": m["precision_delta"], "interval": m["bootstrap"]["interval"],
                                "draws": m["bootstrap"]["draws"], "units": fusion["evaluation_components"],
                                "left_correct": m["left"]["correct"], "right_correct": m["right"]["correct"]})
    for task, task_name, baseline in (("relation_support", "SciFact", "baseline_choice"),
                                       ("entity_resolution", "Identity", "baseline_noul")):
        for arm, short in ((baseline, "Generic"), ("fewshot_contract", "Few-shot")):
            g = graph["tasks"][task][arm]["graph"]
            m, life = g["metrics"], g["lifecycle"]
            hist = m["weak_component_size_histogram"]
            if sum(int(size)*n for size, n in hist.items()) != m["nodes"] or sum(hist.values()) != m["weak_components"]:
                raise ValueError("Topology histogram does not conserve nodes/components")
            row = {"task": task, "arm": arm, "name": task_name + " / " + short,
                   "nodes": m["nodes"], "edges": m["typed_edges"], "isolates": m["isolates"],
                   "isolate_fraction": m["isolates"]/m["nodes"], "weak_components": m["weak_components"],
                   "largest_component": m["largest_component"], "histogram": hist,
                   "claims_with_opposing_source_labels": m["claims_with_opposing_source_labels"]}
            if task == "relation_support":
                # A directed Document -> Claim graph has D*C possible endpoint pairs,
                # not V*(V-1). This still does not measure candidate retrieval recall.
                possible = m["node_type_counts"]["Document"] * m["node_type_counts"]["Claim"]
                row.update(schema_eligible_pairs=possible, schema_pair_density=m["distinct_directed_pairs"]/possible)
                for label in ("SUPPORTS", "REFUTES"):
                    data["predicate_frontiers"].append({"arm": arm, "label": label,
                        "points": graph["tasks"][task][arm]["actions"][label]["frontier"]})
            data["topology"].append(row)
            if life["active_after_withdrawal"] + life["actual_retractions"] != life["original_assertions_preserved"]:
                raise ValueError("Withdrawal loses assertion history")
            data["withdrawals"].append({"name": row["name"], "initial": m["assertions"],
                "active_after": life["active_after_withdrawal"], "retracted": life["actual_retractions"],
                "history_preserved": life["original_assertions_preserved"], "reopen_equal": life["durable_reopen_equal"]})
    scored = {arm: read_scores(backend, "relation_support", arm, "evaluation") for arm in ARMS[:2]}
    for arm, rows in scored.items():
        bins = reliability(rows)
        n = sum(x["n"] for x in bins)
        correct = sum(x["correct"] for x in bins)
        expected = fusion["arms"][arm]["operational"]["edges"]
        if n != expected["accepted"] or correct != expected["correct"]:
            raise ValueError("Reliability observations disagree with archived edge counts")
        data["reliability"].append({"arm": arm, "accepted": n, "bins": bins})
    # Select a real neighborhood by candidate incidence, never by correctness.
    counts = Counter(x["row"]["claim_id"] for x in scored[ARMS[0]])
    claim = min(counts, key=lambda key: (-counts[key], key))
    right = {x["id"]: x for x in scored[ARMS[1]]}
    selected = sorted((x for x in scored[ARMS[0]] if x["row"]["claim_id"] == claim),
                      key=lambda x: x["row"]["document_id"])
    data["neighborhood"] = {"claim_id": claim,
        "selection": "Highest candidate document incidence; ties by claim ID lexicographically; gold not consulted.",
        "candidates": [{"id": x["id"], "document_id": x["row"]["document_id"],
                        "generic": x["label"], "fewshot": right[x["id"]]["label"], "gold": x["gold"]} for x in selected]}
    return data


def write_tables(data: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "data.json").write_bytes(encoded(data))
    for name, rows in (("edge_outcomes", data["arms"]), ("matched_precision", data["matched"]),
                       ("topology", data["topology"]), ("withdrawal", data["withdrawals"])):
        keys = list(dict.fromkeys(k for row in rows for k in row if not isinstance(row[k], (list, dict))))
        if name == "matched_precision":
            rows = [dict(row, interval_low=row["interval"][0], interval_high=row["interval"][1]) for row in rows]
            keys += ["interval_low", "interval_high"]
        text = io.StringIO(newline="")
        writer = csv.DictWriter(text, keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        (output / (name + ".csv")).write_bytes(text.getvalue().encode("utf-8"))


def render(data: dict, output: Path, png: bool = True) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 15,
                         "axes.labelsize": 12, "svg.fonttype": "none", "svg.hashsalt": "jev-graph-figures-v1"})
    output.mkdir(parents=True, exist_ok=True)

    def start(title, xlabel, ylabel, height=5.8):
        fig, ax = plt.subplots(figsize=(10.8, height), layout="constrained")
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.spines[["top", "right"]].set_visible(False)
        return fig, ax

    def save(fig, name, note):
        fig.supxlabel(note, fontsize=9)
        fig.savefig(output / (name + ".svg"), metadata={"Date": None, "Creator": "graph_synthesis.visualize_evidence"})
        if png:
            fig.savefig(output / (name + ".png"), dpi=240, metadata={"Software": "graph_synthesis.visualize_evidence"})
        plt.close(fig)

    names = [x["name"] for x in data["arms"]]
    fig, ax = start("What happens to all 339 SciFact candidates?", "Evaluation rows (one outcome per row)", "")
    bottoms = [0]*len(names)
    for key, label, hatch in (("correct_edge", "Correct typed edge", ""), ("unsupported_edge", "Edge / gold no-info", "///"),
                              ("wrong_polarity", "Wrong support/refute label", "xx"), ("no_information", "Predicted no-info", ".."),
                              ("abstain", "Explicit abstention", "++"), ("error", "Operational error", "oo")):
        values = [x[key] for x in data["arms"]]
        bars = ax.barh(names, values, left=bottoms, label=label, hatch=hatch)
        ax.bar_label(bars, labels=[str(x) if x >= 6 else "" for x in values], label_type="center", fontsize=10)
        bottoms = [a+b for a, b in zip(bottoms, values)]
    ax.set_xlim(0, data["evaluation_rows"])
    ax.invert_yaxis()
    ax.legend(ncols=2, loc="upper center", bbox_to_anchor=(.5, -.15), fontsize=10)
    save(fig, FIGURES[0], "Counts, not percentages. No-info is a model outcome, not necessarily correct or an abstention. Exact small counts: CSV.")

    fig, ax = start("Typed-edge precision must be read with recall", "Correct typed edges / 209 gold typed edges", "Correct typed edges / accepted edges")
    positions = [(.91, .84), (.80, .875), (.86, .915), (.765, .945), (.825, .795)]
    for row, position, marker in zip(data["arms"], positions, ("o", "s", "^", "D", "P")):
        ax.scatter(row["recall"], row["precision"], s=95, marker=marker)
        ax.annotate(f'{row["name"]}\n{row["correct"]}/{row["accepted"]} accepted correct',
                    (row["recall"], row["precision"]), xytext=position, textcoords="data", fontsize=10,
                    arrowprops={"arrowstyle": "-", "linewidth": .7})
    ax.set_xlim(.75, 1.02)
    ax.set_ylim(.76, .98)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    save(fig, FIGURES[1], "Post-hoc fixed-candidate comparisons. Axes are zoomed; points have different accepted counts. No KARMA score is plotted.")

    fig, ax = start("Equal-volume precision differences remain uncertain", "Precision difference (percentage points; right arm minus left)", "", 6.4)
    for i, row in enumerate(data["matched"]):
        lo, hi = [100*x for x in row["interval"]]
        delta = 100*row["delta"]
        ax.errorbar(delta, i, xerr=[[delta-lo], [hi-delta]], fmt="o", capsize=5)
        ax.text(1.01, i, f'K={row["k"]}', transform=ax.get_yaxis_transform(), va="center", fontsize=10)
    ax.set_yticks(range(len(data["matched"])), [x["name"] for x in data["matched"]], fontsize=10)
    ax.invert_yaxis()
    ax.axvline(0, linestyle="--", linewidth=1)
    save(fig, FIGURES[2], "Exploratory paired 95% component-bootstrap intervals: 1,000 draws (first two), 2,000 (others). No multiplicity correction.")

    fig, ax = start("Precision at the same accepted-edge budget", "Accepted typed edges K (score-ranked, label-independent tie break)", "Correct typed edges / K")
    for row, marker in zip(data["arms"], ("o", "s", "^", "D", "P")):
        points = row["budget_curve"]
        ax.plot([p["accepted"] for p in points], [p["precision"] for p in points], marker=marker, label=row["name"])
    ax.set_ylim(0, 1.04)
    ax.set_xlim(0, 225)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="lower left", fontsize=10)
    save(fig, FIGURES[3], "Only archived budgets are shown; no extrapolation. Exact-K sets can split confidence ties. This is not a deployable threshold policy.")

    fig, ax = start("Accepted evidence graphs are small and fragmented", "Weak component size (nodes)", "Number of weak components")
    for i, row in enumerate(data["topology"][:2]):
        xs = list(range(1, 7))
        bars = ax.bar([x + (i-.5)*.36 for x in xs], [row["histogram"].get(str(x), 0) for x in xs], .36,
                      label=f'{row["name"]}: {row["isolates"]}/{row["nodes"]} isolates', hatch="//" if i else "")
        ax.bar_label(bars, padding=3, fontsize=10)
    ax.set_xticks(range(1, 7))
    ax.set_ylim(0, 285)
    ax.legend(loc="upper right", fontsize=10)
    save(fig, FIGURES[4], "All 583 candidate nodes are retained. Identity graphs separately have 413 two-record components each; not large-cluster evidence.")

    fig, ax = start("Accepted-edge confidence is not a safety certificate", "Mean winning-label probability in fixed-width bin", "Observed typed-edge correctness in bin")
    for i, row in enumerate(data["reliability"]):
        points = row["bins"]
        ax.plot([p["mean_confidence"] for p in points], [p["accuracy"] for p in points],
                marker="o" if i == 0 else "s", label=f'{NAMES[row["arm"]]} (n={row["accepted"]})')
        for p in points:
            ax.annotate(f'n={p["n"]}', (p["mean_confidence"], p["accuracy"]),
                        xytext=(0, 10 if i == 0 else -17), textcoords="offset points", ha="center", fontsize=9)
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Equality reference")
    ax.set_xlim(0, 1.06)
    ax.set_ylim(0, 1.09)
    ax.legend(loc="lower right", fontsize=10)
    save(fig, FIGURES[5], "Evaluation-set diagnostic only. Ten fixed bins; empty bins omitted; p=1 retained. Dependent rows: no independent-binomial intervals.")

    fig, ax = start("Historical input usage per correct retained edge", "Recorded input tokens / correct typed edge", "")
    values = [x["input_tokens_per_correct_edge"] for x in data["arms"]]
    bars = ax.barh(names, values)
    ax.bar_label(bars, labels=[f'{v:,.0f}  ({r["recorded_calls"]} calls)' for v, r in zip(values, data["arms"])], padding=5)
    ax.set_xlim(0, max(values)*1.35)
    ax.invert_yaxis()
    save(fig, FIGURES[6], "Original evaluation input tokens only; excludes output tokens, retrieval, review, storage, calibration and fitting. Zero fresh calls.")

    fig, ax = start("Controlled withdrawal preserves assertion history", "Stored assertion count", "")
    rows = data["withdrawals"]
    names2 = [x["name"] for x in rows]
    active = [x["active_after"] for x in rows]
    bars = ax.barh(names2, active, label="Active after withdrawal")
    ax.bar_label(bars, label_type="center")
    bars = ax.barh(names2, [x["retracted"] for x in rows], left=active, hatch="///", label="Inactive, history retained")
    ax.bar_label(bars, labels=[f'-{x["retracted"]}; history={x["history_preserved"]}' for x in rows], padding=5, fontsize=10)
    ax.set_xlim(0, 540)
    ax.invert_yaxis()
    ax.legend(loc="lower center", bbox_to_anchor=(.5, -.25), ncols=2, fontsize=10)
    save(fig, FIGURES[7], "One constructed withdrawal per graph, not observed scientific retractions. Reopen and audit pass; no semantic accuracy claim.")

    fig, ax = start("A real supplied claim-document neighborhood", "", "", 6.5)
    hood = data["neighborhood"]
    rows = hood["candidates"]
    ax.set_xlim(-.2, 1.15)
    ax.set_ylim(-.9, len(rows)-.3)
    ax.axis("off")
    cy = (len(rows)-1)/2
    ax.scatter([1], [cy], s=2400, marker="s")
    ax.text(1, cy, 'Claim\n'+hood["claim_id"], ha="center", va="center", fontsize=11)
    for i, row in enumerate(rows):
        ax.scatter([0], [i], s=1600, marker="o")
        ax.text(0, i, row["document_id"], ha="center", va="center", fontsize=9)
        labels = [row["generic"], row["fewshot"], row["gold"]]
        actual = any(x in ("SUPPORTS", "REFUTES") for x in labels[:2])
        ax.annotate("", xy=(.93, cy), xytext=(.52, i),
                    arrowprops={"arrowstyle": "->", "linestyle": "-" if actual else ":", "alpha": .7})
        short = {"SUPPORTS": "S", "REFUTES": "R", "NOT_ENOUGH_INFO": "NEI", "ERROR": "ERR"}
        ax.text(.13, i, "G: " + short.get(labels[0], labels[0]) + " / F: " + short.get(labels[1], labels[1])
                + " / gold: " + short.get(labels[2], labels[2]), fontsize=10)
    save(fig, FIGURES[8], "Real IDs; largest candidate incidence, ties by claim ID. Dotted = candidate only. G=generic; F=few-shot; S=support; NEI=no-info.")

    fig, ax = start("Support and refutation have different risk-coverage trade-offs", "Accepted action count / all 339 evaluation candidates", "Incorrect accepted actions / accepted action count")
    for row, marker in zip(data["predicate_frontiers"], ("o", "s", "^", "D")):
        points = [p for p in row["points"] if p["accepted"]]
        ax.plot([p["coverage"] for p in points], [p["false"]/p["accepted"] for p in points],
                marker=marker, label=NAMES[row["arm"]] + " / " + row["label"])
    ax.set_xlim(0, .46)
    ax.set_ylim(0, .31)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="upper left", fontsize=10)
    save(fig, FIGURES[9], "Fixed thresholds: 0.50, 0.85, 0.90, 0.95, 0.99, 1.00. Empty acceptance omitted, not zero risk. Not false-positive rate among negatives.")


def build(root: Path, output: Path, png: bool = True) -> dict:
    data = collect(root)
    write_tables(data, output)
    render(data, output, png)
    sources = {**data["source_sha256"], "graph_synthesis/visualize_evidence.py": digest(Path(__file__).read_bytes())}
    names = ["data.json", "edge_outcomes.csv", "matched_precision.csv", "topology.csv", "withdrawal.csv"]
    names += [x + ".svg" for x in FIGURES]
    if png:
        names += [x + ".png" for x in FIGURES]
    manifest = {"source_sha256": sources, "outputs": {n: digest((output/n).read_bytes()) for n in names},
                "notes": "SVG has fixed IDs and no date metadata. PNG is a high-resolution convenience rendering. Frozen source files are never modified."}
    (output / "manifest.json").write_bytes(encoded(manifest))
    return manifest


def check(root: Path, output: Path) -> None:
    """Check source/data drift and every tracked rendering's integrity.

    Numerical data and SVG are regenerated and compared byte-for-byte. PNG
    integrity is checked against the manifest; PNG regeneration is not required.
    Use the pinned renderer for SVG comparison rather than tolerant image claims.
    """
    manifest = json.loads((output / "manifest.json").read_bytes())
    with tempfile.TemporaryDirectory(prefix="graph-figures-") as tmp:
        regenerated = Path(tmp)
        fresh = build(root, regenerated, png=False)
        if fresh["source_sha256"] != manifest["source_sha256"]:
            raise ValueError("Figure source lineage changed; regenerate figures")
        for name, expected in manifest["outputs"].items():
            if Path(name).name != name or digest((output/name).read_bytes()) != expected:
                raise ValueError("Changed or unsafe figure artifact: " + name)
        for name in fresh["outputs"]:
            if (output/name).read_bytes() != (regenerated/name).read_bytes():
                raise ValueError("Stale generated artifact (use pinned renderer): " + name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output or root / "graph_synthesis/evidence_figures"
    if args.check:
        check(root, output)
        print("Figure data, SVG regeneration, source lineage and artifact integrity passed.")
    else:
        build(root, output, png=not args.no_png)
        print("Wrote 10 evidence-backed figures and source tables to", output)


if __name__ == "__main__":
    main()
