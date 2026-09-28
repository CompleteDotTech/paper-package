import unittest

from graph_synthesis.post_certificate_h2_followup.run import execute


class FrozenFollowupTests(unittest.TestCase):
    def test_full_replay_meets_new_conjunction(self):
        result = execute()
        self.assertTrue(result['primary_target_met'])
        self.assertEqual(result['original_h2_result'],
                         {'passed': 63, 'total': 64, 'primary_target_met': False})
        self.assertEqual(result['counts']['affected_injection'], {'passed': 64, 'total': 64})
        self.assertEqual(result['counts']['unaffected_noop'], {'passed': 64, 'total': 64})

    def test_suppressed_injection_is_detected(self):
        result = execute(suppress_fault=True)
        self.assertFalse(result['primary_target_met'])
        self.assertEqual(result['counts']['affected_injection'], {'passed': 0, 'total': 64})


if __name__ == '__main__':
    unittest.main()
