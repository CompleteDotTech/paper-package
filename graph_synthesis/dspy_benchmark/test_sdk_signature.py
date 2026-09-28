"""SDK schema regression: construction only, no inference or credentials."""
import unittest
from .study import proposer

class TestSignature(unittest.TestCase):
    def test_real_dspy_signature_has_no_reserved_fields(self):
        _, _, predictor = proposer(17)
        self.assertEqual(set(predictor.signature.output_fields), {'improved_instructions', 'improved_criteria'})
        self.assertIn('training_feedback_json', predictor.signature.input_fields)

if __name__ == '__main__':
    unittest.main()
