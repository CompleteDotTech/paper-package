import json
import tempfile
import unittest
from pathlib import Path
from pydantic import BaseModel
from .audit import json_safe
from .execution import install_audit_boundary
from . import study


class TokenDetails(BaseModel):
    cached_tokens: int = 7


class AuditTests(unittest.TestCase):
    def test_nested_sdk_usage_preserves_values(self):
        trace = {'usage': {'prompt_tokens_details': TokenDetails(), 'completion_tokens': 18}, 'outputs': ['ok']}
        expected = {'usage': {'prompt_tokens_details': {'cached_tokens': 7}, 'completion_tokens': 18}, 'outputs': ['ok']}
        self.assertEqual(json_safe(trace), expected)
        self.assertEqual(json.loads(json.dumps(json_safe(trace))), expected)

    def test_no_unknown_repr_or_nonfinite_values(self):
        for value in [object(), float('nan'), float('inf')]:
            with self.assertRaises((TypeError, ValueError)):
                json_safe(value)

    def test_digest_and_writer_share_identical_normalization(self):
        install_audit_boundary()
        value = {'usage': TokenDetails()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.json'
            study.write_json(path, value)
            self.assertEqual(study.digest(value), study.digest(json.loads(path.read_text())))

    def test_full_search_persists_nested_metadata(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import contextlib
        import numpy as np
        class LocalPredictor:
            def __call__(self, **kwargs):
                return SimpleNamespace(improved_instructions=['same?'], improved_criteria=[{}])
        lm = SimpleNamespace(history=[{'usage': {'prompt_tokens_details': TokenDetails()}, 'outputs': ['ok'], 'messages': []}])
        dspy = SimpleNamespace(context=lambda **kwargs: contextlib.nullcontext(), JSONAdapter=lambda: None)
        class FakeLive:
            def evaluate(self, task, arm, rows, configs, demos, phase):
                return np.array([[[.8,.2] if r['gold_label']=='same' else [.2,.8] for r in rows]])
        rows = [{'id':'1','record_1':{},'record_2':{'id':'a'},'gold_label':'same'},
                {'id':'2','record_1':{},'record_2':{'id':'b'},'gold_label':'different'}]
        baseline = {'q': {'type':'noul','instructions':'same?'}}
        install_audit_boundary()
        with tempfile.TemporaryDirectory() as directory, patch.object(study, 'proposer', return_value=(dspy,lm,LocalPredictor())):
            result = study.search('entity_resolution','baseline_noul',baseline,
                    {'train':rows,'validation':rows,'demonstrations':[]},FakeLive(),Path(directory),17)
            saved = json.loads((Path(directory)/'search-17.json').read_text())
            self.assertEqual(result['ledger_sha256'],study.digest(saved))
            self.assertEqual(len(saved),4)


if __name__ == '__main__':
    unittest.main()
