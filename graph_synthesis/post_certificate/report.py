from __future__ import annotations

import argparse, csv, hashlib, io, json, math, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RESULTS=HERE/'results.json'
FIGDIR=HERE/'figures'
START='<!-- POST_CERTIFICATE_RESEARCH_START -->'
END='<!-- POST_CERTIFICATE_RESEARCH_END -->'


def pct(x): return f"{100*x:.2f}%"

def fmt(x):
    if isinstance(x,float): return f"{x:.6g}"
    return str(x)


def svg_bar(title, labels, values, ylabel, note=''):
    W,H=1200,700; ml,mr,mt,mb=120,60,100,150
    pw=W-ml-mr; ph=H-mt-mb
    vmax=max(values) if values else 1
    if vmax<=0: vmax=1
    n=len(values); gap=24; bw=(pw-gap*(n+1))/max(1,n)
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{W/2}" y="48" text-anchor="middle" font-family="sans-serif" font-size="30" font-weight="700">{title}</text>',
         f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="black"/>',
         f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="black"/>']
    for t in range(6):
        y=mt+ph-(ph*t/5); val=vmax*t/5
        out += [f'<line x1="{ml-6}" y1="{y:.1f}" x2="{ml}" y2="{y:.1f}" stroke="black"/>',
                f'<text x="{ml-12}" y="{y+5:.1f}" text-anchor="end" font-family="sans-serif" font-size="18">{val:.3g}</text>']
    for i,(lab,val) in enumerate(zip(labels,values)):
        x=ml+gap+i*(bw+gap); h=ph*val/vmax; y=mt+ph-h
        out += [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="#667085"/>',
                f'<text x="{x+bw/2:.1f}" y="{y-10:.1f}" text-anchor="middle" font-family="sans-serif" font-size="18">{val:.4g}</text>',
                f'<text x="{x+bw/2:.1f}" y="{mt+ph+30:.1f}" text-anchor="middle" font-family="sans-serif" font-size="17">{lab}</text>']
    out += [f'<text x="28" y="{mt+ph/2}" transform="rotate(-90 28 {mt+ph/2})" text-anchor="middle" font-family="sans-serif" font-size="20">{ylabel}</text>']
    if note:
        out += [f'<text x="{W/2}" y="{H-40}" text-anchor="middle" font-family="sans-serif" font-size="16">{note}</text>']
    out.append('</svg>')
    return '\n'.join(out)+'\n'


def svg_lines(title, xs, series, ylabel, note=''):
    W,H=1200,700; ml,mr,mt,mb=120,70,100,150; pw=W-ml-mr; ph=H-mt-mb
    ymax=max(max(vals) for _,vals in series) if series else 1; xmax=max(xs); xmin=min(xs)
    if ymax<=0:ymax=1
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{W/2}" y="48" text-anchor="middle" font-family="sans-serif" font-size="30" font-weight="700">{title}</text>',
         f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="black"/><line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="black"/>']
    dash=['','6,5','2,5','10,4']
    for si,(name,vals) in enumerate(series):
        pts=[]
        for x,v in zip(xs,vals):
            xx=ml+pw*(x-xmin)/(xmax-xmin if xmax!=xmin else 1); yy=mt+ph-ph*v/ymax; pts.append(f'{xx:.1f},{yy:.1f}')
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#344054" stroke-width="4" stroke-dasharray="{dash[si%len(dash)]}"/>')
        out.append(f'<text x="{ml+pw-10}" y="{mt+28+28*si}" text-anchor="end" font-family="sans-serif" font-size="18">{name}</text>')
    for x in xs:
        xx=ml+pw*(x-xmin)/(xmax-xmin if xmax!=xmin else 1)
        out.append(f'<text x="{xx:.1f}" y="{mt+ph+30}" text-anchor="middle" font-family="sans-serif" font-size="16">{x}</text>')
    out.append(f'<text x="28" y="{mt+ph/2}" transform="rotate(-90 28 {mt+ph/2})" text-anchor="middle" font-family="sans-serif" font-size="20">{ylabel}</text>')
    if note: out.append(f'<text x="{W/2}" y="{H-40}" text-anchor="middle" font-family="sans-serif" font-size="16">{note}</text>')
    out.append('</svg>')
    return '\n'.join(out)+'\n'


