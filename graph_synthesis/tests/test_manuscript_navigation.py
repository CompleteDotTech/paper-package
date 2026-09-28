"""Check that the published directory points into all preserved studies."""

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from graph_synthesis import manuscript_navigation as nav
from graph_synthesis.manuscript_navigation import END, START, STUDIES, update_navigation
from graph_synthesis.render_current_paper import render_with_anchors, strip_research_markers


ROOT = Path(__file__).resolve().parents[2]


class ManuscriptNavigationTests(unittest.TestCase):
    def test_map_is_current_and_preserves_every_study_byte(self):
        source = (ROOT / 'manuscript/paper-current.md').read_text(encoding='utf-8')
        self.assertEqual(update_navigation(source), source)
        _, remainder = source.split(START, 1)
        _, studies = remainder.split(END, 1)
        self.assertEqual(studies.count('<!-- ADAPTIVE_RESEARCH_START -->'), 1)
        self.assertEqual(studies.count('# Original study (historical evidence; unchanged text)'), 1)
        for study in STUDIES:
            self.assertEqual(studies.count('# ' + study.title + '\n'), 1)

    def test_markdown_links_resolve_in_rendered_html(self):
        source = (ROOT / 'manuscript/paper-current.md').read_text(encoding='utf-8')
        body = render_with_anchors(strip_research_markers(source))
        destinations = set(re.findall(r'\bid="([^"]+)"', body))
        fragments = re.findall(r'href="#([^"]+)"', body)
        self.assertEqual(len(fragments), 2 * len(STUDIES) + 3)
        self.assertTrue(set(fragments) <= destinations)
        anchors = nav._study_anchors(source.split(END, 1)[1])
        for index, (study_anchor, protocol_anchor) in enumerate(anchors):
            self.assertIn(study_anchor, destinations)
            self.assertIn(protocol_anchor, destinations)
            self.assertIn(f'href="#{study_anchor}"', body)
            self.assertIn(f'href="#{protocol_anchor}"', body)
            start = body.index(f'id="{study_anchor}"')
            protocol = body.index(f'id="{protocol_anchor}"')
            self.assertLess(start, protocol)
            if index + 1 < len(anchors):
                self.assertLess(protocol, body.index(f'id="{anchors[index + 1][0]}"'))

    def test_duplicate_protocol_headings_link_to_their_own_studies(self):
        studies = (nav.Study('First study', 'Protocol', 'Recorded', 'Result'),
                   nav.Study('Second study', 'Protocol', 'Controlled', 'Result'))
        source = '<!-- FIRST_RESEARCH_START -->\n\n# First study\n\n## Protocol\n\n# Second study\n\n## Protocol\n'
        with patch.object(nav, 'STUDIES', studies):
            mapped = update_navigation(source)
        self.assertIn('[Protocol and scope](#protocol)', mapped)
        self.assertIn('[Protocol and scope](#protocol-1)', mapped)
        body = render_with_anchors(strip_research_markers(mapped))
        self.assertLess(body.index('id="second-study"'), body.index('id="protocol-1"'))

    def test_missing_study_fails_instead_of_publishing_stale_map(self):
        source = (ROOT / 'manuscript/paper-current.md').read_text(encoding='utf-8')
        missing = source.replace('# ' + STUDIES[0].title + '\n', '# Missing\n', 1)
        with self.assertRaisesRegex(ValueError, 'study title'):
            update_navigation(missing)


if __name__ == '__main__':
    unittest.main()
