"""Run bounded synthetic E5/E7/E8 mechanisms without model/API dependencies.

    python -m pgc.research.advanced_experiments

These controlled simulations establish implementation behavior, not performance
on real entities, scientific claims, or calibrated neural model probabilities.
"""

import argparse
import hashlib
import json
import math
import platform
import random
import subprocess
import time
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from statistics import mean

from .policies import (
    DevelopmentOutcome, EvidenceScore, QueryContext, ValueOfInformationRouter,
    aggregate_evidence, dependency_risk, exact_identity_clustering,
    greedy_identity_clustering, identity_pairs, pairwise_metrics, select_queries,
)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _split_manifest(name, count, seed):
    ids = [f"{name}:{index}" for index in range(count)]
    return {"name": name, "episodes": count, "seed": seed,
            "episode_ids_sha256": _digest(ids)}


def paired_bootstrap(left, right, seed, resamples=1000):
    """Percentile interval for the mean paired episode difference, left-right."""
    if not left or len(left) != len(right):
        raise ValueError("Paired bootstrap requires equal, nonempty episode vectors")
    if resamples < 100:
        raise ValueError("Use at least 100 bootstrap resamples")
    differences = [a - b for a, b in zip(left, right)]
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(resamples))
    return {"mean_difference": mean(differences),
            "ci95": [estimates[int(0.025 * resamples)], estimates[min(resamples - 1, int(0.975 * resamples))]],
            "independent_episode_count": len(differences), "bootstrap_resamples": resamples,
            "direction": "first policy minus second policy"}


def _table(rows_by_policy):
    return {policy: {metric: mean(row[metric] for row in rows)
                     for metric in rows[0]} for policy, rows in rows_by_policy.items()}


def _compare(rows, first, second, metric, seed, resamples):
    return {"first": first, "second": second, "metric": metric,
            **paired_bootstrap([row[metric] for row in rows[first]],
                               [row[metric] for row in rows[second]], seed, resamples)}


def evidence_experiment(seed, episodes, resamples):
    """Independent noisy source origins, dependent derivative passages and copies."""
    rng = random.Random(seed)
    rows = {name: [] for name in ("naive", "exact_dedup", "grouped", "wrong_all_sources_one_group")}
    source_accuracy = 0.72
    magnitude = math.log(source_accuracy / (1 - source_accuracy))
    for episode in range(episodes):
        truth = rng.choice((0, 1))
        evidence = []
        for origin in range(3):
            observed = truth if rng.random() < source_accuracy else 1 - truth
            score = magnitude * (1 if observed else -1)
            # Derivative passages share exactly one latent source observation.
            for passage in range(rng.choice((1, 2, 4))):
                item = EvidenceScore(f"eval:{episode}:source:{origin}", f"eval:{episode}:group:{origin}",
                                     f"episode {episode}, origin {origin}, derivative {passage}, sign {observed}", score)
                evidence.extend([item] * rng.choice((1, 2, 5, 10)))
        for policy in rows:
            if policy == "wrong_all_sources_one_group":
                supplied = [replace(item, group_id="incorrect-common-origin") for item in evidence]
                probability = aggregate_evidence(supplied)["probability"]
            else:
                probability = aggregate_evidence(evidence, mode=policy)["probability"]
            clipped = min(1 - 1e-12, max(1e-12, probability))
            rows[policy].append({"brier_one_coordinate": (probability - truth) ** 2,
                                 "log_loss": -math.log(clipped if truth else 1 - clipped),
                                 "accuracy": float((probability >= 0.5) == bool(truth)),
                                 "coverage": 1.0, "extra_queries": 0})
    support = EvidenceScore("paper-A", "origin-A", "A supports the claim", 2.0)
    independent = EvidenceScore("paper-B", "origin-B", "B independently supports the claim", 2.0)
    contradiction = EvidenceScore("paper-C", "origin-C", "C contradicts the claim", -3.0)
    single = aggregate_evidence([support])["probability"]
    duplicate = {str(count): aggregate_evidence([support] * count)["probability"] for count in (1, 2, 5, 10)}
    relabeled_copy = replace(support, source_id="copy", group_id="copy-origin")
    return {"experiment": "E5", "execution_mode": "synthetic",
            "primary_metric": "one-coordinate binary Brier score; lower is better",
            "split": _split_manifest("evidence-evaluation", episodes, seed),
            "development": "No fitted parameters; group mean and source likelihood fixed before evaluation.",
            "generator": {"prior": 0.5, "source_accuracy": source_accuracy, "independent_origins_per_claim": 3,
                          "derivative_count_options": [1, 2, 4], "exact_copy_count_options": [1, 2, 5, 10]},
            "table": _table(rows),
            "paired_comparisons": [_compare(rows, a, b, "brier_one_coordinate", seed + index + 1, resamples)
                                   for index, (a, b) in enumerate((("grouped", "naive"),
                                       ("grouped", "exact_dedup"), ("wrong_all_sources_one_group", "grouped")))],
            "invariance_probes": {"single_support": single, "exact_copies": duplicate,
                "copy_with_new_source_label": aggregate_evidence([support, relabeled_copy])["probability"],
                "independent_corroboration": aggregate_evidence([support, independent])["probability"],
                "independent_contradiction": aggregate_evidence([support, contradiction])["probability"]},
            "limitations": ["Source group identities are known in this simulation; real provenance grouping is unresolved.",
                            "A mean within a source group is only a heuristic outside this generating model.",
                            "Misspecified common-origin grouping intentionally loses independent corroboration."]}


