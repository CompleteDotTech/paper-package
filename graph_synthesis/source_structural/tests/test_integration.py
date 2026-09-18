"""Concurrent research sections cannot displace one another."""
import json
import unittest
from graph_synthesis.source_structural.report import START, END, ANCHOR, replace_after_anchor, render
from graph_synthesis.source_structural.run import HERE
from graph_synthesis.structural.report import insert, START as OTHER_START, END as OTHER_END

class IntegrationTests(unittest.TestCase):
    def test_either_reporter_is_idempotent_after_both_sections(self):
        text = 'before\n' + ANCHOR + '\nold tail\n'
        text = insert(text, 'concurrent evidence')
        text = replace_after_anchor(text, 'new evidence')
        self.assertEqual(insert(text, 'concurrent evidence'), text)
        self.assertEqual(replace_after_anchor(text, 'new evidence'), text)
        self.assertLess(text.index(OTHER_END), text.index(START))
        self.assertEqual(text.count(OTHER_START), 1)
        self.assertEqual(text.count(END), 1)
        self.assertTrue(text.endswith('old tail\n'))

    def test_concurrent_evidence_disclosure_is_in_manuscript_source(self):
        r = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
        text = render(r)
        self.assertIn('PR #18', text)
        self.assertIn('must not be pooled as independent observations', text)
        self.assertIn('No hypothesis, threshold or numerical result here was retuned', text)

if __name__ == '__main__':
    unittest.main()
