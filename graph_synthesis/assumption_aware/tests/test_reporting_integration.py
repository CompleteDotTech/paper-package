"""Preserve concurrently merged research sections during additive regeneration."""
import unittest
from graph_synthesis.assumption_aware.report import replace, START, END, ANCHOR


class ReportingIntegrationTests(unittest.TestCase):
    def test_append_after_latest_predecessor_and_preserve_content(self):
        for markers in ([ANCHOR], [ANCHOR, '<!-- STRUCTURAL_RESEARCH_END -->'],
                        [ANCHOR, '<!-- STRUCTURAL_RESEARCH_END -->', '<!-- SOURCE_STRUCTURAL_RESEARCH_END -->']):
            source='prefix\n'+'\n'.join(markers)+'\n\nretained trailing study\n'
            got=replace(source,'new evidence')
            self.assertLess(got.index(markers[-1]),got.index(START))
            self.assertLess(got.index(END),got.index('retained trailing study'))
            for marker in markers:self.assertEqual(got.count(marker),1)
            self.assertEqual(got,replace(got,'new evidence'))
    def test_replace_only_own_section(self):
        source=ANCHOR+'\n\n<!-- STRUCTURAL_RESEARCH_START -->\nkeep structural\n<!-- STRUCTURAL_RESEARCH_END -->\n'
        got=replace(source,'old own text')
        updated=replace(got,'replacement')
        self.assertNotIn('old own text',updated)
        self.assertIn('keep structural',updated)
        self.assertEqual(updated.count(START),1)
        self.assertEqual(updated.count(END),1)
    def test_missing_or_duplicated_predecessor_rejected(self):
        for source in ('no anchor',ANCHOR+'\n'+ANCHOR):
            with self.assertRaises(ValueError):replace(source,'new evidence')


if __name__=='__main__':unittest.main()
