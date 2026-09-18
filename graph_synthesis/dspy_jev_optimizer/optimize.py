#!/usr/bin/env python3
"""Optimize Jev questions with DSPy, then audit a frozen winner separately."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

if __package__ in {None, ""}:  # Also supports python path/to/optimize.py.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dspy_jev_optimizer.core import (Cache, Evaluator, Example, JevConfig, evaluate_frozen,
                                        frozen_run, load_data, optimize, read_json)
    from dspy_jev_optimizer.providers import DSPyProposer, TypeSafeBackend
else:
    from .core import (Cache, Evaluator, Example, JevConfig, evaluate_frozen,
                       frozen_run, load_data, optimize, read_json)
    from .providers import DSPyProposer, TypeSafeBackend


class NoProposer:
    identity = {"provider": "none", "model": "none"}

    def propose(self, *args):
        raise RuntimeError("No proposer configured")


class FixtureBackend:
    """Deliberately scripted test double. Never reports a live Jev benchmark."""
    identity = {"provider": "offline-fixture", "model": "fixture-v1"}

    def predict(self, config, state):
        labels = list(config.criteria)
        selected = state["fixture_index"] if config.instructions == "fixture-perfect" else 0
        return {"model": "fixture-v1", "choice": labels[selected],
                "probabilities": {label: .9 if n == selected else .05 for n, label in enumerate(labels)},
                "usage": {"input_tokens": 0, "output_tokens": 0}}


class FixtureProposer:
    identity = {"provider": "offline-scripted-proposal", "model": "none"}

    def propose(self, config, feedback, iteration, history):
        return {**asdict(config), "instructions": "fixture-perfect"}


def demo(output: Path, cache: Cache) -> dict:
    config = JevConfig.from_dict({"task": "Synthetic wiring test, NOT semantic research",
                                 "instructions": "fixture-baseline",
                                 "criteria": {"supports": "Supports", "refutes": "Refutes", "insufficient": "Insufficient"}})
    def rows(split):
        return [Example(f"{split}-{i}", {"fixture_index": i, "split": split}, label)
                for i, label in enumerate(config.criteria)]
    optimize(config, rows("train"), rows("validation"), FixtureProposer(),
             Evaluator(FixtureBackend(), cache, output, 100), output, iterations=2)
    test_path = output / "fixture-test.jsonl"
    test_path.write_text("".join(json.dumps(asdict(row)) + "\n" for row in rows("test")), encoding="utf-8")
    result = evaluate_frozen(output, test_path, Evaluator(FixtureBackend(), cache, output / "final", 100))
    return {"mode": "offline-fixture", "live_model_calls": 0, "research_claim": False, "result": result}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("optimize", help="Search TRAIN/VALIDATION; never accepts a test path")
    search.add_argument("--config", type=Path, required=True)
    search.add_argument("--train", type=Path, required=True)
    search.add_argument("--validation", type=Path, required=True)
    search.add_argument("--output", type=Path, required=True)
    search.add_argument("--jev-model", default="jev-1.13.0")
    search.add_argument("--proposer-model", default=os.getenv("DSPY_PROPOSER_MODEL", ""))
    search.add_argument("--iterations", type=int, default=12)
    search.add_argument("--selection-metric", choices=("accuracy", "macro_f1", "composite"), default="accuracy")
    search.add_argument("--failure-sample", type=int, default=12)
    search.add_argument("--patience", type=int, default=0)
    search.add_argument("--timeout", type=float, default=30)
    search.add_argument("--retries", type=int, default=2)
    audit = commands.add_parser("evaluate", help="Audit baseline and champion after freezing")
    audit.add_argument("--run", type=Path, required=True)
    audit.add_argument("--test", type=Path, required=True)
    offline = commands.add_parser("demo", help="Synthetic offline wiring test, not model evidence")
    offline.add_argument("--output", type=Path, required=True)
    for sub in (search, audit, offline):
        sub.add_argument("--cache", type=Path, default=Path.home()/".cache"/"jev-dspy"/"v1.sqlite3")
    for sub in (search, audit):
        sub.add_argument("--max-jev-calls", type=int, default=10000, help="Logical calls; each has at most retries+1 HTTP attempts")
    args = parser.parse_args(argv)
    cache, backend = None, None
    try:
        if args.command == "optimize":
            config = JevConfig.from_dict(read_json(args.config))
            train, validation = load_data(args.train, config.criteria), load_data(args.validation, config.criteria)
            if args.iterations and not args.proposer_model:
                raise ValueError("Specify --proposer-model or DSPY_PROPOSER_MODEL")
            backend = TypeSafeBackend(args.jev_model, timeout=args.timeout, retries=args.retries)
            proposer = DSPyProposer(args.proposer_model) if args.iterations else NoProposer()
            cache = Cache(args.cache)
            result = optimize(config, train, validation, proposer,
                              Evaluator(backend, cache, args.output, args.max_jev_calls), args.output,
                              iterations=args.iterations, selection_metric=args.selection_metric,
                              failure_sample=args.failure_sample, patience=args.patience)
        elif args.command == "evaluate":
            protocol, _ = frozen_run(args.run)
            identity = protocol["backend"]
            if identity["provider"] != "typesafe-sdk":
                raise ValueError("Use demo for offline fixtures; evaluate is for live frozen runs")
            backend = TypeSafeBackend(identity["model"], timeout=identity["timeout_seconds"], retries=identity["max_retries"])
            cache = Cache(args.cache)
            result = evaluate_frozen(args.run, args.test, Evaluator(backend, cache, args.run/"final", args.max_jev_calls))
        else:
            cache = Cache(args.cache)
            result = demo(args.output, cache)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")
    except Exception as exc:
        # Provider errors can contain request text or credentials: don't print them.
        parser.exit(1, f"Execution failed ({type(exc).__name__}); inspect the local audit records.\n")
    finally:
        if cache is not None:
            cache.close()
        if backend is not None:
            backend.close()


if __name__ == "__main__":
    main()
