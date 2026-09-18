"""Render standalone scientific plots from saved results; no inference or refitting."""

import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(__file__).resolve().parents[2] / "results" / "research"
    nli = json.loads((root / "nli_results.json").read_text(encoding="utf-8"))
    er = json.loads((root / "er_results.json").read_text(encoding="utf-8"))
    output = root / "figures"
    output.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.bbox": "tight"})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3))
    for ax, title, summaries in [
        (axes[0], "SciFact: full abstract", [("Raw", nli["metrics"]["full"]), ("Calibrated", nli["metrics"]["full_calibrated"]) ]),
        (axes[1], "Identity matching: full context", [("Raw", er["arms"]["er-full-context"]["summary"]),
                                                     ("Calibrated", er["arms"]["er-full-context-calibrated"]["summary"])])]:
        ax.plot([0, 1], [0, 1], color="0.65", linestyle="--", label="Perfect reliability")
        for series_index, (label, summary) in enumerate(summaries):
            bins = [b for b in summary["reliability_bins"] if b["count"]]
            line, = ax.plot([b["mean_confidence"] for b in bins], [b["accuracy"] for b in bins], marker="o", label=label)
            for b in bins:
                ax.annotate(str(b["count"]), (b["mean_confidence"], b["accuracy"]),
                            xytext=(-2, 7 if series_index == 0 or b["accuracy"] < 0.05 else -13), ha="right",
                            color=line.get_color(), textcoords="offset points", fontsize=7)
        ax.set(xlim=(0, 1.02), ylim=(0, 1.08), xlabel="Mean top-class confidence", ylabel="Observed accuracy", title=title)
        ax.legend(fontsize=8, loc="upper left")
    for label, key in [("Full", "full"), ("Full calibrated", "full_calibrated"), ("Selected calibrated", "selected_calibrated")]:
        values = [p for p in nli["metrics"][key]["selective_accuracy"] if p["accepted_count"]]
        axes[2].plot([p["coverage"] for p in values], [1-p["accuracy"] for p in values], marker="o", label=label)
    axes[2].set(xlabel="Fraction of eligible examples selected", ylabel="Classification error among selected", title="SciFact: confidence selection", xlim=(0, 1.02), ylim=(0, 1))
    axes[2].legend(fontsize=8)
    fig.suptitle("Held-out reliability and coverage — numbers beside points are bin counts", y=1.04)
    fig.tight_layout()
    fig.savefig(output / "reliability_and_coverage.svg")
    fig.savefig(output / "reliability_and_coverage.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, entries, title in [
        (axes[0], [("Training prior", nli["metrics"]["train_prior"]), ("80 characters", nli["metrics"]["prefix80"]),
                   ("Full evidence", nli["metrics"]["full"]), ("Selected evidence", nli["metrics"]["selected"])], "SciFact cited-abstract classification"),
        (axes[1], [("Lexical", er["arms"]["lexical-logistic"]["summary"]), ("Title only", er["arms"]["er-title-only"]["summary"]),
                   ("Full context", er["arms"]["er-full-context"]["summary"]), ("No hard negatives", er["arms"]["er-no-hard-negatives"]["summary"])], "DBLP-ACM identity matching")]:
        x = list(range(len(entries)))
        bars = ax.bar(x, [100*s["accuracy"] for _, s in entries], color=["#8c9da8", "#486e84", "#20756d", "#b27038"])
        ax.bar_label(bars, fmt="%.2f%%", padding=3, fontsize=9)
        ax.set(xticks=x, xticklabels=[name for name, _ in entries], ylabel="Held-out accuracy (%)", ylim=(0, 108), title=title)
        ax.tick_params(axis="x", labelrotation=15)
    fig.suptitle("Point estimates on different tasks; paired intervals and limitations are in the reports", y=1.02)
    fig.tight_layout()
    fig.savefig(output / "observed_accuracy.svg")
    fig.savefig(output / "observed_accuracy.png", dpi=180)
    plt.close(fig)
    print(f"Wrote four standalone figures to {output}")


if __name__ == "__main__":
    main()