def identity_experiment(seed, episodes, resamples):
    conditions = {}
    nodes = tuple("abcdef")
    truth = identity_pairs((("a", "b", "c"), ("d", "e", "f")))
    universe = list(combinations(nodes, 2))
    for offset, condition in enumerate(("coherent_control", "noisy_bridges", "misspecified_hard_rule")):
        rng = random.Random(seed + offset)
        rows = {name: [] for name in ("independent", "union_find", "reject_conflict", "joint_exact")}
        timings = {name: [] for name in rows}
        for episode in range(episodes):
            probabilities = {pair: rng.uniform(0.75, 0.97) if pair in truth else rng.uniform(0.01, 0.2)
                             for pair in universe}
            if condition == "noisy_bridges":
                for pair in rng.sample([pair for pair in universe if pair not in truth], 2):
                    probabilities[pair] = rng.uniform(0.65, 0.95)
                probabilities[rng.choice(sorted(truth))] = rng.uniform(0.1, 0.4)
            # This models an observed conflicting stable identifier; in the last
            # condition that metadata is wrong. Every policy receives the same rule.
            cannot_link = (("a", "b"),) if condition == "misspecified_hard_rule" else (("a", "d"),)
            for policy in rows:
                started = time.perf_counter()
                searched = 0
                if policy == "independent":
                    predicted = {pair for pair, p in probabilities.items() if p >= 0.5}
                elif policy == "joint_exact":
                    result = exact_identity_clustering(nodes, probabilities, cannot_link=cannot_link)
                    predicted = identity_pairs(result["partition"])
                    searched = result["partitions_searched"]
                else:
                    predicted = identity_pairs(greedy_identity_clustering(
                        nodes, probabilities, reject_conflict=policy == "reject_conflict", cannot_link=cannot_link))
                timings[policy].append(time.perf_counter() - started)
                rows[policy].append({**pairwise_metrics(nodes, predicted, truth, cannot_link),
                                     "decision_coverage": 1.0, "extra_queries": 0,
                                     "partitions_searched": searched})
        conditions[condition] = {"split": _split_manifest(f"identity-{condition}-evaluation", episodes, seed + offset),
            "table": _table(rows), "mean_wall_seconds": {key: mean(values) for key, values in timings.items()},
            "paired_comparisons": [_compare(rows, "joint_exact", comparator, "pairwise_f1", seed + offset * 10 + index,
                                             resamples) for index, comparator in enumerate(("independent", "union_find", "reject_conflict"))]}
    return {"experiment": "E7", "execution_mode": "synthetic",
            "primary_metric": "pairwise F1 averaged over independent six-entity components; higher is better",
            "development": "No parameters fitted; threshold 0.5 and likelihood objective fixed in advance.",
            "generator": "Two true triples, five true positive pair scores and two spurious bridges in the noisy condition; one genuine positive is noisy negative. Exact decoding retains all 15 scores.",
            "conditions": conditions,
            "limitations": ["Independent predictions need not form an equivalence relation; their transitivity violations are counted.",
                            "Union-find deliberately ignores negative scores and hard rules after selecting positive edges.",
                            "Pair decisions have full coverage; predicted positive pair counts are reported and need not match.",
                            "Exact search is exponential and restricted to at most eight entities.",
                            "A wrong hard rule can force a structurally consistent, semantically worse result."]}


