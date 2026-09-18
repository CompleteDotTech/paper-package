"""Real SDKs with dummy LM / HTTP transport; zero live model inference."""
import importlib.util
import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from graph_synthesis.dspy_jev_optimizer.core import Cache, Evaluator, JevConfig, optimize
from graph_synthesis.dspy_jev_optimizer.providers import DSPyProposer, TypeSafeBackend
from test_optimizer import CONFIG, rows

AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ("dspy", "typesafe_sdk", "httpx2"))
if os.getenv("REQUIRE_SDK_TESTS") == "1" and not AVAILABLE:
    raise RuntimeError("Required live SDK dependencies are missing")


@unittest.skipUnless(AVAILABLE, "Install requirements-test.txt for real SDK contract tests")
class SDKContracts(unittest.TestCase):
    def make_backend(self, handler, retries=0):
        import httpx2
        from typesafe_sdk import RetryPolicy, TypeSafeClient
        client = TypeSafeClient(api_key="test-key-not-a-secret", model="jev-1.13.0",
                                retry=RetryPolicy(max_retries=retries), transport=httpx2.MockTransport(handler))
        backend = TypeSafeBackend("jev-1.13.0", retries=retries, client=client)
        self.addCleanup(backend.close)
        return backend

    def response(self, request):
        import httpx2
        data = json.loads(request.content)
        selected = data["state"]["fixture_index"] if data["questions"]["target"]["instructions"] == "fixture-perfect" else 0
        labels = list(CONFIG.criteria)
        return httpx2.Response(200, json={"model": "jev-1.13.0", "answers": {"target": {
            "type": "choice", "choice": labels[selected],
            "probabilities": {k: .9 if i == selected else .05 for i, k in enumerate(labels)}, "confidence": .3}},
            "usage": {"input_tokens": 20, "output_tokens": 3}})

    def proposer(self):
        import dspy
        from dspy.utils.dummies import DummyLM
        lm = DummyLM([{"improved_instructions": "fixture-perfect", "improved_criteria": CONFIG.criteria}], adapter=dspy.JSONAdapter())
        return DSPyProposer("dummy", lm=lm)

    def test_typesafe_request_response_contract(self):
        requests = []
        def handler(request):
            requests.append(request)
            return self.response(request)
        backend = self.make_backend(handler)
        result = backend.predict(CONFIG, rows("t")[0].state)
        body = json.loads(requests[0].content)
        self.assertEqual(requests[0].url.path, "/v1/systemone")
        self.assertEqual(body["model"], "jev-1.13.0")
        self.assertEqual(body["questions"]["target"]["criteria"], CONFIG.criteria)
        self.assertEqual(result["usage"]["input_tokens"], 20)
        self.assertEqual(result["choice"], "supports")

    def test_dspy_signature_and_structured_outputs(self):
        proposer = self.proposer()
        result = proposer.propose(CONFIG, [{"state": "training-only", "gold": "supports"}], 1, [])
        candidate = JevConfig.from_dict(result, CONFIG)
        self.assertEqual(candidate.instructions, "fixture-perfect")
        messages = json.dumps(proposer.lm.history[-1]["messages"])
        self.assertIn("training-only", messages)

    def test_sdk_rate_limit_retry(self):
        import httpx2
        calls = []
        def handler(request):
            calls.append(request)
            if len(calls) == 1:
                return httpx2.Response(429, headers={"Retry-After": "0"}, json={"error": "rate limited"})
            return self.response(request)
        result = self.make_backend(handler, retries=1).predict(CONFIG, rows("t")[0].state)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["model"], "jev-1.13.0")

    def test_full_dspy_to_typesafe_loop_with_real_sdks(self):
        backend, proposer = self.make_backend(self.response), self.proposer()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = Cache(root/"cache.sqlite3")
            try:
                result = optimize(CONFIG, rows("train"), rows("val"), proposer,
                                  Evaluator(backend, cache, root/"run", 100), root/"run", iterations=1)
                self.assertEqual(result["champion"]["instructions"], "fixture-perfect")
                self.assertEqual(result["champion_validation"]["accuracy"], 1)
            finally:
                cache.close()
