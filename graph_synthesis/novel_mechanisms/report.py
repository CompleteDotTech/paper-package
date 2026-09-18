"""Generate an evidence-linked report, five separate figures and additive paper section."""
from __future__ import annotations
import argparse
import csv
import json
import re
from .run import HERE, ROOT, sha, write

START = '<!-- NOVEL_MECHANISMS_RESEARCH_START -->'
END = '<!-- NOVEL_MECHANISMS_RESEARCH_END -->'
ANCHOR = '<!-- UNCERTAINTY_RESEARCH_END -->'
TITLES = ['Unlabeled label-shift correction','Dependence-robust lineage certificates','Protected-fact minimal repair','Bipartite conflict optimization','Indexed interval conflict construction']
STEMS = ['01_label_shift','02_dependence_bounds','03_minimal_repair','04_bipartite_capacity','05_indexed_conflicts']


def interval(values):
    return '['+', '.join(f'{100*v:+.3f}' for v in values)+'] pp'


def render(r):
    a,b,c,d,e = [r[f'H{i}'] for i in range(1,6)]
    status = lambda h: 'Met' if h['primary_target_met'] else 'Not met'
    sparse=e['sparse'][-1]
    text = ['# Five new mechanisms for evidence-preserving Jev graph synthesis','',
        'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026','',
        '## Abstract','',
        f"Five mechanisms not previously tested in this repository are evaluated under a protocol committed before execution. Unlabeled label-shift correction ties the single-view baseline at {a['matched_k']} emitted edges: both produce {a['matched']['baseline']['wrong']} errors, missing the frozen 20% reduction target. Dependence-robust lineage bounds prevent a false independence-based admission in a correlated-source control, at the cost of wider uncertainty intervals. Protected-fact repair improves on greedy intervention in {c['improved_cases']}/{c['feasible_cases']} feasible seeded fixtures. Bipartite min-cut optimization certifies the supplied-priority optimum in five dense components that the earlier cutset solver stages. Indexed conflict construction reduces semantic pair checks from {sparse['baseline_checks']:,} to {sparse['indexed_checks']:,} on 2,048 sparse assertions, with identical edges. These are exploratory saved-response and controlled algorithm results, not new Jev semantic observations or evidence of superiority to KARMA.",'',
        '## 1. Motivation, novelty scope and protocol','',
        'The [latest reliability extension](../reliability/RESULTS.md) exposed failed source-risk calibration, a false primitive-independence assumption, bounded cyclic-graph solving and global preprocessing excluded from solver-only incremental savings. The [frozen protocol](PROTOCOL.md) maps each new mechanism to the closest earlier experiment. Novelty means untried in the audited repository snapshot, not invented here or never attempted worldwide. Label-shift adaptation, probability bounds, hitting-set search, flow/cover duality and interval sweeps are established ideas; the contribution is this testable integration and its limitations.','',
        f"The protocol commit is `{r['protocol_commit']}`; the baseline is `{r['baseline_commit']}`. H1 reuses {r['development']['n']} development cases in {r['development']['groups']} source groups and {r['test']['n']} evaluation cases in {r['test']['groups']} groups. These previously inspected evaluation data are not a fresh holdout. Authentic raw responses are reconstructed and hashes, IDs and source-group separation checked before scoring. **Fresh service calls: {r['fresh_service_calls']}.** H2-H5 use supplied controlled inputs, not model-produced facts. No production graph policy or default compiler changes; the original evidence archive remains unchanged.",'',
        '| Hypothesis | Frozen primary requirement | Outcome | Evidence |','|---|---|---|---|']
    criteria = ['Retain >=98% of naturally correct edges and reduce matched-volume errors >=20%',
                'No false certified admission or excluded truth; analytic agreement; prevent one independence error',
                'Oracle agreement, no greedy cost regression, improve >=5% of feasible cases',
                'Oracle agreement, no previous-policy regression, solve every large bipartite fixture',
                'Exact edge/staging parity and >=95% fewer sparse pair checks']
    classes = ['Previously captured Jev responses','Supplied marginal and joint probabilities','Supplied proofs, protections and costs','Supplied conflict graphs and priorities','Supplied typed interval assertions']
    for i in range(1,6): text.append(f'| H{i}: {TITLES[i-1]} | {criteria[i-1]} | {status(r[f"H{i}"])} | {classes[i-1]} |')
    text += ['','A target pass is a conjunction of engineering requirements, not a significance test. Do not pool the five outcomes into a semantic success percentage.','',
        '## 2. H1: Unlabeled label-shift correction','',
        'We fit a three-class hard-prediction confusion matrix on development labels, with one pseudo-count per predicted class in each true-class column. Source priors receive one pseudo-count per class. Target priors q minimize ||Cq-m|| squared + 0.01 ||q-p_source|| squared on the simplex; m uses only valid unlabeled target predictions. Enumerating all nonempty simplex faces avoids a local-search stopping criterion. Valid base1 probabilities are multiplied by q/p_source and normalized. Operational failures remain failures. Rank deficiency returns the unchanged predictor. This regularized BBSE-inspired method is not an exact reproduction of [Lipton, Wang and Smola (2018)](https://proceedings.mlr.press/v80/lipton18a.html), nor a guarantee of calibrated posteriors.','',
        '| Policy and volume | Emitted | Correct | Wrong | Precision | Recall over all 153 gold-positive candidates |','|---|---:|---:|---:|---:|---:|']
    for name,key,kind in [('Single view, natural','baseline','natural'),('Corrected, natural','proposed','natural'),('Single view, matched','baseline','matched'),('Corrected, matched','proposed','matched')]:
        v=a[kind][key];text.append(f"| {name} | {v['accepted']} | {v['correct']} | {v['wrong']} | {v['precision']:.2%} | {v['recall']:.2%} |")
    text += ['',f"Natural volume adds three correct edges and two wrong edges. At matched k={a['matched_k']}, the primary error-reduction target is **{status(a).lower()}**. Both policies retain one operational failure in the full 263-candidate denominator. The same {a['recorded_input_tokens']:,} recorded input tokens are charged to each policy, including failed requests. No extra inference calls or invented monetary savings are claimed.",'',
        '| Class | Development prior (smoothed) | Estimated target prior | Observed valid-target prior (evaluation only) |','|---|---:|---:|---:|']
    for i,label in enumerate(('SUPPORTS','REFUTES','NOT_ENOUGH_INFO')):
        text.append(f"| {label} | {a['fit']['source_prior'][i]:.4f} | {a['fit']['target_prior'][i]:.4f} | {a['observed_valid_test_prior'][i]:.4f} |")
    text += ['',f"There are {a['fit']['valid_target']} valid target outputs. Target gold labels never enter fitting or reweighting; the observed prior is a diagnostic only. With fixed fit and selected ID sets, the paired source-group bootstrap gives corrected-minus-baseline precision intervals of {interval(a['bootstrap']['precision']['95'])} (95%) and {interval(a['bootstrap']['precision']['99'])} (99%). Wrong edges per candidate have intervals {interval(a['bootstrap']['wrong_edge_rate']['95'])} and {interval(a['bootstrap']['wrong_edge_rate']['99'])}. These descriptive, non-simultaneous intervals use {r['bootstrap_draws']:,} draws, seed {r['seed']}; they omit fitting uncertainty and do not repair evaluation-set reuse.",'',
        f"The known-confusion control has prior L1 error {a['controls'][0]['l1_prior_error']:.6f}; changing the target conditional confusion increases it to {a['controls'][1]['l1_prior_error']:.6f}. Marginal adaptation is therefore not a remedy for arbitrary conditional shift or semantic errors.",'',
        '![H1. Wrong emitted edges at natural and matched volume; lower is better.](figures/01_label_shift.png)','',
        '## 3. H2: Dependence-robust lineage certificates','',
        'A fact is a disjunction of conjunctive proofs. Instead of multiplying primitive marginals, enumerate Boolean worlds for at most eight atoms and constrain their nonnegative joint masses to match the supplied marginals and sum to one. Two linear programs minimize and maximize the fact indicator. We use [SciPy linear programming](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html), but do not trust a numerical success flag as a safety certificate: dual coefficients are converted to rational numbers, each inequality is checked over every world, and the constant is shifted outward if needed. Rational lower-bound comparison, not rounded display values, governs the 0.95 admission gate. Caps and solver failures return explicit conservative Frechet/union bounds. Certified bounds need not be numerically sharp on every input.','',
        f"Across {len(b['fixtures'])} seeded arbitrary joint-distribution fixtures, {b['interval_exclusions']} certified intervals exclude supplied truth and {b['false_admissions']} false lower-bound admissions occur. The {len(b['analytical'])} two-atom analytical AND/OR cases have {b['analytical_failures']} endpoint failures at tolerance 1e-8, with {b['invariance_failures']} duplicate/order failures. The controlled target is **{status(b).lower()}**. Mean interval width is {b['mean_width']:.6f}; this additional uncertainty is the price of removing independence, not a defect to hide.",'',
        f"At the 0.95 gate, the independence-assuming evaluator admits {sum(row['independent']['lower'] >= .95 for row in b['fixtures'])}/{len(b['fixtures'])} random fixtures and the dependence-robust method admits {sum(row['proposed']['admit_095'] for row in b['fixtures'])}/{len(b['fixtures'])}. Thus the random fixtures test interval validity, not useful acceptance coverage. The explicit correlated-source control below supplies the prevented-admission contrast. The zero random false-admission count must not be presented as evidence of high-coverage deployment safety.",'',
        '| Correlated-source control | Probability or interval | Admitted at 0.95? |','|---|---:|---|',
        '| Independence-assuming evaluator | 0.96 | Yes, incorrectly |','| Dependence-robust certificate | [0.80, 1.00] | No |','| Actual supplied joint truth | 0.80 | Below threshold |','',
        'The control contains two distinct primitive events that are perfectly correlated, each with marginal 0.8. The robust bound prevents the old false admission, but cannot certify an edge whose real dependence is unknown. Conversely, supplying a false marginal of 0.99 for an event whose actual probability is 0.8 still causes an incorrect admission. Certificates are conditional on correct marginals and proof semantics. Jev scores are not established truth marginals; TypeSafe probability outputs do not by themselves establish this assumption ([documentation](https://docs.typesafe.ai/introduction)).','',
        '![H2. Removing primitive independence prevents an unsupported admission, but widens the interval.](figures/02_dependence_bounds.png)','',
        '## 4. H3: Protected-fact minimal source repair','',
        'Instead of propagating a predetermined source withdrawal, the algorithm chooses a minimum-cost set intersecting every target proof while preserving at least one intact proof of each designated protected fact. It branches on an unhit target proof, prunes destroyed protections and dominated costs, and breaks ties by the sorted withdrawal tuple. A 16-atom and 65,536-state cap prevents an unfinished search from masquerading as an optimum: exhaustion stages the request. No sources are actually deleted.','',
        f"An independent exhaustive subset oracle evaluates {len(c['fixtures'])} seeded eight-atom fixtures. There are {c['feasible_cases']} feasible cases and {len(c['fixtures'])-c['feasible_cases']} infeasible cases; feasibility, protection and optimum checks have {c['oracle_failures']} mismatches. Compared with cost-normalized greedy coverage that respects the same protections, {c['improved_cases']}/{c['feasible_cases']} feasible cases ({c['improved_fraction']:.2%}) have strictly lower cost or recover from a greedy dead end, exceeding the frozen 5% target. There are {c['cost_regressions']} cost regressions where greedy completes. The controlled target is **{status(c).lower()}**.",'',
        f"The improvements separate into {sum(row['oracle']['status']=='optimal' and row['greedy']['status']=='feasible' and row['proposed']['cost'] < row['greedy']['cost'] for row in c['fixtures'])} strictly cheaper completed repairs and {sum(row['oracle']['status']=='optimal' and row['greedy']['status']!='feasible' for row in c['fixtures'])} recoveries from greedy dead ends. These outcomes are not additional fixtures.",'',
        'The fixed greedy trap withdraws a,b,c at cost 6, whereas the exact solution withdraws b,c at cost 4. A protected fact identical to the target makes repair infeasible; the algorithm refuses to silently sacrifice the protection. Costs are supplied positive integer units, not dollars or observed reviewer effort. Protected facts are designated by the fixture, not independently proven true.','',
        '![H3. Exact repair improves a subset of feasible cases; infeasible cases remain explicit.](figures/03_minimal_repair.png)','',
        '## 5. H4: Bipartite min-cut conflict optimization','',
        'For each bipartite component up to 256 vertices, a source/sink network computes minimum-weight vertex cover; its complement is a maximum-weight conflict-free assertion set. Cross-edge capacities exceed total priority. Integer max flow, cut capacity, cover membership and positive edge flows form a checkable objective certificate. Nonbipartite graphs retain the actual previous cutset/enumeration/staging implementation. This exploits a different tractable graph family rather than increasing an exponential search cap.','',
        f"Across {len(d['fixtures'])} small weighted bipartite fixtures and {len(d['general_controls'])} general-graph controls, plus five analytical large cases, there are {d['oracle_failures']} oracle failures and {d['utility_regressions']} utility regressions against the previous solver. Duplicate/direction/order checks have {d['invariance_failures']} failures. The controlled target is **{status(d).lower()}**.",'',
        '| Complete bipartite graph | Vertices | Prior cutset utility | Priority-greedy utility | Flow utility | Analytic optimum |','|---|---:|---:|---:|---:|---:|']
    for row in d['large']:text.append(f"| K({row['left']},{row['right']}) | {row['vertices']} | {row['previous']['utility']} | {row['greedy']['utility']} | {row['proposed']['utility']} | {row['oracle']} |")
    text += ['','Left priorities are 2 and right priorities 3. Priority greedy also reaches the optimum on these large fixtures: the result is expanded certified coverage relative to the previous bounded solver, not superiority over every heuristic. A dense 17-clique still stages. A conflicting false assertion with priority 9 defeats a true assertion with priority 8: structural consistency and optimal supplied utility do not establish factual truth.','',
        '![H4. Dense bipartite components are solved beyond the prior cutset staging boundary.](figures/04_bipartite_capacity.png)','',
        '## 6. H5: Indexed interval conflict construction','',
        'Assertions are validated, partitioned by subject/predicate/scope, sorted by start time and swept with an expiry heap. Half-open intervals expire when end <= next start; None endpoints remain unbounded. Only simultaneously active assertions within a partition need semantic collision tests. Unsupported qualifiers stage, and duplicate or missing IDs are rejected. The baseline calls the existing pairwise conflict predicate on all supported pairs, including its per-pair validation. The indexed route validates once and hoists those repeated checks; both differences can affect runtime.','',
        f"The {len(e['fixtures'])} random cases include bounded/unbounded intervals, scope separation, opposing polarity, functional collisions and malformed qualifiers. There are {e['pairwise_failures']} edge/staging mismatches, {e['integer_oracle_failures']} failures against independent finite-instant truth, and {e['invariance_failures']} order failures. The controlled target is **{status(e).lower()}**.",'',
        '| Workload | Rows | Pairwise checks | Indexed checks | Identical conflict edges | Pair-check reduction |','|---|---:|---:|---:|---:|---:|']
    for name,row in [('Sparse',x) for x in e['sparse']]+[('Dense control',e['dense'])]:
        text.append(f"| {name} | {row['n']} | {row['baseline_checks']:,} | {row['indexed_checks']:,} | {row['edge_count']:,} | {row['saving']:.4%} |")
    text += ['','Validation still visits every assertion; partitioning and sorting remain necessary, with O(n log n) comparison sorting overall. Active-pair work remains quadratic for mutually overlapping same-key assertions, and explicit output itself can be quadratic. The measured pair-check reduction is not an inferred end-to-end speedup.','']
    timing_path=HERE/'timings.json'
    if timing_path.exists():
        t=json.loads(timing_path.read_text(encoding='utf-8'))
        text += ['### Separately measured construction runtime','',
            f"Five alternating-order elapsed-time repeats per method were run on `{t['platform']}`, Python {t['python'].split()[0]}, NumPy {t['numpy']}, SciPy {t['scipy']}. Medians below include validation, grouping/sorting, collision tests and edge-list construction; input generation and I/O are excluded. These host-specific measurements are stored separately from deterministic result replay.",'',
            '| Workload | Pairwise median (s) | Indexed median (s) |','|---|---:|---:|']
        for row in t['results']:text.append(f"| {row['workload']} | {row['median_seconds']['pairwise']:.6f} | {row['median_seconds']['indexed']:.6f} |")
        text += ['','Dense-case timing differences include hoisted validation and reduced Python overhead, not fewer pairs or subquadratic behavior. These are not service latency, database I/O or universally transferable speedup estimates.','']
    text += ['![H5. Sparse construction avoids irrelevant pairs; the dense control does not.](figures/05_indexed_conflicts.png)','',
        '## 7. Interpretation and remaining falsification','',
        'The semantic adaptation target failed despite a plausible development-to-target prior shift. Therefore, this evidence does not justify changing the default Jev decision rule. In contrast, the controlled tests identify distinct opt-in engineering paths: represent dependence uncertainty rather than manufacture confidence; optimize a proposed repair while honoring explicit protections; recognize bipartite conflict structure before falling back to bounded generic solving; and index conflict construction rather than report solver-only savings.','',
        'The structural passes remain conditional. Incorrect marginals, incomplete proofs, mistaken protections, false priorities and erroneous scope/interval qualifiers can invalidate semantic conclusions even when every algorithm is correct. Results do not measure candidate generation, novel entity discovery, independent source truth, actual reviewer behavior, production database concurrency, or comparative end-to-end graph quality. A policy frozen before a new source-disjoint independently adjudicated corpus, with matched evidence and resource budgets against an external system such as KARMA, remains unexecuted by this extension.','',
        '## 8. Reproducibility and evidence preservation','',
        '```bash','python -m pip install -r graph_synthesis/novel_mechanisms/requirements.txt',
        'python -B -m graph_synthesis.novel_mechanisms.run --timings',
        'python -B -m unittest discover -s graph_synthesis/novel_mechanisms/tests -v',
        'python -B -m graph_synthesis.novel_mechanisms.run --check',
        'python -B -m graph_synthesis.novel_mechanisms.report --figures --update-paper',
        'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf','```','',
        'The results preserve per-candidate predictions and selections, fitted priors, arbitrary joint tables, rational dual certificates, proof/repair fixtures, solver certificates, interval assertions, finite oracles and SHA-256 inputs. Replay disables network connections and uses the existing disclosed narrow numeric comparison tolerance; exact rational certificate strings are retained. Timings are not replay-equality claims. Five SVG/PNG pairs and summary.csv are generated from recorded results. The extension manifest binds its files; the shared manuscript uses its own build manifest. Current-paper insertion is additive and idempotent, retaining all earlier studies and limitations.','']
    return '\n'.join(text)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    matplotlib.rcParams['svg.hashsalt']='jev-novel-mechanisms-20260918'
    folder=HERE/'figures';folder.mkdir(exist_ok=True)
    def save(fig,index,note):
        fig.text(.10,.02,note,fontsize=9,va='bottom')
        fig.tight_layout(rect=(0,.13,1,1))
        fig.savefig(folder/(STEMS[index]+'.png'),dpi=200,metadata={'Software':'paper-package novel-mechanisms report'})
        fig.savefig(folder/(STEMS[index]+'.svg'),metadata={'Date':None,'Creator':'paper-package novel-mechanisms report'})
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H1'];x=np.arange(2)
    for offset,key,label in [(-.18,'baseline','Single view'),(.18,'proposed','Prior corrected')]:
        bars=ax.bar(x+offset,[h[k][key]['wrong'] for k in ('natural','matched')],.36,label=label);ax.bar_label(bars)
    ax.set(xticks=x,xticklabels=['Natural acceptance volume','Matched volume: 150 edges'],ylim=(0,24),ylabel='Wrong emitted edges',title='H1 | Prior correction does not reduce matched-volume errors');ax.legend()
    save(fig,0,'Natural counts: 132 correct / 18 wrong vs 135 correct / 20 wrong.\nMatched counts: both 132 correct / 18 wrong. Reused evaluation data.')
    fig,ax=plt.subplots(figsize=(8.5,4.8))
    ax.plot([.96],[2],marker='o',linestyle='none',label='Independence-assuming point estimate')
    ax.errorbar([.90],[1],xerr=[[.1],[.1]],fmt='none',capsize=8,label='Certified interval (no point estimate)')
    ax.axvline(.8,linestyle=':',label='Actual correlated truth: 0.80')
    ax.axvline(.95,linestyle='--',label='Admission threshold: 0.95')
    ax.set(yticks=[1,2],yticklabels=['Dependence-robust\ncertificate','Independence-assuming\nestimate'],xlim=(.72,1.03),ylim=(.5,3.4),xlabel='Fact probability',title='H2 | Correct marginals do not imply independent sources');ax.legend(loc='upper left')
    save(fig,1,'Controlled OR of two perfectly correlated events, each with marginal 0.8.\nAdmission uses the exact rational lower bound; unknown dependence widens uncertainty.')
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H3']
    bars=ax.bar(['Greedy tied\n(feasible)','Cheaper or rescued\n(feasible)','Infeasible\n(protections retained)'],[h['feasible_cases']-h['improved_cases'],h['improved_cases'],len(h['fixtures'])-h['feasible_cases']]);ax.bar_label(bars)
    ax.set(ylim=(0,85),ylabel='Controlled fixtures',title='H3 | Minimal repair improves 13 of 82 feasible cases')
    save(fig,2,'128 seeded eight-atom fixtures; zero feasibility or optimum mismatches.\nSupplied withdrawal costs and protected facts; no source is actually deleted.')
    fig,ax=plt.subplots(figsize=(8.5,4.8));rows=r['H4']['large'];x=[v['vertices'] for v in rows]
    ax.plot(x,[v['oracle'] for v in rows],marker='o',label='Flow = analytic optimum = greedy')
    ax.plot(x,[v['previous']['utility'] for v in rows],marker='x',linestyle='--',label='Previous cutset policy: staged')
    ax.set(xlabel='Vertices in complete bipartite component',ylabel='Supplied-priority utility',title='H4 | Bipartite structure expands certified solver coverage');ax.legend()
    save(fig,3,'Five analytical fixtures; maximum 256 vertices. Left weight 2, right weight 3.\nGreedy also succeeds here. Priority optimality is not semantic correctness.')
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H5'];x=np.arange(5);rows=h['sparse']+[h['dense']]
    for offset,key,label in [(-.18,'baseline_checks','Pairwise'),(.18,'indexed_checks','Indexed')]:
        ax.bar(x+offset,[v[key] for v in rows],.36,label=label)
    ax.set(xticks=x,xticklabels=['Sparse\n256','Sparse\n512','Sparse\n1,024','Sparse\n2,048','Dense\n256'],yscale='log',ylabel='Semantic pair checks (log scale)',title='H5 | Identical conflict edges with fewer sparse pair checks');ax.legend()
    save(fig,4,'2,048-row sparse case: 2,096,128 -> 3,712 checks; 1,920 identical edges.\nDense control: no pair-count saving. Runtime is measured separately, not inferred.')


