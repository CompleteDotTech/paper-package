import unittest

from pgc.experiments.run_nli_research import choose_sentences, fit_idf, fit_temperature


class NLIResearchPolicyTests(unittest.TestCase):
    def test_selector_uses_query_and_training_idf_but_no_gold_annotation(self):
        row = {"claim": "Protein X inhibits cancer", "evidence": ["Unrelated background words.",
                                                                    "Protein X inhibits cancer.",
                                                                    "Additional unrelated words."],
               "gold_label": "SUPPORTS", "rationale_sentence_ids": [1]}
        chosen = choose_sentences(row, {"protein": 2, "cancer": 2}, lambda text: len(text.split()), budget=5)
        changed = {**row, "gold_label": "REFUTES", "rationale_sentence_ids": [0]}
        self.assertEqual(chosen, [1])
        self.assertEqual(chosen, choose_sentences(changed, {"protein": 2, "cancer": 2}, lambda text: len(text.split()), budget=5))

    def test_idf_counts_unique_training_documents(self):
        rows = [{"document_id": "a", "evidence": ["common rare"]},
                {"document_id": "a", "evidence": ["common rare"]},
                {"document_id": "b", "evidence": ["common"]}]
        idf = fit_idf(rows)
        self.assertAlmostEqual(idf["common"], 1.0)
        self.assertGreater(idf["rare"], idf["common"])

    def test_temperature_uses_calibration_objective_and_preserves_argmax(self):
        logits = [[6.0, 0.0, 0.0], [6.0, 0.0, 0.0], [6.0, 0.0, 0.0]]
        fitted = fit_temperature(logits, [0, 0, 1])
        self.assertGreater(fitted["temperature"], 1.0)
        self.assertLess(fitted["nll_after"], fitted["nll_before"])
        self.assertEqual(fitted["calibration_rows"], 3)

    def test_sentence_fallback_retains_some_input_under_tiny_budget(self):
        row = {"claim": "target", "evidence": ["very long unrelated sentence", "target matching sentence"]}
        self.assertEqual(choose_sentences(row, {}, lambda text: len(text.split()), budget=1), [1])


if __name__ == "__main__":
    unittest.main()
