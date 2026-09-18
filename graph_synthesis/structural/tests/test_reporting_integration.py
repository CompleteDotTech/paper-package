"""Preserve concurrently merged research under either report rebuild order."""
import unittest
from graph_synthesis.structural.report import insert, START, END, ANCHOR
from graph_synthesis.reliability.report import replace_after_anchor
class IntegrationTests(unittest.TestCase):
    def test_prior_baseline(self):
        text=insert('prior'+ANCHOR+'\nlegacy','structural')
        self.assertIn('structural',text)
        self.assertTrue(text.endswith('legacy'))
    def test_reliability_precedes_structural(self):
        text=insert(replace_after_anchor('prior'+ANCHOR+'\nlegacy','reliability'),'structural')
        self.assertLess(text.index('<!-- RELIABILITY_RESEARCH_END -->'),text.index(START))
        self.assertEqual(text.count(END),1)
    def test_idempotent(self):
        text=insert(replace_after_anchor('prior'+ANCHOR+'\nlegacy','reliability'),'structural')
        self.assertEqual(text,insert(text,'structural'))
        self.assertEqual(text,replace_after_anchor(text,'reliability'))
    def test_rebuild_order_commutes(self):
        base='prior'+ANCHOR+'\nlegacy'
        first=insert(replace_after_anchor(base,'reliability'),'structural')
        second=replace_after_anchor(insert(base,'structural'),'reliability')
        self.assertEqual(first,second)
