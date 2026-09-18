"""Regression controls for the serialization failure found by full replay."""
import json
import unittest
from graph_synthesis.reliability.run import json_value, graph_benchmark


class ArtifactTests(unittest.TestCase):
    def test_tuples_become_json_arrays(self):
        self.assertEqual(json_value({'edges': [('a', 'b')]}), {'edges': [['a', 'b']]})

    def test_normalization_is_idempotent(self):
        value = {'nested': [(1, {'value': .5})], 'target': False}
        self.assertEqual(json_value(value), json_value(json_value(value)))

    def test_nan_is_rejected(self):
        with self.assertRaises(ValueError):
            json_value({'invalid': float('nan')})

    def test_infinity_is_rejected(self):
        with self.assertRaises(ValueError):
            json_value({'invalid': float('inf')})

    def test_nested_benchmark_container_types_survive_roundtrip(self):
        value = json_value(graph_benchmark())
        restored = json.loads(json.dumps(value))
        def check_types(left, right):
            self.assertIs(type(left), type(right))
            if isinstance(left, dict):
                self.assertEqual(set(left), set(right))
                for key in left:
                    check_types(left[key], right[key])
            elif isinstance(left, list):
                self.assertEqual(len(left), len(right))
                for a, b in zip(left, right):
                    check_types(a, b)
            else:
                self.assertEqual(left, right)
        check_types(value, restored)


if __name__ == '__main__':
    unittest.main()