def _dependency_episodes(seed, episodes, coupling, shared):
    rng = random.Random(seed)
    result = []
    for episode in range(episodes):
        mutation_count = rng.randint(2, 6)
        errors = {}
        required_by_mutation = []
        for index in range(mutation_count):
            identity_id = "identity-shared" if shared else f"identity-{index}"
            if identity_id not in errors:
                errors[identity_id] = rng.uniform(0.005, 0.18)
            support_id = f"support-{index}"
            errors[support_id] = rng.uniform(0.003, 0.09)
            required_by_mutation.append((identity_id, support_id))
        probabilities = {key: 1 - value for key, value in errors.items()}
        uniform = rng.random()
        position = 0
        failures = set()
        for dependency, error in errors.items():
            if coupling == "independent":
                failed = rng.random() < error
            elif coupling == "positive_shared_noise":
                failed = uniform < error
            else:
                # Contiguous intervals on the unit circle preserve each marginal
                # and attain the union bound, including when their sum exceeds 1.
                failed = (uniform - position) % 1 < error
                position += error
            if failed:
                failures.add(dependency)
        true_risk = (1 - math.prod(probabilities.values()) if coupling == "independent"
                     else max(errors.values()) if coupling == "positive_shared_noise"
                     else min(1.0, sum(errors.values())))
        result.append({"episode_id": episode,
                       "estimates": {method: dependency_risk(probabilities, probabilities, method, primary="support-0")
                                     for method in ("single", "product", "union")},
                       "true_risk": true_risk, "corrupted": int(bool(failures)),
                       "damaged_mutations": sum(bool(set(required) & failures) for required in required_by_mutation),
                       "mutation_count": mutation_count, "unique_dependencies": len(errors)})
    return result


def _risk_rows(episodes, accepted):
    return [{"coverage": int(index in accepted),
             "expected_corruption_per_episode": item["true_risk"] if index in accepted else 0,
             "observed_corruption_per_episode": item["corrupted"] if index in accepted else 0,
             "damaged_mutations_per_episode": item["damaged_mutations"] if index in accepted else 0,
             "accepted_mutations_per_episode": item["mutation_count"] if index in accepted else 0,
             "extra_queries": 0} for index, item in enumerate(episodes)]


def _risk_table(rows):
    table = _table(rows)
    for policy, values in table.items():
        coverage = values["coverage"]
        values["expected_corruption_given_commit"] = values["expected_corruption_per_episode"] / coverage if coverage else None
        values["observed_corruption_given_commit"] = values["observed_corruption_per_episode"] / coverage if coverage else None
    return table


