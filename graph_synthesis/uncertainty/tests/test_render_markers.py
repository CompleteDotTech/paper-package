"""Reader-facing rendering must not expose manuscript insertion metadata."""
import unittest
from graph_synthesis.render_current_paper import strip_research_markers


class RenderMarkerTests(unittest.TestCase):
    def test_all_study_markers_are_hidden(self):
        for study in ('FOLLOWUP', 'ADAPTIVE', 'RISK_CONTROL', 'RELIABILITY', 'STRUCTURAL', 'UNCERTAINTY', 'FUTURE_STUDY'):
            for boundary in ('START', 'END'):
                with self.subTest(study=study, boundary=boundary):
                    self.assertEqual(strip_research_markers(f'before<!-- {study}_RESEARCH_{boundary} -->after'), 'beforeafter')

    def test_reader_text_and_other_comments_are_preserved(self):
        text = '# Evidence\n\nUNCERTAINTY_RESEARCH_START is an example identifier.\n<!-- Author note -->\n'
        self.assertEqual(strip_research_markers(text), text)
        cleaned = strip_research_markers('A\n<!-- UNCERTAINTY_RESEARCH_START -->\nB')
        self.assertEqual(strip_research_markers(cleaned), cleaned)


if __name__ == '__main__':
    unittest.main()
