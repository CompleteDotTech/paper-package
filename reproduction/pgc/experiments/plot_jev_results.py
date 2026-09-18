"""Standalone paired-effect plot from frozen Jev results; no API calls or fitting."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    result = json.loads((args.run_dir / "results.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    colors = {"relation_support": "#39759a", "entity_resolution": "#24795d"}
    for ax, metric, title in zip(axes, ("macro_f1", "accuracy"), ("Operational macro-F1", "Operational accuracy")):
        ax.axvline(0, color="0.55", linestyle="--", linewidth=1)
        for y, task in enumerate(("relation_support", "entity_resolution")):
            effect = result["tasks"][task]["evaluation_comparisons"]["raw"]["metrics"][metric]
            delta, (lo, hi) = effect["difference"] * 100, [v * 100 for v in effect["ci95"]]
            ax.errorbar(delta, y, xerr=[[delta-lo], [hi-delta]], fmt="o", capsize=5,
                        markersize=7, linewidth=2, color=colors[task])
            ax.annotate(f"{delta:+.2f} [{lo:+.2f}, {hi:+.2f}]", (delta, y),
                        xytext=(0, 17), textcoords="offset points", ha="center", fontsize=9)
        ax.set(yticks=[0, 1], yticklabels=["SciFact\n339 pairs", "DBLP–ACM\n413 pairs"],
               ylim=(-.55, 1.6), xlim=(-6, 7), xlabel="Selected Jev minus baseline (percentage points)", title=title)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", alpha=.15)
    fig.suptitle("Same Jev model: six training demonstrations versus the corrected baseline", fontsize=12)
    fig.text(.5, .015, "Paired 95% bootstrap intervals; prompts selected on development only. Unadjusted exploratory comparisons.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .92))
    output = args.run_dir / "figures"
    output.mkdir(exist_ok=True)
    for extension in ("svg", "png"):
        fig.savefig(output / ("paired_effects." + extension), dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(str(output))


if __name__ == "__main__":
    main()
