"""Build the reader's map of the cumulative, independently generated studies."""

from __future__ import annotations

import re
from dataclasses import dataclass


START = '<!-- MANUSCRIPT_NAVIGATION_START -->'
END = '<!-- MANUSCRIPT_NAVIGATION_END -->'


@dataclass(frozen=True)
class Study:
    title: str
    protocol: str
    evidence: str
    result: str
    date: str = '2026-09-18'


# Listed in manuscript order. Every title and protocol heading is validated
# against the actual manuscript before the map is written.
STUDIES = (
    Study('Adaptive verification and joint conflict resolution for Jev graph synthesis', 'Research question and provenance', 'Saved responses; simulated review; controlled graphs', 'Routing misses its cost target; fallback adds wrong edges; controlled review and optimization meet targets.'),
    Study('Risk control, targeted verification and structural tractability in Jev graph synthesis', '1. Motivation, scope and provenance', 'Saved responses; controlled graphs', 'Four primary targets fail; forest optimization meets its controlled target.'),
    Study('Reliability, evidence lineage and incremental structure in Jev graph synthesis', '1. Motivation and protocol', 'Saved responses; simulated review; controlled algorithms', 'Reliability calibration misses; four controlled targets meet.'),
    Study('Reliability ranking, source diversity and bounded exact inference for Jev graph synthesis', '1. Research motivation and evidence boundary', 'Saved responses; simulated review; controlled algorithms', 'Ranking, diversity and review miss targets; two exact structural targets meet.'),
    Study('Source risk, review budgets and structural certificates for Jev graph synthesis', '1. Research questions and frozen evaluation', 'Saved responses; simulated review; controlled algorithms', 'Source risk and review miss; three structural targets meet.'),
    Study('Assumption-aware graph synthesis: five falsifiable follow-up experiments', '1. Motivation, scope and novelty boundary', 'Controlled algorithms and decision models', 'Lineage and review miss; three controlled targets meet.'),
    Study('Uncertainty, repair ambiguity and grounded evidence in Jev graph synthesis', '1. Research question, prior evidence and novelty boundary', 'Controlled algorithms and decision models', 'Five controlled targets meet; no new semantic evaluation.'),
    Study('Five initial hypotheses: distinct additions and concurrent replication', '1. Motivation, novelty scope and protocol', 'Saved responses; controlled algorithms', 'Label shift misses; four controlled targets meet; one overlaps concurrent work.'),
    Study('Interval-priority regret: fifth distinct addition after concurrent overlap', 'Hypothesis and falsification', 'Controlled interval optimization', 'Regret target meets on controlled fixtures; no semantic validation.'),
    Study('Structural frontiers for evidence-preserving Jev graph synthesis', '1. Motivation, novelty scope and frozen design', 'Controlled algorithms and decision models', 'Review misses; four structural targets meet.'),
    Study('Dependence-aware certificates for Jev graph synthesis', '1. Motivation, novelty boundary and frozen methodology', 'Saved responses; controlled algorithms', 'Forecasting misses; four controlled targets meet, with documented overlap.'),
    Study('Five post-certificate improvements for Jev graph synthesis', '1. Frozen methodology and novelty boundary', 'Saved responses; controlled algorithms', 'Source-risk stacking misses; four controlled targets meet.'),
    Study('Do additional Jev calls improve graph edges?', 'Design and evidence boundary', '3,024 fresh Jev calls', 'No added-call policy establishes a matched-volume advantage.'),
    Study('Fresh Jev execution and graph-synthesis falsification', 'Evidence scope', 'Fresh same-data Jev repeat; synthetic challenge', 'Original entity improvement is unresolved on fresh macro-F1 interval.'),
    Study('Follow-up: five evidence-driven improvements', 'Summary of fixed operational targets', 'Saved responses; controlled algorithms', 'Mixed target outcomes; no independent semantic validation.'),
    Study('Original study (historical evidence; unchanged text)', '3. Research questions and scope', 'Original Jev calls; cached replay', 'Positive entity-matching result on original split; relation gain inconclusive.'),
)


