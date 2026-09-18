"""Jev experiment isolation, payload provenance, and failure-accounting checks.

Only prepared local data and mocked transports are used; no credentials or API
access are needed. Prepared-data tests skip when the optional data cache is absent.
"""

from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from pgc.decision.jev_real import JevAPIError, JevRealBackend
from pgc.experiments import run_jev_research as research


def small_plan():
    row = {"id": "example", "group": "group", "claim": "A increases B.",
           "evidence": ["A increases B in the supplied experiment."],
           "gold_label": "SUPPORTS"}
    demos = [{**row, "id": "demo-" + str(index), "group": "demo-group-" + str(index)}
             for index in range(6)]
    return {"model": research.MODEL, "seed": research.SEED,
            "tasks": {"relation_support": {"demonstrations": demos, "development": [row]}},
            "question_specs": {"relation_support": {
                arm: research.questions("relation_support", arm)
                for arm in research.ARMS["relation_support"]}}}


class SelectionTests(unittest.TestCase):
    def test_frozen_seed_and_prepared_training_isolation(self):
        self.assertEqual(research.SEED, 20260917)
        for task, filename, expected in (
            ("relation_support", "scifact-prepared.json", {"SUPPORTS": 2, "REFUTES": 2, "NOT_ENOUGH_INFO": 2}),
            ("entity_resolution", "entity_resolution-prepared.json", {"same": 3, "different": 3}),
        ):
            with self.subTest(task=task):
                path = research.ROOT / ".cache/research-data" / filename
                if not path.exists():
                    self.skipTest("Optional prepared research data is not present")
                before = path.read_bytes()
                splits = json.loads(before)
                demos, development = research.development_selection(task, splits["train"])
                self.assertEqual(Counter(row["gold_label"] for row in demos), expected)
                self.assertEqual(len(development), 60)
                self.assertEqual(len({row["id"] for row in demos + development}), 66)
                train_ids = {row["id"] for row in splits["train"]}
                seen = set()
                for row in demos + development:
                    self.assertIn(row["id"], train_ids)
                    groups = research.identities(task, row)
                    self.assertFalse(seen & groups, "Demonstration/development identities overlap")
                    seen.update(groups)
                for split in ("calibration", "evaluation"):
                    held_out = set().union(*(research.identities(task, row) for row in splits[split]))
                    self.assertFalse(seen & held_out)
                again = research.development_selection(task, list(reversed(splits["train"])))
                self.assertEqual((demos, development), again)
                self.assertEqual(path.read_bytes(), before)

    def test_fixture_inputs_keep_context_and_exclude_gold(self):
        rows = research.fixture_rows()
        self.assertEqual(len(rows["relation_support"]), 50)
        self.assertEqual(len(rows["entity_resolution"]), 100)
        self.assertEqual(Counter(row["gold_label"] for row in rows["entity_resolution"])["uncertain"], 12)
        for task, examples in rows.items():
            for row in examples:
                state = research.input_state(task, row)
                self.assertNotIn("gold_label", state)
                self.assertNotIn("id", state)
                if task == "relation_support":
                    self.assertEqual(state, {"claim": row["claim"], "evidence": row["evidence"]})
                else:
                    self.assertEqual(state["record_1"], row["record_1"])
                    self.assertEqual(state["record_2"], row["record_2"])
                    if row.get("context"):
                        self.assertEqual(state["context"], row["context"])


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.plan = small_plan()
        research.write_json(self.directory / "plan.json", self.plan)
        manifest = {"plan_sha256": hashlib.sha256((self.directory / "plan.json").read_bytes()).hexdigest(),
                    "selection": {}, "stages": [], "source_sha256": {},
                    "limits": {"max_http_attempts": 4000, "max_input_tokens": 20_000_000, "concurrency": 4}}
        research.write_json(self.directory / "manifest.json", manifest)
        self.prepared = patch.object(research, "prepare", return_value=self.plan)
        self.prepared.start()
        self.addCleanup(self.prepared.stop)
        self.environment = patch.dict(os.environ, {"TYPESAFE_API_KEY": "test-only-never-a-real-key"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def runner(self, live=False):
        return research.Runner(self.directory, live=live)

    def job(self, runner, arms=("baseline_choice",), repeat=0):
        return next(runner.jobs("relation_support", "evaluation",
                               self.plan["tasks"]["relation_support"]["development"], arms, repeat=repeat))

    @staticmethod
    def success(job):
        answers = {key: {"type": "choice", "probabilities": {"SUPPORTS": .6, "REFUTES": .3, "NOT_ENOUGH_INFO": .1},
                         "confidence": .6} for key in job["payload"]["questions"]}
        return {"response": {"answers": answers}, "metadata": {"attempts": 1},
                "tokens_used": {"input": 10, "output": 0}, "execution_mode": "mock", "latency_ms": 1.0}

    def test_fewshot_context_is_separate_and_repeat_bypasses_cache(self):
        runner = self.runner()
        row = self.plan["tasks"]["relation_support"]["development"][0]
        jobs = list(runner.jobs("relation_support", "development", [row], research.ARMS["relation_support"]))
        self.assertEqual(len(jobs), 2)
        ordinary, fewshot = jobs
        self.assertNotIn("labeled_examples", ordinary["payload"]["state"])
        self.assertNotIn("fewshot_contract", ordinary["arms"])
        self.assertEqual(fewshot["arms"], ["fewshot_contract"])
        self.assertEqual(fewshot["payload"]["state"]["input"], ordinary["payload"]["state"])
        self.assertEqual(len(fewshot["payload"]["state"]["labeled_examples"]), 6)
        first, repeated = self.job(runner), self.job(runner, repeat=1)
        self.assertEqual(first["payload"], repeated["payload"])
        self.assertNotEqual(first["cache_key"], repeated["cache_key"])

    def test_exact_cache_replay_and_mismatched_payload_rejection(self):
        runner = self.runner(live=True)
        job = self.job(runner)
        backend = Mock()
        backend.send_payload.return_value = self.success(job)
        with patch("pgc.decision.jev_real.JevRealBackend", return_value=backend):
            fresh = runner.invoke(job)
        offline = self.runner()
        with patch("pgc.decision.jev_real.JevRealBackend", side_effect=AssertionError("Offline replay contacted transport")):
            self.assertEqual(offline.invoke(job), fresh)
            tampered = deepcopy(job)
            tampered["payload"]["state"]["claim"] = "A decreases B."
            with self.assertRaises((ValueError, RuntimeError)):
                offline.invoke(tampered)
            with self.assertRaises(RuntimeError):
                offline.invoke(self.job(offline, repeat=1))

    def test_retry_failure_is_persisted_with_all_attempts(self):
        runner = self.runner(live=True)
        job = self.job(runner)
        backend = Mock()
        backend.send_payload.side_effect = JevAPIError("Service exhausted retries", status_code=503,
            tokens_used={"input": 7, "output": 0}, metadata={"attempts": 3, "requested_model": research.MODEL})
        with patch("pgc.decision.jev_real.JevRealBackend", return_value=backend):
            call = runner.invoke(job)
        self.assertEqual(call["metadata"]["attempts"], 3)
        self.assertEqual(runner.used_attempts, 3)
        self.assertEqual(call["tokens_used"]["input"], 7)
        self.assertEqual(call["unknown_usage_attempts"], 2)
        self.assertGreater(runner.used_tokens, 7)
        charged = runner.used_tokens
        self.assertEqual(research.load_jsonl(self.directory / "calls.jsonl"), [call])
        resumed = self.runner()
        self.assertEqual(resumed.used_attempts, 3)
        self.assertEqual(resumed.used_tokens, charged)
        self.assertEqual(resumed.invoke(job), call)

    def test_frozen_plan_and_source_changes_are_rejected(self):
        manifest_path = self.directory / "manifest.json"
        manifest = research.read_json(manifest_path)
        manifest["source_sha256"] = {"pgc/experiments/run_jev_research.py": "0" * 64}
        research.write_json(manifest_path, manifest)
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.runner()
        manifest["source_sha256"] = {}
        research.write_json(manifest_path, manifest)
        changed = deepcopy(self.plan)
        changed["seed"] += 1
        research.write_json(self.directory / "plan.json", changed)
        with self.assertRaisesRegex(ValueError, "plan was altered"):
            self.runner()

    def test_cached_replay_rejects_tampered_prediction(self):
        runner = self.runner(live=True)
        job = self.job(runner)
        backend = Mock()
        backend.send_payload.return_value = self.success(job)
        with patch("pgc.decision.jev_real.JevRealBackend", return_value=backend):
            original, = runner.execute_job(job)
        changed = deepcopy(original)
        changed["distribution"] = {"SUPPORTS": .1, "REFUTES": .8, "NOT_ENOUGH_INFO": .1}
        prediction_path = self.directory / "predictions.jsonl"
        prediction_path.write_text(json.dumps(changed) + "\n", encoding="utf-8")
        offline = self.runner()
        with patch("pgc.decision.jev_real.JevRealBackend", side_effect=AssertionError("Replay contacted transport")):
            with self.assertRaisesRegex(ValueError, "Stored prediction differs"):
                offline.execute_job(job)
        self.assertEqual(research.load_jsonl(prediction_path), [changed],
                         "Replay must flag tampering rather than silently rewriting evidence")

    def test_constructor_enforces_four_worker_limit(self):
        for workers in (0, 5, -1, True, 1.5):
            with self.subTest(workers=workers):
                with self.assertRaisesRegex(ValueError, "workers must be between 1 and 4"):
                    research.Runner(self.directory, workers=workers)

    def test_unknown_usage_failure_survives_resume_without_secret(self):
        runner = self.runner(live=True)
        job = self.job(runner)
        secret = "test-only-never-a-real-key"
        def broken_transport(payload):
            raise RuntimeError("A simulated failure echoes " + secret)
        backend = JevRealBackend(api_key=secret, transport=broken_transport, max_retries=0)
        with patch("pgc.decision.jev_real.JevRealBackend", return_value=backend):
            call = runner.invoke(job)
        self.assertIsNone(call["tokens_used"])
        self.assertTrue(call["error"])
        evidence = (self.directory / "calls.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(secret, evidence)
        self.assertIn("REDACTED", evidence)
        resumed = self.runner()
        self.assertEqual(resumed.invoke(job), call)
        self.assertGreaterEqual(resumed.used_attempts, 1)
        self.assertTrue(resumed.abort or resumed.used_tokens > 0,
                        "Unknown billed usage must stop live work or retain a conservative reservation")

    def test_budget_blocks_transport_before_spending(self):
        for attempts, tokens in ((3998, 0), (0, 19_999_999)):
            with self.subTest(attempts=attempts, tokens=tokens):
                runner = self.runner(live=True)
                runner.used_attempts, runner.used_tokens = attempts, tokens
                with patch("pgc.decision.jev_real.JevRealBackend", side_effect=AssertionError("Budget crossed into transport")):
                    with self.assertRaisesRegex(RuntimeError, "budget"):
                        runner.invoke(self.job(runner))
                self.assertFalse((self.directory / "calls.jsonl").exists())

    def test_conditional_noul_chain_preserves_all_three_coordinates(self):
        runner = self.runner()
        job = self.job(runner, arms=("conditional_nouls",))
        call = {"call_id": "chain", "error": None, "execution_mode": "mock", "response": {"answers": {
            "conditional_nouls__support": {"type": "noul", "noul": .2},
            "conditional_nouls__refute_given_not_support": {"type": "noul", "noul": .75},
        }}}
        with patch.object(runner, "invoke", return_value=call):
            record, = runner.execute_job(job)
        self.assertAlmostEqual(record["distribution"]["SUPPORTS"], .2)
        self.assertAlmostEqual(record["distribution"]["REFUTES"], .6)
        self.assertAlmostEqual(record["distribution"]["NOT_ENOUGH_INFO"], .2)
        self.assertAlmostEqual(sum(record["distribution"].values()), 1.0)


class ArtifactVerificationTests(unittest.TestCase):
    def test_verifier_rejects_invalid_vector_without_normalizing_it(self):
        from pgc.experiments.verify_jev_artifacts import response_valid
        call = {"payload": {"questions": {"q": {"type": "choice", "criteria": {"same": "", "different": ""}}}},
                "response": {"model": research.MODEL, "answers": {"q": {"type": "choice", "choice": "same",
                    "confidence": .7, "probabilities": {"same": .7, "different": .29}}}}}
        original = deepcopy(call)
        with self.assertRaisesRegex(ValueError, "Non-normalized"):
            response_valid(call)
        self.assertEqual(call, original)

    def test_incomplete_run_never_writes_success_report(self):
        from pgc.experiments.verify_jev_artifacts import verify
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            research.write_json(path / "manifest.json", {"stages": []})
            research.write_json(path / "plan.json", {})
            with self.assertRaisesRegex(ValueError, "incomplete"):
                verify(path)
            self.assertFalse((path / "verification.json").exists())


if __name__ == "__main__":
    unittest.main()
