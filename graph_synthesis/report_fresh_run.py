"""Generate paper update and figures from saved fresh-run evidence; no inference."""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build(run):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"svg.hashsalt": "jev-fresh-20260918", "font.size": 10})
    current = json.loads((run / "results.json").read_text())
    original = json.loads((ROOT / "reproduction/results/jev/run-20260918/results.json").read_text())
    challenge = json.loads((run / "challenge/evaluation.json").read_text())
    audit = json.loads((run / "challenge/execution-audit.json").read_text())
    falsification = json.loads((ROOT / "experiments/falsification/results.json").read_text())
    def evaluation_rows(path):
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        return {(r["task"], r["arm"], r["id"]):r for r in values if r["split"] == "evaluation"}
    before = evaluation_rows(ROOT / "reproduction/results/jev/run-20260918/predictions.jsonl")
    after = evaluation_rows(run / "predictions.jsonl")
    stability = []
    for task, data in current["tasks"].items():
        for role in ("baseline", "selected"):
            arm = data["selection"][role]
            keys = [k for k in after if k[:2] == (task, arm) and k in before]
            pairs = [(before[k], after[k]) for k in keys]
            valid = [(a,b) for a,b in pairs if not a["error"] and not b["error"]]
            changed = sum(max(a["distribution"], key=a["distribution"].get) != max(b["distribution"], key=b["distribution"].get) for a,b in valid)
            stability.append({"task": task, "arm": arm, "paired": len(pairs), "common_valid": len(valid),
                              "changed_labels": changed, "identical_distributions": sum(a["distribution"] == b["distribution"] for a,b in valid)})
    out = run / "figures"
    out.mkdir(exist_ok=True)
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(out / (name + ".png"), dpi=180, bbox_inches="tight")
        fig.savefig(out / (name + ".svg"), metadata={"Date": None}, bbox_inches="tight")
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    rows = []
    for ax, task in zip(axes, ("entity_resolution", "relation_support")):
        for x, (name, data) in enumerate((("Original", original), ("Fresh", current))):
            t = data["tasks"][task]
            for offset, role, color in ((-.17, "baseline", "#416788"), (.17, "selected", "#20856b")):
                arm = t["selection"][role]
                score = t["scores"]["evaluation"][arm]["raw"]
                ax.bar(x + offset, score["macro_f1"], width=.32, color=color, label=role if x == 0 else None)
                ax.text(x + offset, score["macro_f1"] + .012, f'{score["macro_f1"]:.4f}', ha="center", fontsize=8)
                rows.append({"run": name, "task": task, "role": role, "arm": arm,
                             **{k: score[k] for k in ("n_examples", "accuracy", "macro_f1", "n_errors", "confusion", "brier_score", "log_loss")}})
        ax.set(xticks=[0, 1], xticklabels=["Original", "Fresh"], ylim=(0, 1.08),
               ylabel="Operational macro-F1", title=task.replace("_", " ").title())
        ax.legend(loc="lower right")
    save(fig, "run_comparison")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, task in zip(axes, ("entity_resolution", "relation_support")):
        data = current["tasks"][task]
        for index, role in enumerate(("baseline", "selected")):
            arm = data["selection"][role]
            scores = data["scores"]["evaluation"][arm]
            for offset, version, color in ((-.16, "raw", "#416788"), (.16, "calibrated", "#bd6547")):
                value = scores[version]["brier_score"]
                ax.bar(index + offset, value, .3, color=color, label=version if index == 0 else None)
        ax.set(xticks=[0, 1], xticklabels=["Baseline", "Selected"], ylabel="Multiclass Brier (lower is better)",
               title=task.replace("_", " ").title())
        ax.legend()
    save(fig, "fresh_calibration")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    families = list(challenge["by_family"])
    values = [challenge["by_family"][k]["correct"] for k in families]
    ax.barh([k.replace("_", " ") for k in families], values, color=["#20856b" if v == 4 else "#bd6547" for v in values])
    ax.set(xlim=(0, 4.5), xticks=range(5), xlabel="Correct cases / 4 (provisional synthetic labels)", title="Fresh Jev challenge: 48 cases, 24 paired groups")
    save(fig, "challenge_families")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    losses = falsification["tasks"]["relation_support"]["candidate_loss"]
    x = [100 * r["loss_fraction"] for r in losses]
    for arm, color in (("generic", "#416788"), ("fewshot", "#20856b")):
        values = [r["arm_recall"][arm] for r in losses]
        ax.plot(x, [100 * v["mean"] for v in values], "o-", color=color, label=arm)
        ax.fill_between(x, [100 * v["p05"] for v in values], [100 * v["p95"] for v in values], alpha=.13, color=color)
    ax.plot(x, [100*r["surviving_gold_oracle_recall"]["mean"] for r in losses], "k--", label="surviving-gold ceiling")
    ax.set(xlabel="Removed source groups (%)", ylabel="Recall against original gold (%)", ylim=(0, 105),
           title="Archived outputs + synthetic candidate loss; bands: intervention p05–p95")
    ax.legend()
    save(fig, "candidate_loss")
    summary = {"classification": "fresh_service_rerun_on_previous_fixed_data", "rows": rows, "cross_run_stability": stability,
               "challenge": challenge["overall"], "usage": current["usage"], "challenge_usage": audit,
               "effects": {t:v["evaluation_comparisons"]["raw"]["metrics"] for t,v in current["tasks"].items()}}
    (run / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# Fresh Jev execution and graph-synthesis falsification", "", "Timothy Wayne Gregg — updated research draft, September 18, 2026", "",
             "## Evidence scope", "",
             "This update executes a fresh pinned Jev 1.13.0 service run of the original development, calibration, evaluation, fixture, repeatability and batching protocol. It uses the same data and development-only selection rule. It is a same-data service repeat, not independent validation, a new preregistration, or a new training run. No evaluation labels were used to retune the prompts. The separate 48-case public synthetic challenge uses its exact gold-free exported inputs and fixed question contract; its AI-assisted labels remain provisional pending human adjudication.", "",
             "## Fresh results", "", "| Task | Run | Arm | Accuracy | Macro-F1 | Invalid responses |", "|---|---|---|---:|---:|---:|"]
    for row in rows:
        lines.append(f'| {row["task"]} | {row["run"]} | {row["arm"]} | {row["accuracy"]:.4%} | {row["macro_f1"]:.6f} | {row["n_errors"]} |')
    lines += ["", "![Original and fresh comparison](figures/run_comparison.png)", ""]
    for task, data in current["tasks"].items():
        effect = data["evaluation_comparisons"]["raw"]["metrics"]["macro_f1"]
        lines += [f'**{task}:** selected-minus-baseline macro-F1 = {effect["difference"]:+.6f}; exploratory paired 95% interval [{effect["ci95"][0]:+.6f}, {effect["ci95"][1]:+.6f}]. {data["conclusion"]}', ""]
    er = current["tasks"]["entity_resolution"]
    for role in ("baseline", "selected"):
        c = er["scores"]["evaluation"][er["selection"][role]]["raw"]["confusion"]
        lines.append(f'Entity {role}: {c["different"]["same"]} false merges and {c["same"]["different"]} missed matches. Service failures, if any, are separately retained in the table.')
    lines += ["", "The intervention bundles explicit instructions, typed question format and demonstrations. These runs cannot isolate causal contributions of each ingredient. Intervals are conditional on development selection, unadjusted and exploratory. Repeating this test set does not increase its number of independent entities or documents.", "",
              "![Fresh calibration comparison](figures/fresh_calibration.png)", "",
              "Calibration temperatures are fitted on the separate calibration partition. Brier scores use valid eligible responses, while operational accuracy and F1 retain failures. Calibration changes probability scores, not the selected labels; improvements in one scoring rule do not establish calibrated transaction-level safety.", "",
              "## Fresh repeatability and resource accounting", ""]
    for repeat in current["repeatability"]:
        lines.append(f'- {repeat["task"]} / {repeat["arm"]}: {repeat["n_examples_with_all_three_fresh_labels_identical"]}/{repeat["n_examples"]} examples had identical labels across the three fresh responses; {repeat["argmax_flips"]} pairwise argmax flips.')
    lines += ["", "Across the original and fresh held-out evaluations (distinct from the within-run 20-case panels):", "",
              "| Task / arm | Common valid pairs | Changed labels | Identical distributions |", "|---|---:|---:|---:|"]
    for value in stability:
        lines.append(f'| {value["task"]} / {value["arm"]} | {value["common_valid"]}/{value["paired"]} | {value["changed_labels"]} | {value["identical_distributions"]} |')
    usage = current["usage"]
    lines += ["", f'The main run records {usage["n_calls"]:,} logical calls, {usage["n_http_attempts"]:,} HTTP attempts, {usage["reported_input_tokens"]:,} input tokens and {usage["n_failed_calls"]} failed calls. Estimated cost at the original protocol price is ${usage["estimated_usd_for_reported_usage"]:.6f}; this is not a current price quote or invoice. The challenge adds {audit["requests"]} requests and {audit["input_tokens"]:,} input tokens. Probability variation remains distinct from label stability.', "",
              "## Fresh synthetic challenge", "",
              f'Against provisional labels, Jev classified {challenge["overall"]["correct"]}/48 correctly and got both cases correct in {challenge["paired_cases_all_correct"]}/24 paired groups. It accepted {challenge["overall"]["accepted_edges"]} positive edges, of which {challenge["overall"]["wrong_edges"]} were wrong. These small, public, hand-constructed cases are diagnostics, not a deployment-risk estimate.', "",
              "![Synthetic challenge results](figures/challenge_families.png)", "", "| Case | Family | Provisional gold | Jev |", "|---|---|---|---|"]
    for row in challenge["decisions"]:
        if row["label"] != row["gold"]:
            lines.append(f'| {row["id"]} | {row["family"]} | {row["gold"]} | {row["label"]} |')
    lines += ["", "The generic imported-journal evaluator retains `fresh_execution_verified: false`: hashes alone do not authenticate provider execution. The companion live execution audit and raw journals separately record the actual HTTPS responses and bind their requests. Gold labels, rationales, families and pair IDs were excluded from inference payloads.", "",
              "## Reproduced graph falsification findings", "",
              "PR #10's reference results reproduce exactly. On the original unequal-acceptance SciFact operating points, complete, error-free positive components fall from 140/164 to 126/164 with few-shot prompting, despite improved edge precision. The paired interval for the component difference is approximately [-13.30, -3.70] percentage points. This is not a matched-volume comparison and does not contradict the earlier unresolved matched-volume result. The formulations share 34 errors across 336 common-success examples, including 31 wrong-label agreements; their judgments are not independent corroboration. Five of 73 few-shot positive actions scored exactly 1.0 were wrong.", "",
              "![Candidate availability intervention](figures/candidate_loss.png)", "",
              "Candidate-loss bands describe variation over 100 synthetic removal masks, not confidence intervals or new retrieval measurements. Compiler witnesses remain constructed: a false identity bridge between two 100-record clusters induces 10,000 false cross-cluster identities; explicit retraction repairs them. Exact qualifier comparison misses overlapping temporal intervals. Twenty seeded repair episodes exercise 1,600 assertions and 782 withdrawals. These deterministic properties do not establish Jev factual correctness.", "",
              "## Interpretation and next experiment", "",
              "The original entity macro-F1 interval excluded zero; the fresh-run interval includes it. The descriptive entity advantage persists but its interval-based finding does not reproduce in this run. Neither task establishes a resolved fresh macro-F1 improvement. Independent identity-disjoint data and larger clusters remain necessary. Relation precision, recall, component completeness and total accuracy answer different questions. Do not select a universal winner from one metric, promote correlated fusion without matched-cost benefit, or infer production safety from typed outputs. Prioritize independent entity-matching confirmation and controlled ablations before further prompt tuning on this already inspected test set.", "",
              "## Artifacts and reproduction", "",
              "The run directory contains the frozen plan, captured source, raw requests/responses, prediction journal, calibration, analysis, verification, challenge evidence and figures. `python -B -m graph_synthesis.report_fresh_run --run-dir experiments/jev-rerun-20260918` regenerates this update and its four graphics without inference. The original study and its 161-file inventory remain unchanged. The current full manuscript incorporates this update before the original study as explicitly historical evidence.", ""]
    paper = "\n".join(lines)
    (run / "PAPER_UPDATE.md").write_text(paper, encoding="utf-8")
    historical = (ROOT / "manuscript/paper.md").read_text(encoding="utf-8")
    # Both full manuscripts live in manuscript/, so original relative links stay valid.
    current_text = paper.replace("](figures/", "](../experiments/jev-rerun-20260918/figures/")
    current_text += "\n\n---\n\n# Original study (historical evidence; unchanged text)\n\n" + historical
    (ROOT / "manuscript/paper-current.md").write_text(current_text, encoding="utf-8")
    print(json.dumps({"figures": 4, "paper": "manuscript/paper-current.md"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    build(parser.parse_args().run_dir)
