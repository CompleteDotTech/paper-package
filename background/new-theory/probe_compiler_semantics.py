"""Reproduce current compiler staging semantics without model or API calls.

Run: python -B probe_compiler_semantics.py --output compiler_probe_snapshot.json
Only the optional output file is written. Original repository imports disable
bytecode generation, and a deterministic in-process backend supplies responses.
"""

import sys

sys.dont_write_bytecode = True

import argparse
from contextlib import redirect_stdout
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess


THEORY_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_DIRECTORY = THEORY_DIRECTORY.parent / "typed-probabilistic-graph-compiler"
sys.path.insert(0, str(REPOSITORY_DIRECTORY))

from pgc.compiler.orchestrator import GraphCompiler
from pgc.decision import DecisionBackend, DecisionResponse
from pgc.ir import (
    CandidateGraphIR,
    Constraint,
    ConstraintSet,
    EdgeCandidate,
    ObjectKind,
)


class DeterministicFalseBackend(DecisionBackend):
    def __init__(self):
        self.calls = []

    def name(self):
        return "deterministic-false-offline-probe"

    def version(self):
        return "1"

    def decide(self, request):
        self.calls.append(request)
        return DecisionResponse(
            request_id=request.request_id,
            distribution={"true": 0.01, "false": 0.99},
            confidence=0.99,
        )

    def batch_decide(self, requests):
        return [self.decide(request) for request in requests]


def git_value(*arguments):
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPOSITORY_DIRECTORY), *arguments],
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def probe():
    source_paths = [
        "pgc/compiler/orchestrator.py",
        "pgc/ir/__init__.py",
        "pgc/decision/__init__.py",
    ]
    source_hashes = {
        relative: hashlib.sha256((REPOSITORY_DIRECTORY / relative).read_bytes()).hexdigest()
        for relative in source_paths
    }
    status_before = git_value("status", "--porcelain")
    backend = DeterministicFalseBackend()
    compiler = GraphCompiler("offline-semantics-audit", backend)
    candidates = CandidateGraphIR(
        graph_id="offline-semantics-audit",
        version="v1",
        timestamp=datetime(2026, 9, 17),
        edges=[EdgeCandidate("edge1", ObjectKind.EDGE, "S", "relation", "O", [])],
    )
    constraint = Constraint(
        constraint_id="always-false",
        constraint_type="logical",
        description="Unsatisfiable constraint",
        formal_spec="False",
    )
    constraints = ConstraintSet("schema", "v1", {constraint.constraint_id: constraint})
    with redirect_stdout(io.StringIO()):
        transaction, context = compiler.compile([], candidates, constraints, dry_run=True)

    decisions = list(context.decision_ledger.decisions.values())
    mutations = transaction.mutations
    selected_outcomes = [max(decision.distribution, key=decision.distribution.get) for decision in decisions]
    return {
        "probe": "compiler-staging-semantics",
        "scope": "Offline deterministic backend; no graph persistence or semantic model evaluation",
        "manifest": {
            "repository_name": REPOSITORY_DIRECTORY.name,
            "repository_commit": git_value("rev-parse", "HEAD"),
            "repository_status_before": status_before,
            "repository_status_after": git_value("status", "--porcelain"),
            "python_version": sys.version.split()[0],
            "bytecode_writes_disabled": sys.dont_write_bytecode,
            "source_sha256": source_hashes,
        },
        "input": {
            "candidate_edges": 1,
            "candidate_nodes": 0,
            "evidence_items": 0,
            "backend_distribution": {"true": 0.01, "false": 0.99},
            "backend_confidence": 0.99,
            "constraint_formal_spec": "False",
            "dry_run": True,
        },
        "observed": {
            "backend_call_count": len(backend.calls),
            "backend_requests": [
                {"state": request.state, "options": request.options, "primitive": request.primitive.value}
                for request in backend.calls
            ],
            "second_request_state_empty": len(backend.calls) >= 2 and backend.calls[1].state == "",
            "recorded_decision_count": len(decisions),
            "selected_decision_outcomes": selected_outcomes,
            "negative_decision_selected": selected_outcomes == ["false"],
            "constraint_marked_evaluated": constraint.evaluated,
            "constraint_status": constraint.status.value,
            "transaction_mutation_count": len(mutations),
            "mutation_operations": [mutation.operation.value for mutation in mutations],
            "mutation_statuses": [mutation.status.value for mutation in mutations],
            "mutation_committed_at_set": [mutation.committed_at is not None for mutation in mutations],
            "dry_run_transaction_committed_at_set": transaction.committed_at is not None,
            "dry_run_transaction_committed_by": transaction.committed_by,
            "transaction_graph_version_before": transaction.graph_version_before,
            "transaction_graph_version_after_differs": transaction.graph_version_after != transaction.graph_version_before,
            "compiler_graph_version_after": compiler.graph_version,
            "transaction_read_set_size": len(transaction.read_set),
            "transaction_affected_set_size": len(transaction.affected_set),
            "provenance_entry_count": len(compiler.provenance_db),
            "compiler_error_count": len(context.errors),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for the JSON snapshot")
    arguments = parser.parse_args()
    payload = json.dumps(probe(), indent=2, ensure_ascii=True) + "\n"
    if arguments.output is not None:
        arguments.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")


if __name__ == "__main__":
    main()
