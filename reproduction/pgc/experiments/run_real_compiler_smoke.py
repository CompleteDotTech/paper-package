r"""Two manual NLI examples through the real adapter and transactional compiler.

Integration smoke only: examples are constructed for obvious entailment and
contradiction, not held-out data. Uses a pinned pretrained checkpoint, no training.
Run: .venv\Scripts\python.exe -B -m pgc.experiments.run_real_compiler_smoke
"""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
from time import perf_counter

from pgc.compiler import GraphCompiler, InMemoryGraphStore
from pgc.decision.specialist_nli import SpecialistNLIBackend
from pgc.ir import CandidateGraphIR, Constraint, ConstraintSet, EdgeCandidate, Evidence, EvidenceSpan, ObjectKind


MODEL_ID = "cross-encoder/nli-deberta-v3-small"
MODEL_REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"


def run(output=None):
    import torch

    torch.set_num_threads(2)
    if not torch.cuda.is_available():
        raise RuntimeError("This pinned smoke requests CUDA; no device fallback is permitted")
    started = perf_counter()
    backend = SpecialistNLIBackend(MODEL_ID, revision=MODEL_REVISION, device="cuda", batch_size=2)
    load_seconds = perf_counter() - started
    if not backend.available or backend.execution_mode != "real":
        raise RuntimeError("Real NLI checkpoint unavailable: " + str(backend.load_error))

    cases = []
    for case_id, text, expected_class in (
        ("manual_entailment", "Alice lives in Paris.", "SUPPORTS"),
        ("manual_contradiction", "Alice does not live in Paris. She lives in London.", "REFUTES"),
    ):
        ev = Evidence(case_id, case_id, "document", "1", EvidenceSpan(case_id, "1", 0, len(text), text),
                      "manual-integration-fixture", "1", datetime(2026, 9, 17))
        edge = EdgeCandidate("residence", ObjectKind.EDGE, "Alice", "lives in", "Paris", [ev],
                             subject_id="alice", object_id="paris")
        graph = CandidateGraphIR(case_id, "v1", datetime(2026, 9, 17), edges=[edge])
        constraints = ConstraintSet("smoke-schema", "1", {
            "references": Constraint("references", "referential", "Endpoints exist", {"rule": "referential"}),
            "types": Constraint("types", "type", "Person lives in place",
                                {"rule": "domain_range", "predicate": "lives in", "domain": "Person", "range": "Place"}),
        })
        store = InMemoryGraphStore(case_id, nodes={"alice": {"mention": "Alice", "types": ["Person"]},
                                                   "paris": {"mention": "Paris", "types": ["Place"]}})
        compiler = GraphCompiler(case_id, backend, store=store)
        before_calls, before = backend.call_count, store.snapshot()
        tx, ctx = compiler.compile([ev], graph, constraints, idempotency_key=case_id)
        after = store.snapshot()
        decisions = list(ctx.decision_ledger.decisions.values())
        if len(decisions) != 1:
            raise AssertionError({"case": case_id, "errors": ctx.errors})
        decision = decisions[0]
        expected_commit = expected_class == "SUPPORTS"
        passed = (decision.execution_mode == "real" and decision.selected_outcome == expected_class
                  and len(after.edges) == int(expected_commit) and len(after.provenance) == int(expected_commit)
                  and tx.status == ("committed" if expected_commit else "no_op")
                  and (after.version == "v2" if expected_commit else after == before))
        cases.append({
            "id": case_id, "data_provenance": "manually constructed integration fixture",
            "claim": "Alice lives in Paris", "evidence": text, "expected_class": expected_class,
            "selected_class": decision.selected_outcome, "distribution": decision.distribution,
            "execution_mode": decision.execution_mode, "compiler_threshold": compiler.confidence_threshold,
            "transaction_status": tx.status, "graph_version_before": before.version, "graph_version_after": after.version,
            "edges_after": after.edges, "provenance_entries_after": len(after.provenance),
            "atomic_transaction_entries_after": len(after.transactions), "model_calls": backend.call_count - before_calls,
            "rejected_candidates": ctx.rejected_candidates, "errors": ctx.errors,
            "integration_assertions_passed": passed,
        })
    root = Path(__file__).resolve().parents[2]
    source_files = ("pgc/experiments/run_real_compiler_smoke.py", "pgc/decision/specialist_nli.py",
                    "pgc/decision/pair_backend.py", "pgc/decision/local_model.py",
                    "pgc/compiler/orchestrator.py", "pgc/compiler/graph_store.py", "pgc/ir/__init__.py")
    result = {
        "study": "two-case real-adapter/compiler integration smoke; not a held-out benchmark",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID, "revision": MODEL_REVISION,
        "model_metadata": backend._metadata(), "device": "cuda", "device_name": torch.cuda.get_device_name(0),
        "execution_mode": "real", "weights_updated": False, "load_seconds": load_seconds,
        "dependencies": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "safetensors")},
        "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_files},
        "cases": cases, "all_integration_assertions_passed": all(case["integration_assertions_passed"] for case in cases),
        "limitations": ["Manually selected simple inputs; no generalization estimate", "In-memory graph state only",
                        "Model probabilities are not certified semantic truth; no calibration claim"],
    }
    target = Path(output) if output else root / "results" / "research" / "real_compiler_smoke.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["all_integration_assertions_passed"]:
        raise AssertionError("Smoke outcomes differed from expectations; exact predictions saved to " + str(target))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({"execution_mode": result["execution_mode"], "passed": result["all_integration_assertions_passed"],
                      "cases": [{"id": case["id"], "class": case["selected_class"], "distribution": case["distribution"],
                                 "status": case["transaction_status"], "edges": len(case["edges_after"])}
                                for case in result["cases"]]}, indent=2))
