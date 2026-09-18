"""Validate a curated JSONL corpus and produce a deterministic, offline plan.

This module does not retrieve papers, infer scientific identity, call a model,
annotate evidence, score graphs, authorize spending, or preregister a study.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SPLITS = ("development", "calibration", "test")
FIELDS = {"paper_id", "work_id", "split_group", "domain", "year", "source",
          "license", "rights_reviewed", "full_text", "text_sha256",
          "estimated_candidates"}
CONFIG_FIELDS = {"schema_version", "status", "seed", "domains", "stages",
                 "split_percent", "arms", "repeats", "max_attempts",
                 "max_decisions", "max_estimated_usd", "usd_per_decision",
                 "fixed_overhead_usd", "publication_year_max"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def money(value: Any, name: str, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{name} must be a finite nonnegative amount")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid {name}") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{name} must be a finite nonnegative amount")
    return amount


def names(value: Any, name: str) -> list[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(x, str) or not x.strip() or x != x.strip()
                   for x in value)
            or len(set(value)) != len(value)):
        raise ValueError(f"{name} must contain unique, nonempty names")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict) or set(config) != CONFIG_FIELDS:
        raise ValueError("protocol fields must match the example exactly")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    if config["status"] != "proposed_not_preregistered":
        raise ValueError("this planner only produces proposed plans")
    integer(config["seed"], "seed")
    names(config["domains"], "domains")
    names(config["arms"], "arms")
    stages = config["stages"]
    if not isinstance(stages, list) or not stages:
        raise ValueError("stages must be a nonempty increasing list")
    for stage in stages:
        integer(stage, "stage", 1)
    if stages != sorted(set(stages)):
        raise ValueError("stages must be unique and increasing")
    percentages = config["split_percent"]
    if not isinstance(percentages, dict) or set(percentages) != set(SPLITS):
        raise ValueError("split_percent must name development, calibration, test")
    for key, value in percentages.items():
        integer(value, key, 1)
    if sum(percentages.values()) != 100:
        raise ValueError("split percentages must sum to 100")
    for key in ("repeats", "max_attempts", "max_decisions"):
        integer(config[key], key, 1)
    integer(config["publication_year_max"], "publication_year_max", 1900)
    money(config["max_estimated_usd"], "max_estimated_usd")
    money(config["usd_per_decision"], "usd_per_decision", optional=True)
    money(config["fixed_overhead_usd"], "fixed_overhead_usd", optional=True)


def validate_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("corpus must contain at least one paper")
    seen = {key: set() for key in ("paper_id", "work_id", "text_sha256")}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError(f"row {index}: missing/unknown fields; no labels allowed")
        for key in ("paper_id", "work_id", "split_group", "domain", "source", "license"):
            value = row[key]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"row {index}: {key} must be a trimmed nonempty string")
        if row["domain"] not in config["domains"]:
            raise ValueError(f"row {index}: domain is not in the protocol")
        year = integer(row["year"], "year", 1900)
        if year > config["publication_year_max"]:
            raise ValueError(f"row {index}: year exceeds the frozen cutoff")
        if row["rights_reviewed"] is not True or row["full_text"] is not True:
            raise ValueError(f"row {index}: reviewed rights and full text are required")
        sha = row["text_sha256"]
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError(f"row {index}: invalid normalized-text SHA-256")
        integer(row["estimated_candidates"], "estimated_candidates")
        for key in seen:
            value = row[key]
            if value in seen[key]:
                raise ValueError(f"duplicate {key}: {value}; curate aliases before planning")
            seen[key].add(value)
    return sorted(rows, key=lambda row: row["paper_id"])


def assign_split(group: str, config: dict[str, Any]) -> str:
    bucket = int(digest(["split-v1", config["seed"], group]), 16) % 100
    boundary = 0
    for split in SPLITS:
        boundary += config["split_percent"][split]
        if bucket < boundary:
            return split
    raise AssertionError("invalid split configuration")


def build_plan(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    rows = validate_rows(rows, config)
    domains = sorted(config["domains"])
    ranked: dict[str, list[dict[str, Any]]] = {}
    for domain in domains:
        ranked[domain] = sorted(
            (row for row in rows if row["domain"] == domain),
            key=lambda row: (digest(["sample-v1", config["seed"], row["work_id"]]),
                             row["paper_id"]))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["split_group"]].append(row)
    price = money(config["usd_per_decision"], "usd_per_decision", True)
    overhead = money(config["fixed_overhead_usd"], "fixed_overhead_usd", True)
    cap = money(config["max_estimated_usd"], "max_estimated_usd")
    previous: set[str] = set()
    stages = []
    for target in config["stages"]:
        base, extra = divmod(target, len(domains))
        quotas = {domain: base + (i < extra) for i, domain in enumerate(domains)}
        selected_groups = {row["split_group"] for domain in domains
                           for row in ranked[domain][:quotas[domain]]}
        selected = sorted((row for group in selected_groups for row in groups[group]),
                          key=lambda row: row["paper_id"])
        ids = {row["paper_id"] for row in selected}
        assignments = [{"paper_id": row["paper_id"], "work_id": row["work_id"],
                        "split_group": row["split_group"], "domain": row["domain"],
                        "text_sha256": row["text_sha256"],
                        "split": assign_split(row["split_group"], config)}
                       for row in selected]
        shortages = {domain: quotas[domain] - len(ranked[domain]) for domain in domains
                     if len(ranked[domain]) < quotas[domain]}
        candidates = sum(row["estimated_candidates"] for row in selected)
        decisions = candidates * len(config["arms"]) * config["repeats"] * config["max_attempts"]
        estimate = None if price is None or overhead is None else price * decisions + overhead
        split_papers = Counter(row["split"] for row in assignments)
        split_groups = Counter(assign_split(group, config) for group in selected_groups)
        blockers = []
        if shortages:
            blockers.append("insufficient_papers_in_stratum")
        if any(split_papers[split] == 0 for split in SPLITS):
            blockers.append("empty_development_calibration_or_test_split")
        if candidates == 0:
            blockers.append("no_estimated_candidates")
        if decisions > config["max_decisions"]:
            blockers.append("decision_cap_exceeded")
        if estimate is None:
            blockers.append("unpriced_decisions_or_overhead")
        elif estimate > cap:
            blockers.append("estimated_cost_cap_exceeded")
        stages.append({
            "requested_papers": target, "realized_papers": len(selected),
            "additional_papers": len(ids - previous),
            "group_expansion_papers": len(selected) - sum(min(quotas[d], len(ranked[d])) for d in domains),
            "requested_domain_quotas": quotas, "stratum_shortfalls": shortages,
            "realized_domain_counts": dict(sorted(Counter(row["domain"] for row in selected).items())),
            "paper_counts_by_split": {s: split_papers[s] for s in SPLITS},
            "group_counts_by_split": {s: split_groups[s] for s in SPLITS},
            "estimated_candidates": candidates, "estimated_attempted_decisions": decisions,
            "estimated_usd": None if estimate is None else str(estimate),
            "planning_blockers": blockers, "within_planning_caps": not blockers,
            "execution_authorized": False, "assignments": assignments})
        previous = ids
    result = {
        "schema_version": 1, "status": "dry_run_only_no_empirical_results",
        "protocol_sha256": digest(config), "corpus_sha256": digest(rows),
        "planner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "eligible_unique_papers": len(rows), "declared_independence_groups": len(groups),
        "stages": stages,
        "limitations": ["split groups and rights are supplied attestations, not independently verified",
                        "group closure can exceed requested size and alter domain proportions",
                        "costs are user assumptions, not quotes, invoices or measured usage",
                        "plans do not authorize execution or establish preregistration"]}
    result["plan_sha256"] = digest(result)
    return result


def strict_json(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def reject(value: str) -> None:
        raise ValueError(f"nonfinite JSON value: {value}")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=reject)


def write_receipt(path: Path, result: dict[str, Any]) -> None:
    payload = canonical(result) + b"\n"
    # Exclusive creation protects existing receipts; identical replay is a no-op.
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ValueError("refusing to overwrite a different plan receipt")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True, help="curated metadata JSONL, no labels")
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new path outside frozen evidence")
    args = parser.parse_args()
    try:
        config = strict_json(args.protocol.read_text(encoding="utf-8"))
        rows = [strict_json(line) for line in args.corpus.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        result = build_plan(rows, config)
        write_receipt(args.output, result)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"corpus planner: {exc}\n")
    print(json.dumps({"plan_sha256": result["plan_sha256"], "execution_authorized": False,
                      "stages": [{k: s[k] for k in ("requested_papers", "realized_papers",
                                 "estimated_attempted_decisions", "planning_blockers")}
                                 for s in result["stages"]]}, indent=2))


if __name__ == "__main__":
    main()