def _risk_selection(episodes, policy, coverage, match_mutation_counts=True):
    """Match episode and mutation coverage without looking at true risks/errors."""
    target = int(len(episodes) * coverage)
    if not match_mutation_counts:
        return set(sorted(range(len(episodes)), key=lambda index:
                   (episodes[index]["estimates"][policy], index))[:target])
    strata = {}
    for index, item in enumerate(episodes):
        strata.setdefault(item["mutation_count"], []).append(index)
    quotas = {size: int(len(indices) * coverage) for size, indices in strata.items()}
    # Largest-remainder rounding preserves the exact episode quota and gives
    # every policy identical counts from every transaction-size stratum.
    remainder_order = sorted(strata, key=lambda size: (-(len(strata[size]) * coverage - quotas[size]), size))
    for size in remainder_order[:target - sum(quotas.values())]:
        quotas[size] += 1
    accepted = set()
    for size, indices in strata.items():
        ranked = sorted(indices, key=lambda index: (episodes[index]["estimates"][policy], index))
        accepted.update(ranked[:quotas[size]])
    return accepted


def _risk_comparison(episodes, first, second, coverage, seed, resamples):
    """Resample whole episodes and repeat selection to preserve matched quotas."""
    def difference(sample):
        first_set = _risk_selection(sample, first, coverage)
        second_set = _risk_selection(sample, second, coverage)
        return (sum(sample[index]["true_risk"] for index in first_set) -
                sum(sample[index]["true_risk"] for index in second_set)) / len(sample)
    rng = random.Random(seed)
    values = sorted(difference(rng.choices(episodes, k=len(episodes))) for _ in range(resamples))
    return {"first": first, "second": second, "metric": "expected_corruption_per_episode",
            "mean_difference": difference(episodes),
            "ci95": [values[int(0.025 * resamples)], values[min(resamples - 1, int(0.975 * resamples))]],
            "independent_episode_count": len(episodes), "bootstrap_resamples": resamples,
            "direction": "first policy minus second policy",
            "selection_recomputed_in_each_resample": True}


def dependency_experiment(seed, episodes, resamples):
    conditions = {}
    offset = 0
    for coupling in ("independent", "positive_shared_noise", "maximally_disjoint_failures"):
        for shared in (False, True):
            offset += 1
            name = f"{coupling}:shared_identity={shared}"
            generated = _dependency_episodes(seed + offset, episodes, coupling, shared)
            matched = {}
            episode_only = {}
            for coverage in (0.25, 0.5, 0.75, 1.0):
                rows = {policy: _risk_rows(generated, _risk_selection(generated, policy, coverage))
                        for policy in ("single", "product", "union")}
                matched[str(coverage)] = {"table": _risk_table(rows),
                    "paired_comparisons": [_risk_comparison(generated, "union", comparator, coverage,
                        seed + offset * 100 + int(coverage * 100) + j, resamples)
                        for j, comparator in enumerate(("single", "product"))]}
                episode_only[str(coverage)] = _risk_table({
                    policy: _risk_rows(generated, _risk_selection(generated, policy, coverage, False))
                    for policy in ("single", "product", "union")})
            threshold = {}
            for alpha in (0.05, 0.1, 0.2):
                rows = {policy: _risk_rows(generated, {index for index, item in enumerate(generated)
                        if item["estimates"][policy] <= alpha}) for policy in ("single", "product", "union")}
                threshold[str(alpha)] = _risk_table(rows)
            conditions[name] = {"split": _split_manifest(f"risk-{name}-evaluation", episodes, seed + offset),
                "mean_unique_dependencies": mean(item["unique_dependencies"] for item in generated),
                "risk_underestimate_fraction": {policy: mean(float(item["true_risk"] > item["estimates"][policy] + 1e-12)
                    for item in generated) for policy in ("single", "product", "union")},
                "matched_coverage": matched, "episode_only_coverage": episode_only,
                "fixed_risk_thresholds": threshold}
    return {"experiment": "E8-dependencies", "execution_mode": "synthetic",
            "primary_metric": "expected corruption per offered episode at matched episode coverage; lower is better",
            "development": "No fitted parameters; coverage quotas and thresholds fixed before evaluation.",
            "selection": "Top-k risk estimates within each mutation-count stratum of the offered evaluation batch; largest-remainder quotas match both episode and mutation counts exactly. Selection uses no realized errors or true joint risks.",
            "generator": {"mutations_per_episode": [2, 6], "identity_error_range": [0.005, 0.18],
                          "support_error_range": [0.003, 0.09], "known_marginal_probabilities": True},
            "conditions": conditions,
            "limitations": ["Exact conditional prerequisite probabilities are available by construction; neural confidence does not provide these bounds.",
                            "Primary comparisons match accepted episodes and mutation counts. Secondary episode-only coverage tables expose the effect of preferring smaller transactions.",
                            "No accepted corruption contributes zero loss; conditional risk given a commit is reported separately.",
                            "Intervals resample paired offered episodes and repeat all batch selections and matched quotas; they are descriptive, not risk certificates.",
                            "Union bounds can be very conservative for positively correlated failures and can sharply reduce threshold coverage.",
                            "At full coverage all methods have exactly the same error outcomes."]}