def generated(r):
    h1,h2,h3,h4,h5=[r[f'H{i}'] for i in range(1,6)]
    files={}
    files['figures/01_induced_width.svg']=svg_bar(
        'H1 | Exact repair work versus full enumeration',
        ['factor states','2^n assignments'],[h1['counted_factor_states'],h1['full_assignment_count']], 'counted states',
        f"Aggregate 12-16 vertex fixtures; reduction {pct(h1['state_reduction'])}. Work count is not wall-clock speedup.")
    files['figures/02_transactional_delta.svg']=svg_bar(
        'H2 | Transactional delta evaluations', ['local delta','full recompute','connected control'],
        [h2['local_evaluations']/h2['accepted_transactions'],256,256], 'derived-node evaluations per transaction',
        f"Local reduction {pct(h2['evaluation_reduction'])}; injected-failure controls {h2['failure_atomic_controls']}/64; connected saving {pct(h2['connected_mean_reduction'])}.")
    xs=[x['proof_components'] for x in h3['large']]
    files['figures/03_resilience.svg']=svg_lines('H3 | Exact resilience on decomposable proof families',xs,[('certified cost',[x['cost'] for x in h3['large']])],'minimum deletion cost',f"Recorded oracle/witness failures: {len(h3['failures'])}. Supplied lineage and costs only.")
    files['figures/04_interval_review.svg']=svg_bar('H4 | Endpoint-scenario review outcomes',
        ['strict better','ties','worse'],[h4['strict_improvements'],h4['fixtures']-h4['strict_improvements']-h4['worse_than_midpoint'],h4['worse_than_midpoint']], 'fixtures',
        f"Endpoint gains: {pct(h4['strict_fraction'])}; discrepancies: {h4['oracle_discrepancies']}. Not continuous interval minimax.")
    xs=[x['n'] for x in h5['large']]
    files['figures/05_hypergraph.svg']=svg_lines('H5 | N-ary versus pairwise-projected repair',xs,
        [('n-ary exact',[x['objective'] for x in h5['large']]),('pairwise projection',[x['pairwise_projection'] for x in h5['large']])], 'retained unit utility',
        'Pairwise clique projection is intentionally over-conservative for three-way-only conflicts.')

    outcomes={f'H{i}':('met' if r[f'H{i}']['primary_target_met'] else 'not met') for i in range(1,6)}
    outcome_sentence='; '.join(f'{key}: {value}' for key,value in outcomes.items())+'.'
    counter=h4['interior_counterexample']
    summary=[
        ['hypothesis','result','primary_measure','value','boundary'],
        ['H1',outcomes['H1'],'factor-state reduction',f"{h1['state_reduction']:.12f}",'counted DP states, not wall-clock'],
        ['H2',outcomes['H2'],'local evaluation reduction',f"{h2['evaluation_reduction']:.12f}",'connected control reported separately'],
        ['H3',outcomes['H3'],'recorded oracle/witness failures',str(len(h3['failures'])),'supplied lineage and costs only'],
        ['H4',outcomes['H4'],'strict endpoint-scenario improvements',str(h4['strict_improvements']),'finite endpoint scenarios; continuous interval claim unsupported'],
        ['H5',outcomes['H5'],'recorded oracle/control failures',str(len(h5['failures'])),'supplied n-ary constraints and utility'],
    ]
    buffer=io.StringIO(newline='')
    csv.writer(buffer,lineterminator='\n').writerows(summary)
    files['summary.csv']=buffer.getvalue()
    report=f'''# Post-certificate structural extensions for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026; corrected September 28, 2026

## Abstract

Five precommitted controlled extensions were executed after the dependence-aware certificate study. Recorded frozen-target outcomes: **{outcome_sentence}** These are separate algorithmic conjunctions, not a pooled success percentage. The experiments address induced-width repair, transactional delta maintenance, query resilience, finite endpoint-scenario review and n-ary conflict constraints. **H4 tests endpoint scenarios only; it does not establish minimax review over continuous probability intervals.** An interior counterexample below rejects that broader interpretation. No new semantic-accuracy observations, deployment guarantees or external-system superiority are established.

## 1. Frozen protocol and evidence boundary

The protocol was committed as `{r['protocol_commit']}` against baseline `{r['baseline_commit']}` before implementation and execution. Its bytes, fixture definitions, caps, seed `{r['seed']}` and thresholds remain unchanged. **Fresh Jev calls: {r['fresh_jev_calls']}. New scientific documents: {r['new_scientific_documents']}.** This is exploratory follow-up, not independent preregistration.

[The correction record](CORRECTIONS.md) distinguishes repaired implementation/control defects from the preserved protocol. H4's frozen Method explicitly specifies interval endpoint vectors; its former broader interval-minimax description is withdrawn. The supplemental negative control is outside the frozen 128-fixture population. Treewidth-aware dynamic programming, incremental view maintenance, query resilience, finite-scenario minimax decisions and hypergraph optimization have prior art; these are repository experiments, not worldwide novelty claims.

| Hypothesis | Frozen target | Recorded outcome |
|---|---|---|
| H1: induced-width repair | zero oracle/permutation failures; solve 8 large chains; stage controls; >=90% fewer counted states | **{outcomes['H1']}** |
| H2: transactional delta | zero snapshot/atomicity failures; >=80% fewer local evaluations | **{outcomes['H2']}** |
| H3: query resilience | zero oracle/witness failures; solve 8 analytic families; stage 6 controls | **{outcomes['H3']}** |
| H4: endpoint-scenario review | zero endpoint-oracle discrepancies; never worse than midpoint on endpoint scenarios; strict gain on >=20% | **{outcomes['H4']}**, endpoint scenarios only |
| H5: n-ary conflicts | zero oracle/permutation failures; solve 8 chains; strict gain vs pairwise projection; stage controls | **{outcomes['H5']}** |

A failed conjunction remains not met regardless of individual favorable endpoints.

## 2. H1 - induced-width exact conflict optimization

The solver computes deterministic min-fill order from the actual graph, checking width and allocation limits before constructing exponential tables. The shortcut based on numeric identifier distance has been removed. Of {h1['small_cases']} small fixtures, {h1['small_solved']} match the exhaustive objective; recorded failures: **{len(h1['failures'])}**; permutation failures: **{h1['permutation_failures']}**. Width distribution: {h1['case_width_histogram']}.

For the frozen 12-16 vertex subset, counted elimination evaluations are **{h1['counted_factor_states']:,}**, versus **{h1['full_assignment_count']:,}** full assignments: **{pct(h1['state_reduction'])} reduction**. This original work counter is not total memory allocation or CPU time; a separate cumulative table-allocation guard enforces the frozen cap. Large triangle chains use an independent prefix dynamic-programming oracle. Per-fixture objectives, widths and staged controls remain in `results.json`.

![H1. Counted exact-DP work versus full enumeration.](figures/01_induced_width.svg)

## 3. H2 - transactional batch delta maintenance

Transactions validate revisions and updates, evaluate an overlay in computed topological order, and return it only after successful evaluation. Unknown dependencies and cycles are rejected. Across **{h2['accepted_transactions']}** accepted transactions, independent full recomputation finds **{h2['snapshot_mismatches']} snapshot mismatches**. A control passes only when the expected exception is raised and original values/revision remain unchanged: injected evaluation **{h2['failure_atomic_controls']}/64**, stale revision **{h2['stale_revision_controls']}/64**, malformed update **{h2['malformed_controls']}/64**. Returned revision mismatches: **{h2['revision_mismatches']}**. The frozen injected-failure conjunction is not met: one selected primitive has no affected derived node, so no failure was injected. That case remains in the denominator; the exact control record is retained in `results.json`.

Local evaluations: {h2['local_evaluations']:,}, versus {h2['full_recompute_evaluations']:,} for full recomputation: **{pct(h2['evaluation_reduction'])} reduction**. Connected controls separately show **{pct(h2['connected_mean_reduction'])} mean saving**. These are in-memory atomic batches, not crash durability or concurrent database isolation.

![H2. Local work and connected-control boundary.](figures/02_transactional_delta.svg)

## 4. H3 - exact query-resilience certificates

For supplied monotone DNF lineage and removal costs, incidence decomposition and bounded branch-and-bound find a minimum-cost deletion set hitting each active proof clause. **{h3['small_solved']}/{h3['small_cases']}** small fixtures match the exhaustive oracle. Recorded oracle, witness or control failures: **{len(h3['failures'])}**. All {len(h3['large'])} analytic-family results and {len(h3['controls'])} over-cap controls are retained. This is conditional structural resilience, not factual truth or calibrated review effort.

![H3. Recorded resilience cost in decomposable families.](figures/03_resilience.svg)

## 5. H4 - endpoint-scenario query review

The selector minimizes worst-case expected residual Bernoulli variance **over the finite Cartesian product of interval endpoints**, with two reviews. Production uses Shannon recursion; the independent checker enumerates Boolean worlds over the same endpoint scenarios. Neither searches interval interiors.

Across {h4['fixtures']} frozen fixtures, endpoint-oracle discrepancies: **{h4['oracle_discrepancies']}**; cases worse than midpoint on endpoint scenarios: **{h4['worse_than_midpoint']}**. Strict endpoint gains: **{h4['strict_improvements']}/{h4['fixtures']} ({pct(h4['strict_fraction'])})**, comprising {h4['random_strict']} random and {h4['engineered_strict']} engineered fixtures. Point-interval controls pass **{h4['degenerate_point_controls']}/16**.

**Continuous-interval claim: unsupported.** For singleton queries with intervals `0=[0.1,0.9]`, `1=[0.3,0.4]`, `2=[0.5,0.5]`, the supplemental control selects reviews {counter['endpoint_selected']} and reports endpoint worst loss {counter['endpoint_worst']:.6g}. The allowed interior witness `p0=0.5` yields **{counter['interior_loss']:.6g}**. Reviewing {counter['alternative_review']} has analytic continuous worst loss **{counter['alternative_continuous_worst']:.6g}**. The endpoint choice is therefore not continuous-interval minimax. This negative evidence is separate from the preserved endpoint target. Independent primitives are assumed; no dependence or semantic-calibration guarantee follows.

![H4. Endpoint-scenario outcomes only; continuous interval claim unsupported.](figures/04_interval_review.svg)

## 6. H5 - n-ary conflict constraints

A forbidden hyperedge rejects only its all-selected assignment; pairwise conflict is the arity-two case. **{h5['small_solved']}/{h5['small_cases']}** small fixtures match exhaustive optimization; recorded failures: **{len(h5['failures'])}**; permutation failures: **{h5['permutation_failures']}**. Eight chains compare against `n - floor(n/3)`, with objectives and staging controls retained. At the largest chain, retained n-ary utility is **{h5['large'][-1]['objective']}**, versus **{h5['large'][-1]['pairwise_projection']}** under deliberately over-conservative pairwise projection.

![H5. N-ary repair versus pairwise projection.](figures/05_hypergraph.svg)

## 7. Interpretation

Every result is conditional on supplied graphs, lineage, costs, constraints or finite probability scenarios. Work counters do not measure wall-clock/API latency or cloud cost. The H4 interior counterexample rejects the broader interval-minimax interpretation. None establishes correct extracted entities, relations, qualifiers or probabilities. No production graph policy changes here.

## 8. Reproducibility

```bash
python -B -m unittest discover -s graph_synthesis/post_certificate/tests -v
python -B -m graph_synthesis.post_certificate.run --check
python -B -m graph_synthesis.post_certificate.report --check --update-paper
```

`results.json` retains outcomes and controls; `summary.csv` and five SVGs derive from those measurements. Manual validation also checks protocol ancestry/bytes, archive integrity, deterministic HTML and current-paper build hashes. The correction record documents implementation and interpretation changes; the frozen protocol is unchanged.
'''
    files['RESULTS.md']=report
    paper=report.replace('](figures/','](../graph_synthesis/post_certificate/figures/')
    paper=paper.replace('](CORRECTIONS.md)','](../graph_synthesis/post_certificate/CORRECTIONS.md)')
    files['PAPER_SECTION.md']=paper
    current=f'''{START}\n\n## Five post-certificate structural extensions\n\n[Executed report](graph_synthesis/post_certificate/RESULTS.md), [frozen protocol](graph_synthesis/post_certificate/PROTOCOL.md), [corrections](graph_synthesis/post_certificate/CORRECTIONS.md), and [five figures](graph_synthesis/post_certificate/figures/). Recorded target outcomes: **{outcome_sentence}** H4 covers only endpoint scenarios; its broader continuous-interval minimax claim is unsupported, with an interior counterexample retained. Counted H1 reduction: {pct(h1['state_reduction'])}; local H2 reduction: {pct(h2['evaluation_reduction'])}, connected-control saving: {pct(h2['connected_mean_reduction'])}. No fresh Jev calls, independent semantic-accuracy claim, external-system superiority or production-policy change.\n\n{END}\n'''
    files['CURRENT_SNIPPET.md']=current
    return files


