from __future__ import annotations

import argparse, csv, hashlib, json, math, sys
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
        f"Local aggregate reduction {pct(h2['evaluation_reduction'])}; connected control reduction {pct(h2['connected_mean_reduction'])}.")
    xs=[x['proof_components'] for x in h3['large']]
    files['figures/03_resilience.svg']=svg_lines('H3 | Exact resilience on decomposable proof families',xs,[('certified cost',[x['cost'] for x in h3['large']])],'minimum deletion cost','All analytic large fixtures match the independent closed form.')
    files['figures/04_interval_review.svg']=svg_bar('H4 | Interval-minimax review outcomes',
        ['strict better','ties','worse'],[h4['strict_improvements'],h4['fixtures']-h4['strict_improvements']-h4['worse_than_midpoint'],h4['worse_than_midpoint']], 'fixtures',
        f"Strict minimax improvement on {pct(h4['strict_fraction'])}; 0 oracle discrepancies.")
    xs=[x['n'] for x in h5['large']]
    files['figures/05_hypergraph.svg']=svg_lines('H5 | N-ary versus pairwise-projected repair',xs,
        [('n-ary exact',[x['objective'] for x in h5['large']]),('pairwise projection',[x['pairwise_projection'] for x in h5['large']])], 'retained unit utility',
        'Pairwise clique projection is intentionally over-conservative for three-way-only conflicts.')

    summary=[
        ['hypothesis','result','primary_measure','value','boundary'],
        ['H1','met','factor-state reduction',f"{h1['state_reduction']:.12f}",'counted DP states, not wall-clock'],
        ['H2','met','local evaluation reduction',f"{h2['evaluation_reduction']:.12f}",'connected control saves 0%'],
        ['H3','met','small/large oracle failures','0','supplied lineage and costs only'],
        ['H4','met','strict minimax improvements',str(h4['strict_improvements']),'independent marginals with interval uncertainty'],
        ['H5','met','large exact hypergraph fixtures',str(len(h5['large'])),'supplied n-ary constraints and utility'],
    ]
    files['summary.csv']='\n'.join(','.join(row) for row in summary)+'\n'

    report=f'''# Post-certificate structural extensions for Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Five precommitted controlled extensions were executed after the dependence-aware certificate study. All five frozen **algorithmic** targets were met: bounded induced-width max-sum repair matched exhaustive oracles and solved connected non-bipartite triangle chains through 1,025 vertices; atomic batch delta maintenance matched full recomputation across 640 accepted transactions while reducing counted local derived-node evaluations by {pct(h2['evaluation_reduction'])}; exact query resilience matched 160 exhaustive small oracles and eight large analytic decompositions; interval-minimax review never worsened the frozen worst-case objective and strictly improved {h4['strict_improvements']}/{h4['fixtures']} fixtures ({pct(h4['strict_fraction'])}); and n-ary forbidden-set repair matched all small oracles and retained strictly more supplied utility than a pairwise clique projection on every large three-way-conflict chain. These are structural and decision-theoretic findings. They are not new Jev semantic-accuracy observations, deployment guarantees, or evidence of superiority to an external graph-synthesis system.

## 1. Frozen protocol and evidence boundary

The protocol was committed as `{r['protocol_commit']}` against baseline `{r['baseline_commit']}` before implementation and execution. Seed `{r['seed']}` is an arbitrary reproducibility seed. **Fresh Jev calls: {r['fresh_jev_calls']}. New scientific documents: {r['new_scientific_documents']}.** Existing negative semantic/routing/calibration results motivated this round, so this is exploratory follow-up rather than independent preregistration.

The package-level additions are not worldwide novelty claims. Treewidth-aware dynamic programming, incremental view maintenance, query resilience/deletion propagation, minimax decision rules under imprecise probabilities, and hypergraph/constraint optimization all have prior art. The contribution here is the frozen integration and falsification suite for this repository.

| Hypothesis | Frozen target | Outcome |
|---|---|---|
| H1: induced-width exact conflict optimization | zero small/oracle/permutation failures; solve 8 large width-2 chains; stage all over-width controls; >=90% fewer counted states | **Met** |
| H2: transactional batch delta maintenance | zero snapshot or atomicity failures; >=80% fewer local derived evaluations | **Met** |
| H3: exact query-resilience certificates | zero small oracle/witness failures; solve 8 analytic large fixtures; stage 6 over-cap controls | **Met** |
| H4: interval-minimax query review | zero oracle discrepancies; never worse than midpoint worst case; strict gain on >=20% | **Met** |
| H5: n-ary conflict constraints | zero small oracle/permutation failures; solve 8 large chains; strict utility gain vs pairwise projection; stage controls | **Met** |

“Met” refers only to the predeclared controlled fixture conjunction. These rows must not be pooled into a semantic-success percentage.

## 2. H1 - induced-width exact conflict optimization

A max-sum variable-elimination solver uses a deterministic min-fill order and stages components whose induced width exceeds four or whose materialized state budget exceeds the frozen cap. On 160 seeded 8-16 vertex bounded-width graphs, the solver matches exhaustive maximum-weight compatible-subset objectives with **0 failures** and **0 input-order permutation failures**. Width distribution is {h1['case_width_histogram']}.

For 12-16 vertex fixtures, counted factor states are **{h1['counted_factor_states']:,}** versus **{h1['full_assignment_count']:,}** full assignments, a {pct(h1['state_reduction'])} reduction in this work metric. All eight connected triangle-chain controls from 33 to 1,025 vertices are solved exactly at induced width two. K6-K10 controls stage at widths 5-9. State-count reduction is not a measured CPU or service-latency speedup.

![H1. Counted exact-DP states versus full enumeration.](figures/01_induced_width.svg)

## 3. H2 - transactional batch delta maintenance

Each transaction validates its revision and changes, computes a reverse-dependency closure, evaluates a copy-on-write overlay in topological order, and commits only after every affected derived node succeeds. Across **{h2['accepted_transactions']}** accepted 1-4 primitive transactions on 128 modular DAGs there are **{h2['snapshot_mismatches']} snapshot mismatches** against independent full recomputation. The suite also records {h2['failure_atomic_controls']}/64 injected-evaluation failures, {h2['stale_revision_controls']}/64 stale revisions and {h2['malformed_controls']}/64 malformed updates with no partial state/revision mutation.

Local work falls from {h2['full_recompute_evaluations']:,} full derived-node evaluations to {h2['local_evaluations']:,}, a {pct(h2['evaluation_reduction'])} reduction. Every connected control evaluates all 256 derived nodes, yielding {pct(h2['connected_mean_reduction'])} saving and making the locality boundary explicit. This is in-memory atomic batch behavior, not crash durability or concurrent database isolation.

![H2. Local delta work and connected worst-case control.](figures/02_transactional_delta.svg)

## 4. H3 - exact query-resilience certificates

For monotone DNF lineage, the method computes a minimum-cost evidence deletion set that hits every active proof clause using incidence-component decomposition and bounded branch-and-bound. All **{h3['small_cases']}** small fixtures match exhaustive deletion-subset oracles with valid witnesses. Eight analytic decomposable families from 256 to 2,048 proof components (up to 4,096 atoms) match their closed-form optimum; six connected 19-24 atom controls stage under the frozen component cap.

The output is a robustness margin relative to the supplied proof lineage and removal costs. It does not say that those proofs are factually correct or that their costs are calibrated to real review effort.

![H3. Certified resilience cost across large decomposable proof families.](figures/03_resilience.svg)

## 5. H4 - interval-minimax query review

Point-risk review can be brittle when primitive probabilities are uncertain. The proposed selector chooses two reviews minimizing worst-case expected residual Bernoulli variance across all endpoint combinations of supplied marginal probability intervals. Production query probability uses memoized Shannon recursion; the independent checker enumerates Boolean worlds directly.

Across {h4['fixtures']} non-degenerate fixtures there are **{h4['oracle_discrepancies']} oracle discrepancies** and **{h4['worse_than_midpoint']} cases worse than the midpoint selector** under the same worst-case objective. The minimax selector is strictly better on **{h4['strict_improvements']} fixtures ({pct(h4['strict_fraction'])})**, including {h4['random_strict']} seeded random fixtures and all {h4['engineered_strict']} engineered fragile-midpoint controls. All {h4['degenerate_point_controls']} point-interval controls reduce to the point solution.

This remains conditional on independent primitives; interval robustness is not a dependence certificate or a semantic calibration guarantee.

![H4. Minimax versus midpoint worst-case review outcomes.](figures/04_interval_review.svg)

## 6. H5 - n-ary conflict constraints

Pairwise conflict edges cannot faithfully represent a rule such as “not all three assertions may coexist.” The factor solver is generalized to forbidden hyperedges: a factor rejects only the all-selected assignment for that scope. Pairwise conflict is the arity-two special case.

All **{h5['small_cases']}** weighted small hypergraphs match exhaustive subset optimization with **0 failures** and **{h5['permutation_failures']} permutation failures**. Eight three-consecutive-forbidden chains from 64 through 2,048 vertices match the analytic optimum `n - floor(n/3)`. Pairwise clique projection is deliberately over-conservative: at n=2,048 it retains {h5['large'][-1]['pairwise_projection']} unit utility versus {h5['large'][-1]['objective']} for the n-ary model. All arity-6 through arity-10 over-width controls stage.

![H5. Exact n-ary repair versus pairwise projection.](figures/05_hypergraph.svg)

## 7. Interpretation

This round strengthens a repeated pattern in the package: explicit structure can create large exactness/work-count gains under supplied assumptions, while those gains do not substitute for semantic validation. H1 and H5 broaden tractable repair structure; H2 makes local maintenance atomic across batches; H3 adds a quantitative fragility certificate; H4 replaces a point-risk review objective with a worst-case interval objective. None establishes that Jev extracted the right entities, relations, qualifiers, probabilities, priorities, costs or constraints.

A decisive next semantic study still requires a new source-disjoint corpus, frozen policy before evaluation, independent adjudication, prospective service cost/latency and matched external baselines. No production graph policy changes in this extension.

## 8. Reproducibility

```bash
python -B -m unittest discover -s graph_synthesis/post_certificate/tests -v
python -B -m graph_synthesis.post_certificate.run --check
python -B -m graph_synthesis.post_certificate.report --check
```

`results.json` contains the frozen benchmark outcomes, controls and work counters; `summary.csv` provides a compact result table; the five SVG figures are deterministic renderings of those results. The frozen protocol remains unchanged.
'''
    files['RESULTS.md']=report
    paper=report.replace('](figures/','](../graph_synthesis/post_certificate/figures/')
    files['PAPER_SECTION.md']=paper
    current=f'''{START}\n\n## Five post-certificate structural extensions\n\n[Executed report](graph_synthesis/post_certificate/RESULTS.md), [frozen protocol](graph_synthesis/post_certificate/PROTOCOL.md), [five figures](graph_synthesis/post_certificate/figures/) and the updated full paper. H1-H5 meet their frozen controlled targets. Induced-width repair reduces counted exact-DP states {pct(h1['state_reduction'])} on the measured small subset; transactional local updates reduce counted derived evaluations {pct(h2['evaluation_reduction'])} while the connected control saves 0%; query resilience matches exhaustive/analytic optima; interval-minimax review is strictly better on {h4['strict_improvements']}/{h4['fixtures']} worst-case fixtures and never worse; n-ary repair avoids pairwise over-rejection on all large controls. No fresh Jev calls, independent semantic-accuracy claim, external-system superiority, worldwide novelty claim or production-policy change.\n\n{END}\n'''
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