def _routing_episodes(seed, count, condition, shifted=False):
    rng = random.Random(seed)
    result = []
    for episode in range(count):
        observations = []
        for index in range(20):
            confidence = rng.choice((0.55, 0.7, 0.85, 0.95))
            kind = rng.choice(("resolvable", "ambiguous"))
            impact = rng.choice((1.0, 5.0, 20.0, 100.0))
            if condition == "uniform_specialist":
                query_accuracy = 0.9
            elif shifted:
                query_accuracy = 0.55 if kind == "resolvable" else 0.97
            else:
                query_accuracy = 0.97 if kind == "resolvable" else 0.55
            shared_noise = rng.random()
            baseline_correct = shared_noise < confidence
            # Forty percent of queries share an error driver with the base model.
            query_noise = shared_noise if rng.random() < 0.4 else rng.random()
            queried_correct = query_noise < query_accuracy
            observations.append(DevelopmentOutcome(QueryContext(confidence, kind, impact, 1.0),
                                                   baseline_correct, queried_correct))
        result.append(observations)
    return result


def routing_experiment(seed, episodes, resamples):
    conditions = {}
    for offset, condition in enumerate(("heterogeneous_specialist", "uniform_specialist", "distribution_shift")):
        dev_seed, eval_seed = seed + offset * 100, seed + offset * 100 + 1
        development = _routing_episodes(dev_seed, episodes, condition)
        evaluation = _routing_episodes(eval_seed, episodes, condition, shifted=condition == "distribution_shift")
        router = ValueOfInformationRouter().fit([item for episode in development for item in episode])
        budgets = {}
        for budget in (0, 1, 2, 5, 10, 20):
            rows = {policy: [] for policy in ("random", "confidence", "impact", "voi")}
            for episode_id, episode in enumerate(evaluation):
                contexts = [item.context for item in episode]
                for policy in rows:
                    queried = select_queries(contexts, budget, policy, seed=eval_seed + episode_id * 37, router=router)
                    errors = [not (item.queried_correct if index in queried else item.baseline_correct)
                              for index, item in enumerate(episode)]
                    weighted_error = sum(context.impact * error for context, error in zip(contexts, errors)) / len(episode)
                    rows[policy].append({"accuracy": 1 - mean(errors), "any_episode_error": float(any(errors)),
                        "weighted_error_per_decision": weighted_error, "decision_coverage": 1.0,
                        "query_count_per_episode": len(queried), "query_cost_per_decision": len(queried) / len(episode),
                        "weighted_error_plus_query_cost": weighted_error + len(queried) / len(episode)})
            budgets[str(budget)] = {"query_budget_per_20_decisions": budget, "table": _table(rows),
                "paired_comparisons": [_compare(rows, "voi", comparator, "weighted_error_per_decision",
                    seed + offset * 1000 + budget * 10 + j, resamples)
                    for j, comparator in enumerate(("random", "confidence", "impact"))]}
        conditions[condition] = {"development": _split_manifest(f"routing-{condition}-development", episodes, dev_seed),
            "evaluation": _split_manifest(f"routing-{condition}-evaluation", episodes, eval_seed),
            "development_cost": {"simulated_base_predictions": episodes * 20,
                                 "simulated_queries": episodes * 20,
                                 "simulated_query_cost_units": episodes * 20,
                                 "actual_api_calls": 0,
                                 "applies_to": "VOI fitting; not included in matched evaluation-query budgets"},
            "fitted_policy": router.manifest(), "budgets": budgets}
    return {"experiment": "E8-routing", "execution_mode": "synthetic",
            "primary_metric": "impact-weighted errors per offered decision at identical query counts and full coverage; lower is better",
            "generator": {"decisions_per_episode": 20, "baseline_correctness": [0.55, 0.7, 0.85, 0.95],
                          "impact_costs_available_at_runtime": [1, 5, 20, 100], "query_cost": 1,
                          "heterogeneous_query_accuracy": {"resolvable": 0.97, "ambiguous": 0.55},
                          "uniform_query_accuracy": 0.9, "shared_error_driver_fraction": 0.4},
            "runtime_inputs": ["baseline confidence", "source kind", "known action impact", "query cost"],
            "conditions": conditions,
            "limitations": ["Synthetic correctness flags are available only to development fitting and the evaluator, never to runtime routing.",
                            "The budget is spent even when estimated query value is negative so cost is exactly matched.",
                            "All decisions are retained, so improved scores cannot be explained by lower coverage.",
                            "No gold-outcome oracle baseline is used. The impact baseline assumes correction opportunity, not guaranteed correction.",
                            "VOI also requires offline development queries, disclosed per condition; matched evaluation cost is not a claim of matched lifetime cost.",
                            "Distribution shift reverses the source-kind/query-quality relation only at evaluation, exposing failure of development estimates.",
                            "Actual neural inference latency and biomedical utility are not measured here."]}


