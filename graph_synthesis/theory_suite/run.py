"""Reproduce the ten-theory suite offline: python -B -m graph_synthesis.theory_suite.run."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import socket

from .analyses import BOOTSTRAPS, SEED, load, run_recorded
from .controlled import t07, t08, t09, t10

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TITLES = {
    "T01": "Group-conformal mutation contracts", "T02": "Correlated verification errors",
    "T03": "Rare-edge prior sensitivity", "T04": "Composed graph-risk budgets",
    "T05": "Topology-aware review value", "T06": "Calibration-selected decision cascades",
    "T07": "Joint identity decoding", "T08": "Dependency-complete semantic caching",
    "T09": "Alternative-proof survival", "T10": "Observable schema-migration contracts",
}


def _no_network(*args, **kwargs):
    raise RuntimeError("The theory suite is offline; fresh inference is prohibited")


def run(root: Path = ROOT) -> dict:
    old_socket = socket.socket
    socket.socket = _no_network
    try:
        backend, data, audit = load(root)
        results = run_recorded(data)
        results.update({"T07": t07(data), "T08": t08(), "T09": t09(), "T10": t10()})
    finally:
        socket.socket = old_socket
    source_paths = ["graph_synthesis/core.py", "graph_synthesis/recorded.py", "graph_synthesis/study.py"]
    source_paths += sorted(p.relative_to(root).as_posix() for p in (root / "graph_synthesis/theory_suite").rglob("*.py"))
    return {"schema_version": 1, "baseline_commit": "2c5184390bfa63740b44fb556a270418a6c1d882",
            "model": backend.plan["model"], "seed": SEED, "bootstrap_replicates": BOOTSTRAPS,
            "fresh_service_calls": 0, "recorded_input_hashes": backend.hashes,
            "source_hashes": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths},
            "source_overlap_audit": audit, "experiments": results,
            "status": "exploratory; no new model benchmark, universal guarantee, or comparison with KARMA"}


def clean_numbers(value):
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, dict):
        return {k: clean_numbers(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_numbers(v) for v in value]
    return value


def render(result: dict) -> str:
    lines = ["# Ten Jev graph-synthesis hypotheses: executed results", "",
             "This is exploratory reanalysis of archived Jev observations plus controlled systems experiments. "
             "**No new Jev service calls were made.** A met target is not a proven general theory. "
             "The original study and default compiler are unchanged.", "",
             f"Requested archived model: `{result['model']}`. Baseline commit: `{result['baseline_commit']}`. "
             f"Seed: {result['seed']}; paired component bootstrap replicates: {result['bootstrap_replicates']}.", "",
             "## Calibration and evidence separation", "",
             "Components use shared record IDs or claim/document IDs, not labels. Calibration components "
             "touching evaluation are purged. The earlier formulation selection already used the original "
             "calibration set: this purge does not retroactively create independent conformal calibration.", "",
             "| Task | Original calibration | Retained | Purged | Retained components | Evaluation rows / components |",
             "|---|---:|---:|---:|---:|---:|"]
    for task, a in result["source_overlap_audit"].items():
        lines.append(f"| {task} | {a['calibration_original_rows']} | {a['calibration_retained_rows']} | {a['calibration_purged_rows']} | {a['calibration_retained_components']} | {a['evaluation_rows']} / {a['evaluation_components']} |")
    lines += ["", "## Findings", ""]
    e = result["experiments"]
    for id_, title in TITLES.items():
        lines += [f"### {id_}: {title}", ""]
        if id_ == "T01":
            for task, r in e[id_].items():
                a, b = r['baseline'], r['contract']
                lines.append(f"**{task}:** wrong emitted edges {a['wrong']} → {b['wrong']}; correct edges {a['correct']} → {b['correct']}; retention {r['correct_edge_retention']:.2%}. Singleton contract accepted {b['accepted']} edges. Label-set coverage {r['row_label_coverage']:.2%}; all-label component coverage {r['all_labels_covered_component_fraction']:.2%}; target met: **{r['target_met']}**. Calibration quantile {r['fit']['quantile']:.6f} from {r['fit']['groups']} groups.")
            lines.append("Entity label-set coverage is below the nominal 90% level even though the error/retention target is met. This is a warning against interpreting this retrospective construction as a valid coverage guarantee. Relation singleton precision can also be worse than full-coverage precision: report correct-edge loss, not just fewer errors.")
        elif id_ == "T02":
            for task, r in e[id_].items():
                lines.append(f"**{task}:** {r['both_wrong']} double faults versus {r['independent_expected_double_faults']:.3f} expected under independence. Excess probability {r['double_fault_excess']:.4f}, descriptive 95% component-bootstrap interval {r['descriptive_component_bootstrap_95']}. Perfect-router accuracy upper bound {r['oracle_router_accuracy_upper_bound']:.2%}; best observed arm {r['best_observed_accuracy']:.2%}. Positive excess: **{r['target_met']}**; interval excludes zero: **{r['interval_excludes_zero']}**. The oracle uses gold and is not an implementable router.")
        elif id_ == "T03":
            for task, r in e[id_].items():
                for arm, a in r['arms'].items():
                    projected = a['projected_precision']['0.01']
                    lines.append(f"**{task} / {arm}:** observed {a['label']} precision {a['observed_precision']:.2%}; projected precision at 1% prevalence {projected:.2%}. False positives {a['fp']} / {a['gold_negative']} negative examples. At least 10-point drop: **{a['target_met']}**.")
            lines.append("These are Bayes-rule sensitivity projections, not deployment measurements. Conditional errors and the negative-class mixture are assumed unchanged; finite-sample uncertainty is not propagated into this grid.")
        elif id_ == "T04":
            for task, r in e[id_].items():
                a, b = r['fixed_095_gate'], r['raw_score_component_budget']
                lines.append(f"**{task}:** fixed gate accepts {a['accepted']} edges ({a['wrong']} wrong); component budget accepts {b['accepted']} ({b['wrong']} wrong). Any-error component frequency {b['component_error_frequency']:.2%}; correct-edge retention {r['correct_edge_retention']:.2%}; target met: **{r['target_met']}**. {r['wrong_edges_at_probability_one']} wrong positive edges carry confidence exactly one.")
            lines.append("The budget and fixed gate select the same number of edges on these sparse observed graphs; this does not establish an advantage from composition. The union-bound arithmetic is not the problem: unvalidated Jev scores are not certified conditional error probabilities. A point-estimate pass is not a graph-safety certificate.")
        elif id_ == "T05":
            for task, r in e[id_].items():
                lines.append(f"**{task}:** review budget {r['review_budget']} of {r['candidate_edges']} edges. Clean correct-edge neighborhoods: initial {r['before']['clean_correct_edges']}, uncertainty review {r['uncertainty_review']['clean_correct_edges']}, topology-aware {r['topological_review']['clean_correct_edges']}, random mean {r['random_mean_clean_correct_edges']:.3f}. Strict topology advantage: **{r['target_met']}**.")
            lines.append("This is a perfect equal-cost reviewer counterfactual on the observed sparse candidate graph; no reviewer or additional model was run. Missing candidate edges cannot be repaired by this experiment.")
        elif id_ == "T06":
            for task, r in e[id_].items():
                if 'fit' not in r:
                    lines.append(f"**{task}:** {r['status']}.")
                    continue
                lines.append(f"**{task}:** calibration-selected threshold {r['fit']['threshold']}; escalations {r['escalations']} / {r['evaluation_n']}. Macro-F1 {r['fewshot_macro_f1']:.6f} → {r['cascade_macro_f1']:.6f}; difference {r['macro_f1_difference']:+.6f}. Hypothetical input tokens {r['all_fewshot_input_tokens']:,} → {r['cascade_input_tokens']:,}; saving {1-r['input_token_ratio']:.2%}; joint cost/quality target met: **{r['target_met']}**.")
            r = e[id_]["relation_support"]
            if "cascade_edges" in r:
                a, b = r["fewshot_edges"], r["cascade_edges"]
                lines.append(f"For graph synthesis the relation cascade changes wrong emitted edges {a['wrong']} → {b['wrong']} and accepted-edge precision {a['precision']:.2%} → {b['precision']:.2%}. Therefore a macro-F1/cost target pass is NOT evidence that it is the better graph policy. Inspect edge metrics as well as classification averages.")
            lines.append("All baseline-first input tokens are charged, including those preceding a fallback. These are recorded single-decision token counts, not measured new service latency or invoices.")
        elif id_ == "T07":
            for arm, r in e[id_]['arms'].items():
                if 'worlds' not in r:
                    lines.append(f"**{arm}:** {r['status']}.")
                    continue
                lines.append(f"**{arm}:** {r['worlds']} synthetic six-node worlds. Greedy → exact: false merges {r['greedy']['false_merges']} → {r['exact']['false_merges']}; missed matches {r['greedy']['missed_matches']} → {r['exact']['missed_matches']}. Strict objective improvements in {r['strict_objective_improvement_worlds']} worlds; greedy order sensitivity in {r['greedy_order_sensitive_worlds']}. Truth-level target met: **{r['target_met']}**.")
            lines.append(e[id_]['assumptions'] + " Objective optimality must not be confused with correctness of synthetic pair truth. The fixed small worlds test an architectural mechanism, not full-corpus scalability.")
        elif id_ == "T08":
            r = e[id_]
            lines += [f"{r['requests']:,} simulated lookups across {r['decisions']} decisions and {r['epochs_including_initial']} epochs.", "", "| Cache key | Hits | Stale hits | Recomputations |", "|---|---:|---:|---:|"]
            for name, a in r['strategies'].items():
                lines.append(f"| {name} | {a['hits']} | {a['stale_hits']} | {a['recomputations']} |")
            lines += ["", f"Target met: **{r['target_met']}**. " + r['limitation']]
        elif id_ == "T09":
            r = e[id_]
            lines.append("Actual GraphStore execution of all 16 withdrawal subsets for Q=((s0 AND s1) OR s2) AND s3:")
            for name, a in r['strategies'].items():
                lines.append(f"{name}: {a['false_removals']} false removals, {a['false_retention']} false retentions.")
            lines.append(f"Target met: **{r['target_met']}**. " + r['limitation'])
        else:
            r = e[id_]
            lines.append(f"{r['type_valid_migrations']} type-valid controlled migrations, including {r['query_changing_migrations']} that change finite query answers. Type-only gate accepts all {r['drift_accepted_by_type_only_gate']} drifting migrations; preview query gate accepts {r['drift_accepted_by_query_gate']}; benign false rejections {r['benign_rejected_by_query_gate']}. Original database unchanged: **{r['original_unchanged']}**. Target met: **{r['target_met']}**. " + r['limitation'])
        lines += [""]
    lines += ["## Scientific interpretation and next validation", "",
              "Treat Jev as an evidence-bound local decision component, not as a source of automatically valid global graph probabilities. "
              "Joint decoding, abstention, routing, caching, lineage, and migration contracts operate at different layers and require separate evaluation. "
              "Do not count controlled invariant passes as accuracy improvements or combine the ten endpoints into a single success rate.", "",
              "T01–T06 reuse the same historical observations and are exploratory. T07 resamples historical scores onto synthetic truths; "
              "T08 uses a digest oracle; T09–T10 use hand-specified source logic and schema queries. There are no fresh full-paper extraction "
              "results, externally adjudicated new labels, qualified biomedical relation tests, model-drift measurements, or matched KARMA comparisons. "
              "A confirmatory follow-up needs a newly collected, source-disjoint corpus; fixed prompts, calibration and cost policies; "
              "document-level human edge/qualifier adjudication; repeated fresh service measurements; and multiplicity-aware primary endpoints.", "",
              "All methods and thresholds are specified in [PROTOCOL.md](PROTOCOL.md). Exact counts, token grids, synthetic cases, "
              "source hashes and assumptions are in [results.json](results.json). Reproduce with "
              "`python -B -m graph_synthesis.theory_suite.run --check` and "
              "`python -B -m unittest discover -s graph_synthesis/theory_suite/tests -v`.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    parser.add_argument("--report", type=Path, default=HERE / "RESULTS.md")
    parser.add_argument("--check", action="store_true", help="Compare regenerated outputs; do not overwrite")
    args = parser.parse_args()
    result = clean_numbers(run())
    outputs = {args.output: json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", args.report: render(result)}
    for path, text in outputs.items():
        if args.check:
            if path.read_text(encoding="utf-8") != text:
                raise SystemExit("Reproduction mismatch: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    print("Ten experiments reproduced; fresh service calls: 0; " + ("committed outputs match" if args.check else "results written"))


if __name__ == "__main__":
    main()
