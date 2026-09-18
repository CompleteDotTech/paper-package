"""Report integration is additive and retains negative evidence."""
import json
import re
import unittest
from graph_synthesis.source_structural.report import (START, END, ANCHOR, TITLES, render, replace_after_anchor)
from graph_synthesis.source_structural.run import HERE


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = json.loads((HERE/'results.json').read_text(encoding='utf-8'))

    def test_all_five_hypotheses(self):
        text = render(self.results)
        for i, title in enumerate(TITLES, 1):
            self.assertIn(f'| H{i}: {title}', text)

    def test_negative_outcomes_retained(self):
        text = render(self.results)
        rows = [x for x in text.splitlines() if x.startswith('| H')]
        self.assertEqual(sum('| Not met |' in x for x in rows), 2)
        self.assertEqual(sum('| Met |' in x for x in rows), 3)

    def test_no_new_service_claim(self):
        text = render(self.results)
        self.assertIn('Fresh service calls: 0', text)
        self.assertIn('not an independent preregistration', text)
        self.assertIn('not necessarily one document', text)

    def test_five_local_figures(self):
        links = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', render(self.results))
        self.assertEqual(len(links), 5)
        self.assertEqual(len(set(links)), 5)
        self.assertTrue(all(link.startswith('figures/') and link.endswith('.png') for link in links))

    def test_additive_update(self):
        text = 'before\n'+ANCHOR+'\n\nafter\n'
        updated = replace_after_anchor(text, 'new')
        self.assertTrue(updated.startswith('before\n'+ANCHOR))
        self.assertTrue(updated.endswith('after\n'))
        self.assertEqual(updated.count(START), 1)
        self.assertEqual(updated.count(END), 1)

    def test_idempotent_update(self):
        once = replace_after_anchor(ANCHOR+'\nold tail\n', 'new')
        self.assertEqual(replace_after_anchor(once, 'new'), once)
        changed = replace_after_anchor(once, 'replacement')
        self.assertNotIn('\nnew\n', changed)
        self.assertIn('old tail', changed)

    def test_absent_anchor_rejected(self):
        with self.assertRaises(ValueError):
            replace_after_anchor('missing', 'new')

    def test_duplicate_anchor_rejected(self):
        with self.assertRaises(ValueError):
            replace_after_anchor(ANCHOR+ANCHOR, 'new')


if __name__ == '__main__':
    unittest.main()