def render_markdown(result):
    evidence = result["evidence"]
    lines = ["# Controlled synthetic research results", "", "These are reproducible mechanism experiments, not real-model or biomedical results.", "",
             "Run: `python -m pgc.research.advanced_experiments`.", "",
             "## E5: source dependence", "", "| Policy | Brier (one coordinate) | Log loss | Accuracy |",
             "|---|---:|---:|---:|"]
    for policy, row in evidence["table"].items():
        lines.append(f"| {policy} | {row['brier_one_coordinate']:.4f} | {row['log_loss']:.4f} | {row['accuracy']:.3f} |")
    lines.extend(["", "Exact-copy invariance, independent corroboration, and contradiction sensitivity are recorded in JSON. Known source grouping is an assumption; incorrectly collapsing origins loses information.", "",
                  "## E7: exact small-component identity inference", "", "| Condition | Policy | Pairwise F1 | False merge rate | Transitivity violations | Hard-rule violations |", "|---|---|---:|---:|---:|---:|"])
    for condition, data in result["identity"]["conditions"].items():
        for policy, row in data["table"].items():
            lines.append(f"| {condition} | {policy} | {row['pairwise_f1']:.3f} | {row['false_merge_rate']:.3f} | {row['transitivity_violations']:.2f} | {row['hard_constraint_violations']:.2f} |")
    lines.extend(["", "All 15 pair scores are held fixed across policies. Wrong hard rules are deliberately included. Exact inference enumerates 203 partitions per six-entity component; this implementation is bounded to eight entities.", "",
                  "## E8: dependency risk at 50% episode coverage", "", "| Coupling / sharing | Policy | Expected corruption given commit | Accepted mutations / episode |", "|---|---|---:|---:|"])
    for condition, data in result["dependencies"]["conditions"].items():
        for policy, row in data["matched_coverage"]["0.5"]["table"].items():
            lines.append(f"| {condition} | {policy} | {row['expected_corruption_given_commit']:.3f} | {row['accepted_mutations_per_episode']:.2f} |")
    lines.extend(["", "Primary tables match both accepted episode and mutation counts by stratifying on transaction size. The JSON also gives 25%, 75%, and 100% coverage, episode-only matching, fixed risk thresholds, realized corruption, and damaged facts. Union bounds stay valid under the synthetic dependence structures but can reject almost everything at a strict threshold. Products underestimate disjoint failures. Neither uses estimated neural probabilities here.", "",
                  "## E8: routing at five queries per 20 decisions", "", "| Condition | Policy | Weighted error / decision | Accuracy | Coverage |", "|---|---|---:|---:|---:|"])
    for condition, data in result["routing"]["conditions"].items():
        for policy, row in data["budgets"]["5"]["table"].items():
            lines.append(f"| {condition} | {policy} | {row['weighted_error_per_decision']:.3f} | {row['accuracy']:.3f} | {row['decision_coverage']:.1f} |")
    lines.extend(["", "Runtime routing sees confidence, source kind, action impact, and query cost only. VOI uses disjoint development outcomes; its additional development-query cost is disclosed separately in JSON and is excluded from matched evaluation budgets. The distribution-shift arm deliberately reverses specialist competence, so a development-fitted router can be worse than a simple policy. Zero-query and all-query policies coincide across methods.", "",
                  "## Interpretation and uncertainty", "",
                  "The JSON includes paired episode-bootstrap mean differences and 95% percentile intervals for every declared primary comparison. These intervals are exploratory, unadjusted for multiple comparisons, and are not formal risk certificates. Read the full frontier before choosing a policy; this report does not select policies using evaluation outcomes.", "",
                  "Supported only in the stated controls: copies should not create new evidence; negative identity scores can prevent false merges; complete dependency accounting improves on a single-score gate; and routing can exploit development-observed heterogeneous query value. These mechanisms do not establish a real-data improvement. Null full-coverage results, wrong-rule damage, conservative risk coverage, and distribution-shift failures remain in the tables.", ""])
    return "\n".join(lines)