def replace_after_anchor(text,body):
    text=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*','',text,flags=re.S)
    if text.count(ANCHOR)!=1:raise ValueError('Expected exactly one reliability section anchor')
    before,after=text.split(ANCHOR,1)
    return before+ANCHOR+'\n\n'+START+'\n\n'+body.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def update_paper(r):
    def rebase(match):
        url=match.group(1)
        if '://' in url or url.startswith('#'):return ']('+url+')'
        path=(HERE/url).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Link outside repository')
        return '](../'+path.relative_to(ROOT).as_posix()+')'
    body=re.sub(r'\]\(([^)]+)\)',rebase,render(r))
    path=ROOT/'manuscript/paper-current.md';path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'),body),encoding='utf-8',newline='\n')
    outcomes='; '.join(f"H{i} {'met' if r[f'H{i}']['primary_target_met'] else 'did not meet'} its frozen target" for i in range(1,6))
    note=('## Five previously untested mechanisms after PR #17\n\n'
          '[Executed report](graph_synthesis/novel_mechanisms/RESULTS.md), [frozen protocol](graph_synthesis/novel_mechanisms/PROTOCOL.md), '
          '[five figures](graph_synthesis/novel_mechanisms/figures/) and [updated full paper](manuscript/paper-current.pdf). '
          +outcomes+'. Label-shift correction ties at 18 wrong edges per 150 accepted. Dependence-safe certificates, protected-fact repair, '
          'bipartite optimization and indexed conflict construction meet controlled targets. No fresh Jev calls, independent semantic accuracy '
          'or worldwide novelty claims; no production policy changes. Negative results and assumption-breaking controls are retained.')
    path=ROOT/'CURRENT_RESULTS.md';path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'),note),encoding='utf-8',newline='\n')


def manifest():
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact-manifest.json'}
    write(HERE/'artifact-manifest.json',{'sha256':files,'note':'New-mechanism extension only; excludes self-reference. Shared paper uses its build manifest.'})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--figures',action='store_true');parser.add_argument('--update-paper',action='store_true')
    args=parser.parse_args();r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    (HERE/'RESULTS.md').write_text(render(r),encoding='utf-8',newline='\n')
    with (HERE/'summary.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['hypothesis','mechanism','primary_target_met','fresh_service_calls'])
        for i,title in enumerate(TITLES,1):writer.writerow([f'H{i}',title,r[f'H{i}']['primary_target_met'],0])
    if args.figures:figures(r)
    if args.update_paper:update_paper(r)
    manifest();print('Generated new-mechanism report, CSV, requested figures and additive manuscript section')


if __name__=='__main__':main()
