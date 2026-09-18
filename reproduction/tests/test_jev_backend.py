"""Jev API contract, transport safety, and accounting tests; never calls a model."""

import hashlib
import io
import json
import math
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from pgc.decision import DecisionRequest
from pgc.decision.jev_real import JevAPIError, JevRealBackend, _NoRedirects
from pgc.ir import PrimitiveType


def choice_request(request_id="decision", **kwargs):
    fields = dict(primitive=PrimitiveType.CHOICE, question="Which label fits?", state="Evidence",
                  labels=["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"])
    fields.update(kwargs)
    return DecisionRequest(request_id, **fields)


def choice_answer():
    return {"type": "choice", "choice": "SUPPORTS", "confidence": .6,
            "probabilities": {"SUPPORTS": .8, "REFUTES": .1, "NOT_ENOUGH_INFO": .1}}


def api_response(answers=None):
    return {"model": "jev-1.13.0", "answers": answers or {"q1": choice_answer()},
            "usage": {"input_tokens": 11, "output_tokens": 5}}


def http_error(status, body="Service error", retry_after=None):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return urllib.error.HTTPError(JevRealBackend.API_ENDPOINT, status, "fixture", headers,
                                  io.BytesIO(body.encode("utf-8")))


class JevBackendTests(unittest.TestCase):
    def setUp(self):
        # Every test fails locally rather than accidentally reaching a service.
        self.network_block = patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Network forbidden"))
        self.network_block.start()
        self.addCleanup(self.network_block.stop)

    def test_constructor_has_no_network_or_token_side_effect(self):
        backend = JevRealBackend(api_key="fake-test-key")
        self.assertTrue(backend.available)
        self.assertEqual(backend.version(), "jev-1.13.0")
        self.assertEqual(backend.call_count, 0)
        self.assertEqual(backend.total_input_tokens, 0)
        self.assertEqual(backend.get_stats()["requests_made"], 0)

    def test_choice_schema_and_probability_field(self):
        transport = Mock(return_value=api_response())
        backend = JevRealBackend(transport=transport)
        response = backend.decide(choice_request())
        self.assertIsNone(response.error)
        question = transport.call_args.args[0]["questions"]["q1"]
        self.assertEqual(set(question), {"type", "instructions", "criteria"})
        self.assertEqual(question["instructions"], "Which label fits?")
        self.assertEqual(set(question["criteria"]), {"SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"})
        self.assertEqual(response.distribution, choice_answer()["probabilities"])
        self.assertEqual(response.confidence, .6)
        self.assertEqual(response.execution_mode, "mock")
        self.assertEqual(response.metadata["returned_model"], backend.version())
        self.assertNotIn("Authorization", json.dumps(transport.call_args.args[0]))

    def test_task_context_is_included_and_explicit_prompt_overrides_work(self):
        transport = Mock(return_value=api_response())
        backend = JevRealBackend(transport=transport)
        request = choice_request(task="relation_support", payload={"claim": "Alice founded Acme", "evidence": "Evidence"})
        backend.decide(request)
        instructions = transport.call_args.args[0]["questions"]["q1"]["instructions"]
        self.assertEqual(instructions["context"], {"claim": "Alice founded Acme"})
        criteria = {"SUPPORTS": "entails", "REFUTES": "contradicts", "NOT_ENOUGH_INFO": "undetermined"}
        request.payload = {"instructions": {"question": "Classify only this evidence"}, "criteria": criteria}
        backend.decide(request)
        question = transport.call_args.args[0]["questions"]["q1"]
        self.assertEqual(question["instructions"], request.payload["instructions"])
        self.assertEqual(question["criteria"], criteria)

    def test_noul_named_mapping_is_independent_of_label_order(self):
        backend = JevRealBackend(transport=lambda _: api_response({"q1": {"type": "noul", "noul": .9}}))
        request = choice_request(primitive=PrimitiveType.NOUL, labels=["different", "same"],
                                 question="Are they the same entity?", task="entity_resolution")
        response = backend.decide(request)
        self.assertIsNone(response.error)
        self.assertEqual(response.distribution["same"], .9)
        self.assertAlmostEqual(response.distribution["different"], .1)
        self.assertIsNone(response.confidence)
        self.assertEqual(response.metadata["positive_label"], "same")

    def test_reordered_options_keep_label_meanings_and_descriptions_align(self):
        backend = JevRealBackend(transport=Mock())
        request = choice_request(options=["REFUTES", "NOT_ENOUGH_INFO", "SUPPORTS"])
        criteria = backend._format_questions(request)["q1"]["criteria"]
        self.assertIn("contradicts", criteria["REFUTES"])
        request.options = ["entails", "contradicts", "undetermined"]
        self.assertEqual(backend._format_questions(request)["q1"]["criteria"]["SUPPORTS"], "entails")

    def test_json_service_error_preserves_reason_without_inventing_usage(self):
        backend = JevRealBackend(transport=lambda _: {"error": "overloaded"})
        response = backend.decide(choice_request())
        self.assertIn("overloaded", response.error)
        self.assertIsNone(response.tokens_used)
        self.assertEqual(response.distribution, {})
        self.assertEqual(response.raw_output, {"error": "overloaded"})

    def test_failed_validation_preserves_provider_response_with_credentials_redacted(self):
        raw = api_response()
        raw["model"] = "wrong-model"
        raw["headers"] = {"Authorization": "Bearer fake-test-key"}
        raw["detail"] = "Echoed fake-test-key"
        backend = JevRealBackend(api_key="fake-test-key", transport=lambda _: raw)
        with self.assertRaises(JevAPIError) as caught:
            backend.send_payload("Evidence", backend._format_questions(choice_request()))
        captured = caught.exception.raw_response
        self.assertEqual(captured["answers"], raw["answers"])
        self.assertEqual(captured["model"], "wrong-model")
        self.assertEqual(captured["headers"], "[REDACTED]")
        self.assertNotIn("fake-test-key", json.dumps(captured))
        self.assertEqual(raw["detail"], "Echoed fake-test-key")

    def test_http_json_error_body_is_preserved_without_auth(self):
        body = json.dumps({"error": "Invalid input", "api_key": "fake-test-key", "field": "criteria"})
        backend = JevRealBackend(api_key="fake-test-key", transport=Mock(side_effect=http_error(422, body)))
        with self.assertRaises(JevAPIError) as caught:
            backend.send_payload("Evidence", backend._format_questions(choice_request()))
        self.assertEqual(caught.exception.raw_response["field"], "criteria")
        self.assertNotIn("fake-test-key", json.dumps(caught.exception.raw_response))

    def test_custom_noul_requires_declared_polarity(self):
        backend = JevRealBackend(transport=lambda _: api_response({"q1": {"type": "noul", "noul": .9}}))
        request = choice_request(primitive=PrimitiveType.NOUL, labels=["accept", "reject"])
        self.assertIn("positive_label", backend.decide(request).error)
        self.assertEqual(backend.call_count, 0)
        request.payload = {"positive_label": "accept", "negative_label": "reject"}
        self.assertEqual(backend.decide(request).distribution["accept"], .9)

    def test_missing_or_invalid_noul_is_error_not_half_probability(self):
        for value in (None, True, -1, 1.1, math.nan, math.inf, ".9"):
            with self.subTest(value=value):
                answer = {"type": "noul"}
                if value is not None:
                    answer["noul"] = value
                backend = JevRealBackend(transport=lambda _: api_response({"q1": answer}))
                response = backend.decide(choice_request(primitive=PrimitiveType.NOUL, labels=["same", "different"]))
                self.assertTrue(response.error)
                self.assertEqual(response.distribution, {})

    def test_score_indices_map_to_explicit_labels_and_expectation_stays_separate(self):
        answer = {"type": "score", "score": 1.3, "confidence": .54,
                  "legend": {"0": "minor", "1": "moderate", "2": "major"},
                  "probabilities": {"0": 0., "1": .7, "2": .3}}
        transport = Mock(return_value=api_response({"q1": answer}))
        backend = JevRealBackend(transport=transport)
        request = choice_request(primitive=PrimitiveType.SCORE, labels=["low", "medium", "high"],
                                 rubric=["minor", "moderate", "major"])
        response = backend.decide(request)
        self.assertIsNone(response.error)
        self.assertEqual(response.distribution, {"low": 0., "medium": .7, "high": .3})
        self.assertEqual(response.metadata["score_expectation"], 1.3)
        self.assertAlmostEqual(response.metadata["score_expectation_from_probabilities"], 1.3)
        self.assertEqual(transport.call_args.args[0]["questions"]["q1"]["criteria"], request.rubric)

    def test_invalid_answer_ids_models_types_and_distributions_fail_closed(self):
        variants = []
        for model in (None, "jev-latest", "jev-1.12.0"):
            response = api_response()
            response["model"] = model
            variants.append(response)
        for answers in ({}, {"different_id": choice_answer()}, {"q1": choice_answer(), "extra": choice_answer()}):
            response = api_response()
            response["answers"] = answers
            variants.append(response)
        for field, value in (("type", "noul"), ("choice", "not-an-option"), ("choice", "REFUTES"),
                             ("choice", {"SUPPORTS": 1.}), ("confidence", math.nan),
                             ("probabilities", {"SUPPORTS": 1.}),
                             ("probabilities", {"SUPPORTS": .9, "REFUTES": .1, "NOT_ENOUGH_INFO": .1}),
                             ("probabilities", {"SUPPORTS": True, "REFUTES": 0, "NOT_ENOUGH_INFO": 0}),
                             ("probabilities", {"SUPPORTS": math.inf, "REFUTES": 0, "NOT_ENOUGH_INFO": 0})):
            response = api_response()
            response["answers"]["q1"][field] = value
            variants.append(response)
        for raw in variants:
            with self.subTest(raw=raw):
                backend = JevRealBackend(transport=lambda _: raw)
                response = backend.decide(choice_request())
                self.assertTrue(response.error)
                self.assertEqual(response.distribution, {})
                self.assertEqual(backend.call_count, 1)
                self.assertEqual(response.tokens_used, {"input": 11, "output": 5})
                self.assertEqual(backend.total_input_tokens, 11)

    def test_raw_payload_keeps_arbitrary_ids_exact_response_and_request_hash(self):
        questions = {"urgent": {"type": "noul", "instructions": "Is it urgent?"},
                     "department": {"type": "choice", "instructions": "Where?", "criteria": {"a": None, "b": "other"}}}
        raw = api_response({"urgent": {"type": "noul", "noul": .4},
                            "department": {"type": "choice", "choice": "b", "confidence": .2,
                                           "probabilities": {"a": .4, "b": .6}}})
        transport = Mock(return_value=raw)
        backend = JevRealBackend(transport=transport)
        result = backend.send_payload({"text": "evidence"}, questions)
        self.assertEqual(result["response"], raw)
        self.assertEqual(result["execution_mode"], "mock")
        canonical = json.dumps(transport.call_args.args[0], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        self.assertEqual(result["metadata"]["request_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(result["metadata"]["attempts"], 1)
        self.assertGreaterEqual(result["latency_ms"], 0)

    def test_batched_usage_retains_remainders_and_counts_once(self):
        raw = api_response({"q1": choice_answer(), "q2": choice_answer(), "q3": choice_answer()})
        backend = JevRealBackend(transport=lambda _: raw)
        responses = backend.batch_decide([choice_request(str(i)) for i in range(3)])
        self.assertEqual([response.request_id for response in responses], ["0", "1", "2"])
        self.assertEqual(sum(response.tokens_used["input"] for response in responses), 11)
        self.assertEqual(sum(response.tokens_used["output"] for response in responses), 5)
        self.assertEqual(backend.total_input_tokens, 11)
        self.assertEqual(backend.total_output_tokens, 5)
        self.assertEqual(backend.call_count, 1)
        self.assertEqual(backend.get_stats()["successful_requests"], 1)

    def test_batch_validation_failure_preserves_usage_once_and_no_success(self):
        backend = JevRealBackend(transport=lambda _: api_response())
        responses = backend.batch_decide([choice_request("a"), choice_request("b")])
        self.assertTrue(all(response.error for response in responses))
        self.assertEqual(sum(response.tokens_used["input"] for response in responses), 11)
        self.assertEqual(backend.total_input_tokens, 11)
        self.assertEqual(backend.success_count, 0)

    def test_different_states_use_distinct_requests(self):
        backend = JevRealBackend(transport=lambda _: api_response())
        responses = backend.batch_decide([choice_request("a", state="A"), choice_request("b", state="B")])
        self.assertEqual(len(responses), 2)
        self.assertEqual(backend.call_count, 2)
        self.assertEqual(backend.total_input_tokens, 22)
        self.assertEqual(backend.batch_decide([]), [])

    def test_retryable_status_backoff_is_bounded_and_usage_is_once(self):
        transport = Mock(side_effect=[http_error(429, retry_after="1000"), http_error(529), api_response()])
        sleep = Mock()
        backend = JevRealBackend(transport=transport, sleep=sleep, max_backoff_seconds=3)
        result = backend.send_payload("Evidence", backend._format_questions(choice_request()))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3, 1.])
        self.assertEqual(result["metadata"]["attempts"], 3)
        attempts = result["metadata"]["attempt_log"]
        self.assertEqual([attempt["status"] for attempt in attempts], [429, 529, "response_received"])
        self.assertEqual([attempt["known_usage"] for attempt in attempts], [None, None, {"input": 11, "output": 5}])
        self.assertTrue(all(attempt["started_at"].endswith("+00:00") for attempt in attempts))
        self.assertEqual(attempts[0]["error_kind"], "HTTPError")
        self.assertEqual(backend.get_stats()["retries"], 2)
        self.assertEqual(backend.get_stats()["requests_made"], 1)
        self.assertEqual(backend.call_count, 3)
        self.assertEqual(backend.total_input_tokens, 11)

    def test_retry_exhaustion_is_an_error(self):
        backend = JevRealBackend(transport=Mock(side_effect=[http_error(503) for _ in range(3)]), sleep=Mock())
        with self.assertRaises(JevAPIError) as caught:
            backend.send_payload("Evidence", backend._format_questions(choice_request()))
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.metadata["attempts"], 3)
        self.assertTrue(all(attempt["known_usage"] is None for attempt in caught.exception.metadata["attempt_log"]))
        self.assertIsNone(caught.exception.tokens_used)
        self.assertEqual(backend.total_input_tokens, 0)

    def test_auth_validation_and_redirect_errors_do_not_retry_or_leak(self):
        for status in (301, 302, 307, 308, 401, 403, 422):
            with self.subTest(status=status):
                transport = Mock(side_effect=http_error(status, "Authorization: Bearer fake-test-key\nBad request"))
                sleep = Mock()
                backend = JevRealBackend(api_key="fake-test-key", transport=transport, sleep=sleep)
                with self.assertRaises(JevAPIError) as caught:
                    backend.send_payload("Evidence", backend._format_questions(choice_request()))
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn("fake-test-key", str(caught.exception))
                self.assertNotIn("Authorization", str(caught.exception))
                self.assertIn("Bad request", str(caught.exception))
                self.assertEqual(transport.call_count, 1)
                sleep.assert_not_called()

    def test_network_error_never_exposes_credential_and_is_not_retried(self):
        transport = Mock(side_effect=urllib.error.URLError("failed fake-test-key"))
        backend = JevRealBackend(api_key="fake-test-key", transport=transport)
        response = backend.decide(choice_request())
        self.assertTrue(response.error)
        self.assertNotIn("fake-test-key", response.error)
        self.assertEqual(transport.call_count, 1)

    def test_missing_credentials_return_explicit_unavailable_without_http(self):
        backend = JevRealBackend(api_key="")
        response = backend.decide(choice_request())
        self.assertIn("TYPESAFE_API_KEY", response.error)
        self.assertEqual(response.execution_mode, "unavailable")
        self.assertEqual(response.distribution, {})
        self.assertEqual(backend.call_count, 0)

    def test_http_path_uses_fixed_https_and_marks_success_real(self):
        backend = JevRealBackend(api_key="fake-test-key")
        opened = Mock()
        opened.__enter__ = Mock(return_value=opened)
        opened.__exit__ = Mock(return_value=False)
        opened.read.return_value = json.dumps(api_response()).encode()
        with patch.object(backend._opener, "open", return_value=opened) as send:
            response = backend.decide(choice_request())
        self.assertIsNone(response.error)
        self.assertEqual(response.execution_mode, "real")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-test-key")
        self.assertNotIn("fake-test-key", json.dumps(response.metadata))

    def test_modified_endpoint_is_rejected_and_redirect_handler_refuses(self):
        backend = JevRealBackend(api_key="fake-test-key")
        backend.API_ENDPOINT = "https://attacker.invalid/v1/systemone"
        response = backend.decide(choice_request())
        self.assertIn("official HTTPS", response.error)
        request = urllib.request.Request("https://api.typesafe.ai/v1/systemone", headers={"Authorization": "Bearer fake"})
        self.assertIsNone(_NoRedirects().redirect_request(request, None, 302, "redirect", {}, "https://attacker.invalid"))

    def test_usage_requires_nonnegative_integer_counts(self):
        for usage in (None, {}, {"input_tokens": True, "output_tokens": 1},
                      {"input_tokens": -1, "output_tokens": 1}, {"input_tokens": 1.5, "output_tokens": 1}):
            raw = api_response()
            raw["usage"] = usage
            backend = JevRealBackend(transport=lambda _: raw)
            response = backend.decide(choice_request())
            self.assertTrue(response.error)
            self.assertIsNone(response.tokens_used)
            self.assertEqual(backend.total_input_tokens, 0)

    def test_request_contract_errors_happen_before_transport(self):
        transport = Mock()
        backend = JevRealBackend(transport=transport)
        for questions in ({}, {"q": {"type": "choice", "prompt": "Wrong field", "options": ["a"]}},
                          {"q": {"type": "score", "instructions": "Rate", "criteria": ["only one"]}}):
            with self.assertRaises(JevAPIError):
                backend.send_payload("state", questions)
        self.assertTrue(backend.decide(choice_request(labels=[])).error)
        transport.assert_not_called()

    def test_relation_benchmark_wrapper_uses_canonical_choice_and_mock_mode(self):
        from pgc.experiments.scifact_benchmark import SciFactBenchmark, SciFactExample

        transport = Mock(return_value=api_response())
        backend = JevRealBackend(transport=transport)
        example = SciFactExample("wrapper-relation", "Alice founded Acme", ["Alice founded Acme in 2001."], "SUPPORTS")
        row = SciFactBenchmark([example]).run([backend]).results[0]

        self.assertTrue(row.service_success)
        self.assertTrue(row.correct)
        self.assertEqual(row.execution_mode, "mock")
        self.assertEqual(row.decision_primitive, "choice")
        self.assertEqual(row.labels, ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"])
        self.assertEqual(row.distribution, choice_answer()["probabilities"])
        payload = transport.call_args.args[0]
        self.assertEqual(payload["questions"]["q1"]["type"], "choice")
        self.assertEqual(json.loads(payload["state"]), {"claim": example.claim_text, "evidence": example.evidence_passages})
        self.assertNotIn("gold_label", json.dumps(payload))

    def test_entity_resolution_wrapper_uses_canonical_noul_and_mock_mode(self):
        from pgc.experiments.benchmark_entity_resolution_100 import EntityResolutionBenchmark
        from pgc.experiments.entity_resolution_100 import ERExample

        transport = Mock(return_value=api_response({"q1": {"type": "noul", "noul": .9}}))
        backend = JevRealBackend(transport=transport)
        example = ERExample("wrapper-er", "Alice Smith", "A. Smith", "same", context="Both names identify the Acme founder.")
        row = EntityResolutionBenchmark([example]).run([backend])["results"][0]

        self.assertTrue(row.service_success)
        self.assertTrue(row.correct)
        self.assertEqual(row.execution_mode, "mock")
        self.assertEqual(row.decision_primitive, "noul")
        self.assertEqual(row.labels, ["same", "different"])
        self.assertEqual(row.distribution["same"], .9)
        self.assertAlmostEqual(row.distribution["different"], .1)
        self.assertIsNone(row.reported_confidence)
        payload = transport.call_args.args[0]
        self.assertEqual(payload["questions"]["q1"]["type"], "noul")
        self.assertEqual(payload["questions"]["q1"]["criteria"], {"true": "same", "false": "different"})
        self.assertEqual(json.loads(payload["state"])["context"], example.context)
        self.assertNotIn("gold_label", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
