"""Narrow, idempotent integration of publication infrastructure; no evidence edits."""
from __future__ import annotations
import ast
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RENDERER = 'graph_synthesis/render_current_paper.py'
WORKFLOW = '.github/workflows/jev-multicall.yml'
MARKERS = r'<!-- [A-Z][A-Z0-9_]*_RESEARCH_(?:START|END) -->'
COMMANDS = ('          python -B -m graph_synthesis.novel_mechanisms.report --update-paper\n'
            '          python -B -m graph_synthesis.novel_mechanisms.regret --report\n')


def renderer_text(text: str) -> str:
    """Replace only the research-marker stripping expression, keeping HTML disabled."""
    lines = text.splitlines(keepends=True)
    matches = [i for i,line in enumerate(lines) if line.lstrip().startswith('markdown = re.sub(')
               and '_RESEARCH_' in line and 'source.read_text' in line]
    if len(matches) != 1:
        raise ValueError('Expected exactly one reviewed marker-stripping line')
    i = matches[0]
    original = lines[i]
    parsed = ast.parse(original.strip())
    call = parsed.body[0].value
    if not isinstance(call,ast.Call) or len(call.args) != 3 or not isinstance(call.args[0],ast.Constant):
        raise ValueError('Unexpected marker-strip expression')
    # Keep every other statement, asset restriction and Markdown setting intact.
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


def transformed(path: str, original: str) -> str:
    if path == RENDERER:
        return renderer_text(original)
    if path == WORKFLOW:
        return workflow_text(original)
    raise ValueError('Unreviewed publication mutation')


def main():
    for name in (RENDERER, WORKFLOW):
        path = ROOT/name
        path.write_text(transformed(name,path.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    print('Prepared marker-only renderer and additive full-rebuild workflow updates')


if __name__=='__main__':main()
