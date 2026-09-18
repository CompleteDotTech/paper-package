import math
import unittest

from pgc.decision import DecisionRequest
from pgc.decision.local_model import record_text, softmax
from pgc.decision.specialist_er import SpecialistERBackend
from pgc.decision.specialist_nli import SpecialistNLIBackend
from pgc.ir import PrimitiveType


class FixedPairModel:
    metadata = {"test_fixture": True}

    def __init__(self, labels, logits):
        self.id2label, self.logits, self.pairs = labels, logits, []

    def predict(self, pairs, batch_size=8):
        self.pairs.extend(pairs)
        return [self.logits[:] for _ in pairs], [{"input_tokens": 10} for _ in pairs]


def nli_request(**changes):
    params = dict(request_id="nli", primitive=PrimitiveType.CHOICE, question="Generic question ignored",
                  state="Not parsed as premise", task="relation_support",
                  labels=["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"],
                  payload={"claim": "The treatment helped.", "evidence": ["A long preamble. " * 20, "The treatment did not help."]})
    params.update(changes)
    return DecisionRequest(**params)


class LocalBackendTests(unittest.TestCase):
    def test_uses_declared_class_order_and_actual_premise_hypothesis(self):
        model = FixedPairModel({0: "neutral", 1: "contradiction", 2: "entailment"}, [-5, 5, -5])
        backend = SpecialistNLIBackend(model=model)
        request = nli_request()
        response = backend.decide(request)
        self.assertEqual(max(response.distribution, key=response.distribution.get), "REFUTES")
        self.assertEqual(model.pairs, [("\n".join(request.payload["evidence"]), request.payload["claim"])])
        self.assertAlmostEqual(sum(response.distribution.values()), 1.0)
        self.assertEqual(response.execution_mode, "mock")

    def test_no_random_prediction_when_loading_disabled(self):
        backend = SpecialistNLIBackend(load_model=False)
        response = backend.decide(nli_request())
        self.assertEqual(response.distribution, {})
        self.assertEqual(response.execution_mode, "unavailable")
        self.assertIsNotNone(response.error)

    def test_unknown_label_map_is_unavailable(self):
        model = FixedPairModel({0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"}, [1, 2, 3])
        backend = SpecialistNLIBackend(model=model)
        self.assertFalse(backend.available)
        self.assertTrue(backend.decide(nli_request()).error)

    def test_binary_contract_rejected_without_collapsing_unknown(self):
        model = FixedPairModel({0: "neutral", 1: "contradiction", 2: "entailment"}, [1, 2, 3])
        response = SpecialistNLIBackend(model=model).decide(nli_request(labels=["true", "false"]))
        self.assertTrue(response.error)
        self.assertEqual(model.pairs, [])

    def test_missing_claim_fails_before_model_call(self):
        model = FixedPairModel({0: "neutral", 1: "contradiction", 2: "entailment"}, [1, 2, 3])
        response = SpecialistNLIBackend(model=model).decide(nli_request(payload={"evidence": "Text"}))
        self.assertTrue(response.error)
        self.assertEqual(model.pairs, [])

    def test_nonfinite_logits_are_errors_not_probabilities(self):
        model = FixedPairModel({0: "neutral", 1: "contradiction", 2: "entailment"}, [math.nan, 0, 0])
        self.assertTrue(SpecialistNLIBackend(model=model).decide(nli_request()).error)

    def test_er_requires_identity_checkpoint_and_preserves_attributes(self):
        request = DecisionRequest("er", PrimitiveType.NOUL, "Same?", "", task="entity_resolution",
                                  labels=["same", "different"], payload={
                                      "record_1": {"title": "Paper", "author": "A", "label": "same"},
                                      "record_2": {"title": "Paper", "author": "B"}})
        ranker = FixedPairModel({0: "LABEL_0"}, [10.0])
        self.assertFalse(SpecialistERBackend(model=ranker).available)
        model = FixedPairModel({0: "different", 1: "same"}, [4.0, -4.0])
        response = SpecialistERBackend(model=model).decide(request)
        self.assertGreater(response.distribution["different"], .99)
        self.assertIn("author: A", model.pairs[0][0])
        self.assertNotIn("label", model.pairs[0][0])
        self.assertEqual(response.execution_mode, "mock")

    def test_temperature_preserves_argmax_and_rejects_invalid_values(self):
        self.assertEqual(max(range(3), key=lambda i: softmax([-2, 4, 1], 3)[i]), 1)
        for value in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                softmax([0, 1], value)

    def test_serialization_excludes_gold_and_identifiers(self):
        self.assertEqual(record_text({"title": "A", "gold_label": "same", "id": "123"}), "title: A")


if __name__ == "__main__":
    unittest.main()
