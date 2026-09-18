"""Narrow publication-integration invariants without changing archived studies."""
import re
import unittest
from graph_synthesis.novel_mechanisms.publication import ROOT, RENDERER, WORKFLOW, MARKERS, COMMANDS, renderer_text, workflow_text


class PublicationTests(unittest.TestCase):
    def test_all_named_research_markers_are_removed(self):
        for name in ('FOLLOWUP','SOURCE_STRUCTURAL','NOVEL_MECHANISMS','INTERVAL_REGRET','FUTURE_2'):
            for boundary in ('START','END'):
                marker=f'<!-- {name}_RESEARCH_{boundary} -->'
                self.assertEqual(re.sub(MARKERS,'','before'+marker+'after'),'beforeafter')

    def test_unrelated_html_and_comments_are_not_unescaped(self):
        text='<script>unsafe()</script><!-- ordinary comment -->'
        self.assertEqual(re.sub(MARKERS,'',text),text)
        prepared=renderer_text((ROOT/RENDERER).read_text(encoding='utf-8'))
        self.assertIn('{"html": False}',prepared)
        self.assertIn('Only local assets allowed',prepared)

    def test_renderer_mutation_is_single_line_and_idempotent(self):
        source=(ROOT/RENDERER).read_text(encoding='utf-8')
        prepared=renderer_text(source)
        self.assertEqual(renderer_text(prepared),prepared)
        self.assertEqual(len(source.splitlines()),len(prepared.splitlines()))
        self.assertLessEqual(sum(a!=b for a,b in zip(source.splitlines(),prepared.splitlines())),1)

    def test_full_rebuild_includes_both_additive_reports(self):
        source=(ROOT/WORKFLOW).read_text(encoding='utf-8')
        prepared=workflow_text(source)
        self.assertEqual(workflow_text(prepared),prepared)
        self.assertEqual(prepared.count(COMMANDS),1)
        self.assertLess(prepared.index('source_structural.report --update-paper'),prepared.index(COMMANDS))
        self.assertLess(prepared.index(COMMANDS),prepared.index('git diff --exit-code -- experiments/jev-multicall-20260918/REPORT.md'))
        without=lambda text: ''.join(line for line in text.splitlines(keepends=True) if line not in COMMANDS.splitlines(keepends=True))
        self.assertEqual(without(prepared),without(source))

    def test_unknown_publication_layout_fails_closed(self):
        with self.assertRaises(ValueError):renderer_text('no recognized stripping line')
        with self.assertRaises(ValueError):workflow_text('no recognized reconstruction gate')


if __name__=='__main__':unittest.main()