def replace_block(text, block):
    if START in text:
        before,rest=text.split(START,1)
        if END not in rest: raise ValueError('unterminated post-certificate block')
        _,after=rest.split(END,1)
        return before+block+after.lstrip('\n')
    return text.rstrip()+"\n\n"+block


def paper_block(section):
    return START+'\n\n'+section.rstrip()+'\n\n'+END+'\n'


def write_generated(check=False, update_paper=False):
    r=json.loads(RESULTS.read_text(encoding='utf-8'))
    files=generated(r); mismatches=[]
    for rel,content in files.items():
        path=HERE/rel
        if check:
            if not path.exists() or path.read_text(encoding='utf-8')!=content: mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8',newline='\n')
    if update_paper:
        current_path=ROOT/'CURRENT_RESULTS.md'; paper_path=ROOT/'manuscript/paper-current.md'
        current=replace_block(current_path.read_text(encoding='utf-8'),files['CURRENT_SNIPPET.md'])
        pblock=paper_block(files['PAPER_SECTION.md'])
        paper=replace_block(paper_path.read_text(encoding='utf-8'),pblock)
        if check:
            if current_path.read_text(encoding='utf-8')!=current: mismatches.append('CURRENT_RESULTS.md')
            if paper_path.read_text(encoding='utf-8')!=paper: mismatches.append('manuscript/paper-current.md')
        else:
            current_path.write_text(current,encoding='utf-8',newline='\n'); paper_path.write_text(paper,encoding='utf-8',newline='\n')
    if mismatches:
        print('generated output mismatch: '+', '.join(mismatches),file=sys.stderr); return 2
    return 0


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); ap.add_argument('--update-paper',action='store_true'); args=ap.parse_args(argv)
    return write_generated(args.check,args.update_paper)

if __name__=='__main__': raise SystemExit(main())
