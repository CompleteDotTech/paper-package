"""Offline controls for ER training selection, scoring, and calibration."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pgc.decision import DecisionResponse
from pgc.decision.local_model import softmax
from pgc.experiments.run_er_research import (
    MODEL, REVISION, SEED, fit_temperature, inputs, request_for, score_responses,
    training_examples, train_variant,
)
from pgc.experiments.research_data import digest


def pair(identity, left, right, label):
    return {"id": identity, "record_1": {"title": left, "authors": "A", "gold_label": label},
            "record_2": {"title": right, "authors": "B"}, "gold_label": label,
            "identity_groups": [f"left:{identity}", f"right:{identity}"]}


def response(row, logits, labels=("different", "same")):
    probabilities = softmax(logits)
    return DecisionResponse(row["id"], dict(zip(labels, probabilities)), confidence=max(probabilities),
                            execution_mode="mock", latency_ms=1,
                            raw_output={"logits": logits, "label_mapping": dict(enumerate(labels))})


class ERResearchTests(unittest.TestCase):
    def test_json_roundtrip_checkpoint_reuse_is_compatible_and_checks_training_hash(self):
        rows = [pair("train", "A", "B", "same")]
        args = SimpleNamespace(epochs=2, batch_size=8, max_length=256, reuse_checkpoints=True)
        config = {"name": "er-title-only", "base_model": MODEL, "base_revision": REVISION,
                  "seed": SEED, "epochs": 2, "batch_size": 8, "max_length": 256,
                  "learning_rate": 2e-5, "training_data_sha256": digest(rows),
                  "unique_training_rows": 1, "training_rows_per_epoch": 1,
                  "selection": {"excluded_hard_negative_count": 0, "resampled_easy_negative_count": 0},
                  "title_only": True, "labels": {"0": "different", "1": "same"}}
        manifest = {"configuration": config, "epoch_metrics": [{"examples": 1}]}
        # Reuse must not instantiate a model or tokenizer. Stub these imports so
        # this regression is runnable without torch, GPU access, or downloads.
        modules = {"torch": SimpleNamespace(), "transformers": SimpleNamespace(
            AutoModelForSequenceClassification=None, AutoTokenizer=None, set_seed=None)}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / ".cache" / "models" / "er-title-only"
            checkpoint.mkdir(parents=True)
            (checkpoint / "training_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch("pgc.experiments.run_er_research.ROOT", root), patch.dict("sys.modules", modules):
                reused_path, reused = train_variant("er-title-only", rows, args)
                self.assertEqual(reused_path, checkpoint)
                self.assertEqual(reused, manifest)
                changed = [{**rows[0], "gold_label": "different"}]
                with self.assertRaisesRegex(ValueError, "configuration differs"):
                    train_variant("er-title-only", changed, args)

    def test_hard_negative_replacement_preserves_budget_and_uses_training_only(self):
        rows = [pair("positive", "Graph theory", "Graph theory", "same"),
                pair("hard", "Graph theory", "Graph theories", "different"),
                pair("easy", "Graph algorithms", "Zoological taxonomy", "different")]
        held_out = pair("held-out", "Different", "Words", "different")
        selected, report = training_examples(rows, no_hard_negatives=True)
        self.assertEqual(len(selected), len(rows))
        self.assertEqual(sum(row["gold_label"] == "same" for row in selected), 1)
        self.assertEqual({row["id"] for row in selected}, {"positive", "easy"})
        self.assertNotIn(held_out["id"], {row["id"] for row in selected})
        self.assertEqual(report["excluded_hard_negative_count"], 1)
        self.assertEqual(selected, training_examples(rows, no_hard_negatives=True)[0])

    def test_hard_negative_ablation_requires_an_easy_training_pool(self):
        rows = [pair("hard", "Graph theory", "Graph theories", "different")]
        with self.assertRaisesRegex(ValueError, "easy"):
            training_examples(rows, no_hard_negatives=True)

    def test_context_and_title_arms_do_not_serialize_annotations(self):
        row = pair("x", "Paper A", "Paper B", "same")
        full = inputs(row)
        titles = inputs(row, title_only=True)
        self.assertIn("authors: A", full[0])
        self.assertNotIn("gold_label", full[0])
        self.assertNotIn("same", full[0])
        self.assertEqual(titles, ("Paper A", "Paper B"))
        changed = {**row, "gold_label": "different", "identity_groups": ["new", "groups"]}
        self.assertEqual(request_for(row).payload, request_for(changed).payload)

    def test_scalar_calibration_improves_calibration_nll_without_changing_argmax(self):
        rows = [pair(str(index), "A", "B", label) for index, label in enumerate(("same", "same", "different"))]
        predictions = [response(row, [-3, 3]) for row in rows]
        fitted = fit_temperature(rows, predictions)
        self.assertGreater(fitted["temperature"], 1)
        self.assertLess(fitted["calibration_nll_after"], fitted["calibration_nll_before"])
        self.assertEqual(fitted["fit_ids_sha256"], digest([row["id"] for row in rows]))
        scored = score_responses("calibrated", rows, predictions, temperature=fitted["temperature"])
        self.assertTrue(all(row["predicted_label"] == "same" for row in scored["predictions"]))

    def test_calibration_uses_checkpoint_label_order(self):
        rows = [pair(str(index), "A", "B", "same") for index in range(4)]
        predictions = [response(row, [4, -4], labels=("same", "different")) for row in rows]
        fitted = fit_temperature(rows, predictions)
        self.assertLess(fitted["calibration_nll_before"], 0.001)
        self.assertLessEqual(fitted["calibration_nll_after"], fitted["calibration_nll_before"])

    def test_missing_outputs_cannot_silently_reduce_evaluation_denominator(self):
        rows = [pair("a", "A", "B", "same"), pair("b", "C", "D", "different")]
        with self.assertRaises(ValueError):
            score_responses("missing", rows, [response(rows[0], [0, 1])])
        with self.assertRaises(ValueError):
            fit_temperature(rows, [response(rows[0], [0, 1])])

    def test_reordered_outputs_cannot_be_attached_to_other_gold_labels(self):
        rows = [pair("a", "A", "B", "same"), pair("b", "C", "D", "different")]
        predictions = [response(rows[1], [1, 0]), response(rows[0], [0, 1])]
        with self.assertRaises(ValueError):
            score_responses("reordered", rows, predictions)
        with self.assertRaises(ValueError):
            fit_temperature(rows, predictions)


if __name__ == "__main__":
    unittest.main()
