"""Integration checks exercise real frozen observations; mock calls are explicit."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from graph_synthesis.core import GraphStore, Relation, digest, graph_metrics
from graph_synthesis.recorded import (BASELINES, LABELS, JevFormulation, RecordedJev,
    checked_file, input_state, inventory, parse_answer, payload_for)
from graph_synthesis.study import (action_metrics, binomial_upper, calibration_policy,
    make_graph, paired_precision_interval, read_scores, run_study)
from graph_synthesis.verify import compare_json

ROOT = Path(__file__).resolve().parents[2]


class RecordedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = RecordedJev(ROOT)
        cls.task, cls.arm = 'relation_support', 'fewshot_contract'
        cls.row = cls.backend.plan['tasks'][cls.task]['evaluation'][0]

    def score(self, state=None):
        return self.backend.score(self.task, self.arm, 'evaluation', self.row['id'],
                                  input_state(self.task, self.row) if state is None else state)

    def test_frozen_inventory_is_unchanged(self):
        entries = inventory(ROOT)
        self.assertEqual(len(entries), 161)
        self.assertFalse(any(name.startswith("reproduction/data/sources/") for name in entries))
        self.assertIn("scripts/download_datasets.py", entries)
        self.assertIn("scripts/datasets.json", entries)
        for relative in entries:
            checked_file(ROOT, relative, entries)

    def test_exact_raw_observation_reconstructs(self):
        score = self.score()
        self.assertEqual(score.mode, 'recorded')
        self.assertEqual(score.model, 'jev-1.13.0')
        self.assertIn(score.call_id, self.backend.calls)
        self.assertEqual(score.request_hash, digest(payload_for(self.backend.plan, self.task,
                                        self.arm, input_state(self.task, self.row))))

    def test_state_change_cannot_reuse_a_score(self):
        state = input_state(self.task, self.row)
        state['claim'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'Changed evidence'): self.score(state)

    def test_raw_response_change_is_detected(self):
        score = self.score()
        original = self.backend.calls[score.call_id]
        changed = deepcopy(original)
        changed['response']['model'] = 'not-the-model'
        with patch.dict(self.backend.calls, {score.call_id: changed}):
            with self.assertRaisesRegex(ValueError, 'model'): self.score()

    def test_prompt_change_is_detected(self):
        score = self.score()
        changed = deepcopy(self.backend.calls[score.call_id])
        changed['payload']['state']['input']['claim'] = 'different target'
        with patch.dict(self.backend.calls, {score.call_id: changed}):
            with self.assertRaisesRegex(ValueError, 'formulation'): self.score()

    def test_prediction_change_is_detected(self):
        key = (self.task, self.arm, 'evaluation', self.row['id'])
        changed = deepcopy(self.backend.predictions[key])
        changed['distribution'] = {'SUPPORTS': .1, 'REFUTES': .8, 'NOT_ENOUGH_INFO': .1}
        with patch.dict(self.backend.predictions, {key: changed}):
            with self.assertRaisesRegex(ValueError, 'reconstruct'): self.score()

    def test_error_remains_error_without_neutral_probability(self):
        records = [r for r in self.backend.predictions.values() if r['error']]
        self.assertTrue(records)
        for record in records:
            row = self.backend.rows[record['task'], record['split'], record['id']]
            score = self.backend.score(record['task'], record['arm'], record['split'], record['id'],
                                       input_state(record['task'], row))
            self.assertEqual(score.label, 'ERROR')
            self.assertEqual(score.probabilities, {})

    def test_evaluation_gold_never_enters_current_input(self):
        state = input_state(self.task, {**self.row, 'gold_label': 'SENTINEL_EVALUATION_GOLD'})
        payload = payload_for(self.backend.plan, self.task, self.arm, state)
        self.assertNotIn('SENTINEL_EVALUATION_GOLD', json.dumps(payload))
        self.assertEqual(len(payload['state']['labeled_examples']), 6)
        with self.assertRaisesRegex(ValueError, 'gold labels'):
            payload_for(self.backend.plan, self.task, self.arm, {**state, 'gold_label': 'SUPPORTS'})

    def test_out_of_scope_task_and_arm_fail_closed(self):
        with self.assertRaises(ValueError): self.backend.score('new_task', self.arm, 'evaluation', 'x', {})
        with self.assertRaises(ValueError): self.backend.score(self.task, 'identity_noul', 'evaluation', 'x', {})
        with self.assertRaises(ValueError): self.backend.score(self.task, self.arm, 'train', 'x', {})

    def test_fake_live_adapter_requires_consent_and_counts_failures(self):
        original = self.backend.calls[self.score().call_id]
        class Adapter:
            count = 0
            def version(self): return 'jev-1.13.0'
            def send_payload(self, state, questions):
                self.count += 1
                return {'response': original['response'], 'execution_mode': 'mock'}
        adapter = Adapter()
        with self.assertRaises(ValueError): JevFormulation(self.backend.plan, adapter)
        form = JevFormulation(self.backend.plan, adapter, allow_live=True, max_calls=1)
        self.assertEqual(adapter.count, 0)
        score = form.score(self.task, self.arm, input_state(self.task, self.row))
        self.assertEqual(score.mode, 'synthetic')
        with self.assertRaises(RuntimeError): form.score(self.task, self.arm, input_state(self.task, self.row))
        self.assertEqual(adapter.count, 1)
        failed = JevFormulation(self.backend.plan, adapter, allow_live=True, max_calls=1)
        with patch.object(adapter, 'send_payload', side_effect=RuntimeError('simulated outage')):
            with self.assertRaises(RuntimeError): failed.score(self.task, self.arm, input_state(self.task, self.row))
        self.assertEqual(failed.calls, 1)
        with self.assertRaises(RuntimeError): failed.score(self.task, self.arm, input_state(self.task, self.row))

    def test_unknown_model_cannot_use_frozen_formulation(self):
        class Adapter:
            def version(self): return 'new-model'
        with self.assertRaisesRegex(ValueError, 'versions differ'):
            JevFormulation(self.backend.plan, Adapter(), allow_live=True)

    def test_bad_response_contract_rejected(self):
        for answer in ({'model': 'jev-1.13.0', 'answers': {}},
                       {'model': 'jev-1.13.0', 'answers': {'fewshot_contract__decision':
                        {'type': 'choice', 'choice': 'SUPPORTS', 'probabilities':
                         {'SUPPORTS': .1, 'REFUTES': .8, 'NOT_ENOUGH_INFO': .1}}}}):
            with self.assertRaises(ValueError): parse_answer(answer, self.task, self.arm, 'jev-1.13.0')

    def test_graph_is_independent_of_gold_but_metrics_are_not(self):
        rows = read_scores(self.backend, self.task, self.arm, 'evaluation')[:12]
        altered = [{**row, 'gold': 'changed evaluator gold', 'row': {**row['row'], 'gold_label': 'changed'}} for row in rows]
        a, b = make_graph(rows, self.task), make_graph(altered, self.task)
        self.assertEqual(a['audit'], b['audit'])
        self.assertEqual(a['metrics'], b['metrics'])
        self.assertEqual(a['accepted_assertion_ids'], b['accepted_assertion_ids'])

    def test_exported_graph_contains_sources_and_durable_lifecycle(self):
        rows = read_scores(self.backend, self.task, self.arm, 'evaluation')[:12]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = make_graph(rows, self.task, export_directory=out)
            initial = json.loads((out/'initial-state.json').read_text())
            final = json.loads((out/'after-withdrawal.json').read_text())
            view = json.loads((out/'accepted-view.json').read_text())
            self.assertEqual(len(view['edges']), result['metrics']['typed_edges'])
            self.assertEqual(initial['facts'].keys(), final['facts'].keys())
            self.assertTrue(initial['evidence'])
            for item in initial['facts'].values():
                self.assertTrue(set(item['evidence']) <= initial['evidence'].keys())
                self.assertEqual(item['decision']['mode'], 'recorded')


class MetricTests(unittest.TestCase):
    def rows(self, groups=None):
        return [{'id': str(i), 'group': str(i) if groups is None else groups[i],
                 'gold': 'same' if i == 0 else 'different', 'label': 'same', 'score': .99}
                for i in range(4)]

    def test_precision_false_positive_rate_and_coverage_have_distinct_denominators(self):
        m = action_metrics(self.rows(), {'0', '1'}, 'same')
        self.assertEqual((m['precision'], m['false_positive_rate'], m['coverage']), (.5, 1/3, .5))
        self.assertIsNone(action_metrics(self.rows(), set(), 'same')['precision'])

    def test_binomial_upper_matches_zero_error_closed_form(self):
        self.assertAlmostEqual(binomial_upper(0, 63), 1-.05**(1/63))
        self.assertIsNone(binomial_upper(0, 0))
        self.assertEqual(binomial_upper(3, 3), 1)
        self.assertGreater(binomial_upper(2, 63), 2/63)
        with self.assertRaises(ValueError): binomial_upper(4, 3)

    def test_binomial_numeric_reference(self):
        # P(X<=1) with n=2: 1-p^2=.05, hence p=sqrt(.95).
        self.assertAlmostEqual(binomial_upper(1, 2), .95**.5, places=12)

    def test_calibration_never_accepts_evaluation_split(self):
        with self.assertRaisesRegex(ValueError, 'evaluation'):
            calibration_policy(self.rows(), 'same', split='evaluation')

    def test_small_negative_sample_does_not_certify_deployment(self):
        result = calibration_policy(self.rows(), 'same', split='calibration')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertIsNone(result['threshold'])

    def test_dependent_calibration_rows_cannot_use_iid_binomial_qualification(self):
        result = calibration_policy(self.rows(['a', 'a', 'b', 'b']), 'same', split='calibration')
        self.assertEqual(result['status'], 'dependent_rows_no_binomial_qualification')
        self.assertIsNone(result['threshold'])

    def test_paired_bootstrap_respects_components_and_no_acceptance(self):
        rows = self.rows(['a', 'a', 'b', 'b'])
        result = paired_precision_interval(rows, rows, {'0'}, {'0'}, 'same')
        self.assertEqual(result['units'], 2)
        self.assertEqual(result['interval'], [0, 0])
        self.assertIsNone(paired_precision_interval(rows, rows, set(), set(), 'same')['interval'])

    def test_directed_multi_relation_and_component_metrics(self):
        edges = [{'subject': a, 'predicate': p, 'object': b} for a,p,b in
                 [('a','p','b'), ('a','q','b'), ('b','p','a')]]
        m=graph_metrics('abc', edges)
        self.assertEqual(m['multi_label_directed_pairs'], 1)
        self.assertEqual(m['reciprocal_pair_sets'], 1)
        self.assertEqual(m['weak_component_size_histogram'], {'1': 1, '2': 1})

    def test_float_roundoff_is_reported_and_not_mislabeled_bitwise_equal(self):
        differences = compare_json({'x': .025921259572331056}, {'x': .025921259572331053})
        self.assertEqual(len(differences), 1)
        for a,b in [({'x': 1}, {'x': 2}), ({'x': 1}, {'x': 1.0}), ({'x': .8}, {'x': .81}),
                    ({'x': []}, {'x': [1]}), ({'x': 1}, {'y': 1})]:
            with self.assertRaises(ValueError): compare_json(a,b)

    def test_unmanifested_and_changed_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); (p/'a').write_text('a')
            manifest={'a': {'bytes': 1, 'sha256': hashlib.sha256(b'a').hexdigest()}}
            self.assertEqual(checked_file(p, 'a', manifest), b'a')
            with self.assertRaises(ValueError): checked_file(p, '../a', manifest)
            (p/'a').write_text('b')
            with self.assertRaises(ValueError): checked_file(p, 'a', manifest)


if __name__ == '__main__':
    unittest.main()
