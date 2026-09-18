"""New sections must not compete with previous reports for an insertion point."""
import re
import unittest
from graph_synthesis.novel_mechanisms.publication import report_layout_text, LAYOUT_ANCHOR
from graph_synthesis.novel_mechanisms.report import ANCHOR, replace_after_anchor
from graph_synthesis.novel_mechanisms.regret import insert_section


class PaperLayoutTests(unittest.TestCase):
    def test_anchor_follows_all_integrated_prior_studies(self):
        self.assertEqual(ANCHOR, LAYOUT_ANCHOR)
        self.assertEqual(ANCHOR, '<!-- UNCERTAINTY_RESEARCH_END -->')

    def test_only_anchor_line_changes_and_transformation_is_idempotent(self):
        source="START = 'unchanged'\nANCHOR = '<!-- RELIABILITY_RESEARCH_END -->'\nEND = 'unchanged'\n"
        prepared=report_layout_text(source)
        self.assertEqual(prepared,report_layout_text(prepared))
        self.assertEqual(sum(a!=b for a,b in zip(source.splitlines(),prepared.splitlines())),1)
        self.assertTrue(prepared.startswith("START = 'unchanged'"))
        self.assertTrue(prepared.endswith("END = 'unchanged'\n"))

    def test_prior_section_rebuild_does_not_move_new_sections(self):
        reliability='<!-- RELIABILITY_RESEARCH_END -->'
        start='<!-- STRUCTURAL_RESEARCH_START -->'
        end='<!-- STRUCTURAL_RESEARCH_END -->'
        structural=start+'\n\nprior structural evidence\n\n'+end
        old='intro\n\n'+reliability+'\n\n'+structural+'\n\nprior source evidence\n\n'+ANCHOR+'\n\nfooter\n'
        combined=insert_section(replace_after_anchor(old,'original new experiments'),'replacement experiment')
        # Independently emulate the older report's remove-and-insert operation.
        removed=re.sub(re.escape(start)+r'.*?'+re.escape(end)+r'\s*','',combined,flags=re.S)
        before,after=removed.split(reliability,1)
        rebuilt=before+reliability+'\n\n'+structural+'\n\n'+after.lstrip()
        self.assertEqual(rebuilt,combined)
        self.assertEqual(insert_section(replace_after_anchor(combined,'original new experiments'),'replacement experiment'),combined)
        self.assertTrue(combined.endswith('footer\n'))

    def test_unknown_or_duplicate_anchor_fails_closed(self):
        for text in ('no anchor',"ANCHOR = 'unreviewed'\n", "ANCHOR = 'a'\nANCHOR = 'b'\n"):
            with self.assertRaises(ValueError):report_layout_text(text)


if __name__=='__main__':unittest.main()
