"""The separately maintained frontier paper check must preserve our sections."""
import unittest
from graph_synthesis.novel_mechanisms.publication import (
    ROOT, FRONTIER_WORKFLOW, COMMANDS, frontier_workflow_text, transformed,
)


class FrontierPublicationTests(unittest.TestCase):
    def test_exactly_two_additive_steps_and_no_weakened_gate(self):
        text=(ROOT/FRONTIER_WORKFLOW).read_text(encoding='utf-8')
        prepared=frontier_workflow_text(text)
        self.assertEqual(frontier_workflow_text(prepared),prepared)
        self.assertEqual(transformed(FRONTIER_WORKFLOW,text),prepared)
        self.assertEqual(prepared.count(COMMANDS),1)
        anchor='          git diff --exit-code -- graph_synthesis/frontier manuscript/paper-current.md CURRENT_RESULTS.md'
        self.assertLess(prepared.index(COMMANDS),prepared.index(anchor))
        self.assertIn('python -B -m graph_synthesis.frontier.report --figures --update-paper',prepared)
        without=lambda value: ''.join(line for line in value.splitlines(keepends=True) if line not in COMMANDS.splitlines(keepends=True))
        self.assertEqual(without(prepared),without(text))

    def test_unknown_frontier_layout_fails_closed(self):
        with self.assertRaises(ValueError):
            frontier_workflow_text('no recognized frontier paper reconstruction gate')


if __name__=='__main__':unittest.main()