def heading_id(title: str) -> str:
    """Use the same simple, stable ASCII fragment in Markdown and rendered HTML."""
    return re.sub(r'[^a-z0-9\- ]', '', title.lower()).replace(' ', '-')


def assign_heading_anchors(tokens):
    """Assign GitHub-style duplicate suffixes and return ordered heading records."""
    used = set()
    records = []
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        title = tokens[index + 1].content
        slug = heading_id(title)
        if not slug:
            raise ValueError('Empty manuscript heading anchor')
        unique = slug
        suffix = 1
        while unique in used:
            unique = f'{slug}-{suffix}'
            suffix += 1
        token.attrSet('id', unique)
        used.add(unique)
        records.append((token.tag, title, unique))
    return records


def _study_anchors(text: str):
    from markdown_it import MarkdownIt

    tokens = MarkdownIt('commonmark', {'html': False}).enable('table').parse(text)
    records = assign_heading_anchors(tokens)
    positions = []
    for study in STUDIES:
        matches = [i for i, (tag, title, _) in enumerate(records) if tag == 'h1' and title == study.title]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one study title: {study.title}')
        positions.append(matches[0])
    if positions != sorted(positions):
        raise ValueError('Study order changed')
    anchors = []
    for index, study in enumerate(STUDIES):
        section = records[positions[index] + 1:positions[index + 1] if index + 1 < len(positions) else None]
        protocols = [anchor for _, title, anchor in section if title == study.protocol]
        if len(protocols) != 1:
            raise ValueError(f'Expected one protocol heading in study: {study.title}')
        anchors.append((records[positions[index]][2], protocols[0]))
    return anchors


def update_navigation(text: str) -> str:
    """Replace only the generated map, preserving every research section byte."""
    if (START in text) != (END in text):
        raise ValueError('Unbalanced manuscript navigation markers')
    if START in text:
        if text.count(START) != 1 or text.count(END) != 1:
            raise ValueError('Duplicate manuscript navigation markers')
        before, remainder = text.split(START, 1)
        _, after = remainder.split(END, 1)
        text = before + after.lstrip('\n')
    if text.lstrip().startswith('# ') or not text.lstrip().startswith('<!--'):
        raise ValueError('Unexpected manuscript opening before study sections')
    rows = []
    for study, (study_anchor, protocol_anchor) in zip(STUDIES, _study_anchors(text)):
        title_link = f'[{study.title}](#{study_anchor})'
        protocol_link = f'[Protocol and scope](#{protocol_anchor})'
        rows.append(f'| {title_link}; {protocol_link} | {study.evidence} | {study.result} | {study.date} |')
    map_text = '\n'.join((
        '# Jev graph synthesis: current research map',
        '',
        'This cumulative author-review draft preserves separate studies and the original manuscript. The latest fresh same-data repeat did not resolve the original entity-matching macro-F1 improvement; the later saved-response and controlled results are exploratory and do not establish independent semantic generalization. No study here validates unattended graph writes.',
        '',
        '## Study directory',
        '',
        'Each entry links to its study and its in-document protocol or evidence boundary. Dates refer to the recorded study drafts. “Controlled” means supplied fixtures or simulated decisions, not new Jev service observations.',
        '',
        '| Study and protocol | Evidence type | Main result and limit | Date |',
        '|---|---|---|---|',
        *rows,
        '',
        '## Reading the evidence',
        '',
        'The [fresh repeat](#fresh-jev-execution-and-graph-synthesis-falsification) and [multicall study](#do-additional-jev-calls-improve-graph-edges) contain new service calls. Later studies mostly replay saved responses or test controlled algorithms; their target passes do not measure new semantic accuracy. The [historical original study](#original-study-historical-evidence-unchanged-text) reports the initial fixed-split improvement. See [current results](../CURRENT_RESULTS.md) for the chronological record and the linked protocols and reports.',
    ))
    return START + '\n\n' + map_text + '\n\n' + END + '\n\n' + text.lstrip('\n')
