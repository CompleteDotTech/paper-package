"""Narrow, idempotent integration of publication infrastructure; no evidence edits."""
from __future__ import annotations
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RENDERER = 'graph_synthesis/render_current_paper.py'
WORKFLOW = '.github/workflows/jev-multicall.yml'
REPORT = 'graph_synthesis/novel_mechanisms/report.py'
MARKERS = r'<!-- [A-Z][A-Z0-9_]*_RESEARCH_(?:START|END) -->'
COMMANDS = ('          python -B -m graph_synthesis.novel_mechanisms.report --update-paper\n'
            '          python -B -m graph_synthesis.novel_mechanisms.regret --report\n')
LAYOUT_ANCHOR = '<!-- UNCERTAINTY_RESEARCH_END -->'


def renderer_text(text: str) -> str:
    """Keep the reviewed main helper unchanged, or adapt the previous inline form."""
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise ValueError('Unparseable publication source') from error
    helpers = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='strip_research_markers']
    if helpers:
        # Main 114450 introduced its own safe generic helper. Preserve that
        # implementation and numeric-table improvements byte-for-byte.
        expected = ast.parse("def strip_research_markers(markdown):\n    return RESEARCH_MARKER.sub('', markdown)\n").body[0]
        actual = helpers[0]
        body = [node for node in actual.body if not (isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str))]
        same = (len(helpers)==1 and ast.dump(actual.args)==ast.dump(expected.args)
                and [ast.dump(node) for node in body]==[ast.dump(node) for node in expected.body])
        assignments = [node for node in tree.body if isinstance(node,ast.Assign)
                       and any(isinstance(t,ast.Name) and t.id=='RESEARCH_MARKER' for t in node.targets)]
        pattern = r'<!--\s*[A-Z][A-Z0-9_]*_RESEARCH_(?:START|END)\s*-->'
        approved = ast.parse('RESEARCH_MARKER = re.compile('+repr(pattern)+')').body[0]
        if not (same and len(assignments)==1 and ast.dump(assignments[0])==ast.dump(approved)
                and 'markdown = strip_research_markers(source.read_text(encoding="utf-8"))' in text
                and '{"html": False}' in text and 'Only local assets allowed' in text):
            raise ValueError('Unreviewed main renderer helper')
        return text
    lines = text.splitlines(keepends=True)
    matches = [i for i,line in enumerate(lines) if line.lstrip().startswith('markdown = re.sub(')
               and '_RESEARCH_' in line and 'source.read_text' in line]
    if len(matches) != 1:
        raise ValueError('Expected exactly one reviewed marker-stripping line')
    i = matches[0]
    parsed = ast.parse(lines[i].strip())
    call = parsed.body[0].value
    if not isinstance(call,ast.Call) or len(call.args) != 3 or not isinstance(call.args[0],ast.Constant):
        raise ValueError('Unexpected marker-strip expression')
    lines[i] = ('    markdown = re.sub(r"'+MARKERS+'", "", source.read_text(encoding="utf-8"))\n')
    return ''.join(lines)


def workflow_text(text: str) -> str:
    """Add both new sections after all preceding reconstruction steps, before diff."""
    for line in COMMANDS.splitlines(keepends=True):
        text = text.replace(line,'')
    anchor = '          git diff --exit-code -- experiments/jev-multicall-20260918/REPORT.md'
    if text.count(anchor) != 1:
        raise ValueError('Expected exactly one complete-paper regeneration gate')
    return text.replace(anchor, COMMANDS+anchor,1)


def report_layout_text(text: str) -> str:
    """Append after previous studies, avoiding their individual insertion anchors.

    Only the publication anchor changes. Protocols, hypotheses, algorithms and
    outcomes are unchanged. The integrated uncertainty report follows the
    assumption-aware report; both must precede this extension.
    """
    lines = text.splitlines(keepends=True)
    matches = [i for i,line in enumerate(lines) if line.startswith('ANCHOR = ')]
    if len(matches) != 1:
        raise ValueError('Expected exactly one new-report publication anchor')
    i = matches[0]
    old = ast.literal_eval(lines[i].split('=',1)[1].strip())
    if old not in ('<!-- RELIABILITY_RESEARCH_END -->', '<!-- ASSUMPTION_AWARE_RESEARCH_END -->', LAYOUT_ANCHOR):
        raise ValueError('Unreviewed report anchor')
    lines[i] = 'ANCHOR = '+repr(LAYOUT_ANCHOR)+'\n'
    return ''.join(lines)


def transformed(path: str, original: str) -> str:
    if path == RENDERER:
        return renderer_text(original)
    if path == WORKFLOW:
        return workflow_text(original)
    if path == REPORT:
        return report_layout_text(original)
    raise ValueError('Unreviewed publication mutation')


def main():
    for name in (RENDERER, WORKFLOW, REPORT):
        path = ROOT/name
        path.write_text(transformed(name,path.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    print('Preserved reviewed main renderer and prepared additive, collision-free publication')


if __name__=='__main__':main()