def run(seed=20260917, episodes=300, resamples=1000):
    if episodes < 20:
        raise ValueError("Use at least twenty independent episodes per condition")
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = None
    files = (Path(__file__), Path(__file__).with_name("policies.py"))
    result = {"manifest": {"schema_version": 1, "execution_mode": "synthetic", "seed": seed,
              "evaluation_episodes_per_condition": episodes, "bootstrap_resamples": resamples,
              "python": platform.python_version(), "source_commit": commit,
              "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
              "model": None, "api_calls": 0, "api_fees": 0,
              "protocol": "Frozen generators and policy definitions; no selection or parameter tuning on evaluation outcomes.",
              "uncertainty": "Independent episode bootstrap, 95% percentile intervals; unadjusted exploratory comparisons.",
              "primary_metrics": {"E5": "one-coordinate Brier", "E7": "pairwise F1",
                                  "E8-dependencies": "expected offered-episode corruption at matched coverage",
                                  "E8-routing": "weighted error per decision at matched query count and full coverage"}}}
    for name, function, offset in (("evidence", evidence_experiment, 10000),
                                   ("identity", identity_experiment, 20000),
                                   ("dependencies", dependency_experiment, 30000),
                                   ("routing", routing_experiment, 40000)):
        print(f"Running {name} synthetic controls...", flush=True)
        result[name] = function(seed + offset, episodes, resamples)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260917)
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("results/research/advanced_experiments.json"))
    args = parser.parse_args()
    result = run(args.seed, args.episodes, args.bootstrap_resamples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(render_markdown(result), encoding="utf-8")
    print(f"Saved {args.output} and {args.output.with_suffix('.md')}", flush=True)


if __name__ == "__main__":
    main()
