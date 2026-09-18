"""Deterministic evidence-linked report, five figures and additive paper update."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
from .run import HERE, ROOT, sha, write

START = '<!-- RELIABILITY_RESEARCH_START -->'
END = '<!-- RELIABILITY_RESEARCH_END -->'
ANCHOR = '<!-- RISK_CONTROL_RESEARCH_END -->'
TITLES = ['Out-of-group risk calibration','Single-view review prioritization','Exact bounded lineage','Cycle-cutset optimization','Incremental conflict maintenance']


def ci(value, percent=False):
    factor = 100 if percent else 1
    return '['+', '.join(f'{factor*x:+.4f}' for x in value)+']'+(' pp' if percent else '')


def render(r):
    a,b,c,d,e = [r[f'H{i}'] for i in range(1,6)]
    status = lambda h: 'Met' if h['primary_target_met'] else 'Not met'
    primary = b['budgets'][1]['policies']
    cheap, rich = [primary[k]['primary'] for k in ('single_view','two_view')]
    out = ['# Reliability, evidence lineage and incremental structure in Jev graph synthesis','',
           'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026','',
           '## Abstract','',
           f"Five frozen follow-up tests separate predictive-risk calibration, review-feature economy and deterministic graph maintenance. Out-of-group calibration selects a multiplier of {a['multiplier']:g}: group Brier changes from {a['baseline']['brier']:.6f} to {a['proposed']['brier']:.6f}, and the frozen calibration target is {status(a).lower()}. Single-view review features save {b['token_saving']:.2%} of recorded acquisition input tokens; at 20 idealized reviews they leave {cheap['expected_contaminated_groups']:g} contaminated groups versus {rich['expected_contaminated_groups']:g} for two-view features. Exact small-lineage evaluation, cycle-cutset conflict optimization and incremental component maintenance are evaluated against independent finite or analytic oracles. Their controlled targets are {status(c).lower()}, {status(d).lower()} and {status(e).lower()}, respectively. These results do not establish new Jev semantic accuracy, source independence, human-review effectiveness or superiority to an external graph-synthesis system.",'',
           '## 1. Motivation and protocol','',
           'The [adaptive study](../adaptive/RESULTS.md) and [risk-control study](../risk_control/RESULTS.md) identified optimistic source-contamination estimates, costly secondary review features and structural limits on conflict optimization. The [earlier lineage protocol](../followup/PROTOCOL.md) motivated tightening valid but conservative shared-evidence bounds. These are engineering extensions of established calibration, decomposition and dynamic-programming ideas, not algorithmic novelty claims. TypeSafe exposes typed judgments and probability outputs; structural consistency remains a separate property from semantic correctness ([documentation](https://docs.typesafe.ai/introduction)). Calibration assessment itself requires care about the predicted event and evaluation population ([Vaicenavicius et al.](https://arxiv.org/abs/1902.06977)).','',
           f"The [protocol](PROTOCOL.md) was committed as `{r['protocol_commit']}` before execution, against `{r['baseline_commit']}`. Prior test results were already public and informed hypothesis selection. This is exploratory follow-up, not independent preregistration. H1/H2 reuse {r['development']['n']} development candidates in {r['development']['groups']} groups and {r['test']['n']} evaluation candidates in {r['test']['groups']} groups. These are not fresh holdouts. Raw-response reconstruction, artifact hashes and group separation are checked before analysis. **Fresh service calls: {r['fresh_service_calls']}.** No default compiler or production graph policy changes.",'',
           '| Hypothesis | Frozen primary requirement | Outcome | Evidence class |','|---|---|---|---|']
    criteria = ['10% lower Brier and absolute group calibration bias <=0.03','No review-quality loss at budget 20 and >=25% cheaper features','Exact finite-oracle agreement, invariance, no false admission, one recovered admission','No oracle errors or small-case regression; ten large cycles/wheels exact','No recomputation mismatch; >=75% fewer solver-vertex visits']
    classes = ['Saved-response group scoring','Observed labels with simulated review','Supplied independent primitive-event model','Supplied abstract conflict graphs','In-memory controlled graph mutations']
    for i in range(1,6):
        out.append(f'| H{i}: {TITLES[i-1]} | {criteria[i-1]} | {status(r[f"H{i}"])} | {classes[i-1]} |')
    out += ['','A target pass is an engineering result on its stated population. The five evidence classes must not be pooled into a semantic success percentage. Negative results and falsifying controls are retained.','',
            '## 2. H1: Out-of-group source-risk calibration','',
            'The previous risk model estimates edge-error rates from base1 label, score >=0.90 and disagreement with the compact view, with two global-prior pseudo-observations. Its source contamination estimate is one minus the product of estimated edge-correctness probabilities. That product is a modeling choice, not a certificate of independent errors. For each development source group, we fit on all other groups and predict the held-out group. Empty accepted groups are excluded from this primary scoring population. We select k from {0.25,0.5,0.75,1,1.5,2,3,4} by held-out-group Brier score for q_new = 1-(1-q_old)^k, with frozen tie rules. The final edge-risk fit uses all development groups; test gold is used only for evaluation.','',
            '| Model | Nonempty test groups | Brier | Clipped log loss | Predicted contamination | Observed contamination | Bias |','|---|---:|---:|---:|---:|---:|---:|']
    for name,key in [('Original independent-risk model','baseline'),('Out-of-group calibrated','proposed')]:
        x=a[key];out.append(f"| {name} | {x['n']} | {x['brier']:.6f} | {x['log_loss']:.6f} | {x['mean_predicted']:.2%} | {x['mean_observed']:.2%} | {x['bias']:+.2%} |")
    out += ['',f"The selected multiplier is {a['multiplier']:g}; {len(a['folds'])} nonempty held-out development groups contribute to selection. Proposed-minus-baseline Brier has descriptive 95% interval {ci(a['paired_brier']['95'])} and 99% interval {ci(a['paired_brier']['99'])}. The primary conjunction is **{status(a).lower()}**. Better average proper score would not establish safety under new source distributions; a missed bias threshold remains a failure even if Brier improves.",'',
            '![H1. Group-contamination Brier on identical nonempty accepted source groups.](figures/01_group_calibration.png)','',
            '## 3. H2: Feature-parsimonious review prioritization','',
            'The proposed risk estimator removes compact-disagreement information and retains only base1 label and the fixed score indicator. Its execution receives no compact view and no gold labels. Both policies use the existing group-aware greedy review order and identical edge-review budgets. The primary reviewer removes every wrong reviewed edge, retains every correct edge and cannot add omitted edges. This deliberately idealized intervention isolates the ranking and feature-cost question; it is not an observed human experiment.','',
            '| Budget | Two-view contaminated groups | Single-view contaminated groups | Two-view correct retained | Single-view correct retained |','|---:|---:|---:|---:|---:|']
    for row in b['budgets']:
        x,y=[row['policies'][k]['primary'] for k in ('two_view','single_view')]
        out.append(f"| {row['budget']} | {x['expected_contaminated_groups']:g} | {y['expected_contaminated_groups']:g} | {x['expected_correct_edges']:g} | {y['expected_correct_edges']:g} |")
    out += ['',f"Feature acquisition costs {b['feature_tokens']['two_view']:,} recorded input tokens for two views versus {b['feature_tokens']['single_view']:,} for one view, a {b['token_saving']:.2%} reduction. All candidate decisions, including failed requests, are charged. Review cost itself is unknown and is not added as invented tokens or dollars. At budget 20, single-minus-two-view contaminated-group-rate difference has descriptive 95% interval {ci(b['paired_contamination_rate']['95'],True)} and 99% interval {ci(b['paired_contamination_rate']['99'],True)}. The primary conjunction is **{status(b).lower()}**. Pointwise preservation of a simulated outcome does not prove clinical, human-review or semantic noninferiority.",'',
            'The saved results also report fixed-selection sensitivity at detection rates 50%, 75% and 100%, crossed with false-removal rates 0%, 1% and 5%. Those expectations assume independent reviewer detection across reviewed wrong edges. They are scenario analyses, not additional observations.','',
            '![H2. Ideal-review contamination at equal edge budgets. Feature costs are separate.](figures/02_review_economy.png)','',
            '## 4. H3: Exact bounded shared-lineage probabilities','',
            'A proof is a conjunction of supplied independent primitive Bernoulli events, and a fact is supported by the disjunction of its proofs. Duplicates and subsumed proofs are canonicalized; disjoint primitive components can be combined under the supplied independence assumption. Each component of at most 16 atoms is evaluated by memoized Shannon expansion, conditioning on a primitive being true or false. The state budget is 32,768. Exceeding either limit returns conservative component max-proof/sum-proof bounds, never a partially evaluated probability presented as exact. The comparator is the previous duplicate-only shared-component bound.','',
            f"Across {c['cases']} seeded random fixtures, independent exhaustive event enumeration finds {c['oracle_failures']} disagreements beyond 1e-12. There are {c['invariance_failures']} failures in {c['invariance_checks']} order/duplicate checks and {c['false_admissions']} false lower-bound admissions at threshold 0.95. Mean interval width falls from {c['mean_baseline_width']:.6f} to {c['mean_exact_width']:.6f} on the bounded random fixtures. The primary controlled target is **{status(c).lower()}**.",'',
            '| Controlled example | Conservative lower bound | Exact probability / interval | Interpretation |','|---|---:|---:|---|',
            f"| Shared event 0.99 and eight alternative 0.5 events | {c['fan']['bounds']['lower']:.6f} | {c['fan']['exact']['lower']:.6f} | Recovers a justified >=0.95 admission |",
            f"| Seventeen-atom shared fan | {c['over_cap']['lower']:.6f} | [{c['over_cap']['lower']:.6f}, {c['over_cap']['upper']:.6f}] | Over cap; no exact claim |",
            f"| Forty atoms in twenty disjoint pairs | 0.250000 per proof | {c['disjoint_40_atoms']['result']['lower']:.6f} | Small components match analytic probability |",'',
            '**Falsifying assumption control:** one actual 0.8-probability source, incorrectly represented as two independent primitives, yields 0.96 instead of 0.8. Exact arithmetic cannot repair false lineage. Primitive reliabilities here are supplied fixture values, not calibrated Jev truth probabilities or independently verified document sources. State-count reductions are algorithmic diagnostics, not measured service latency.','',
            '![H3. Exact small-lineage evaluation tightens the conservative bound on a shared-source fan.](figures/03_lineage.png)','',
            '## 5. H4: Cycle-cutset conflict optimization','',
            'The solver accepts an explicit undirected conflict graph and nonnegative integer priorities. Connected components are capped at 256 vertices. Leaf peeling identifies the cycle core; deterministic highest-core-degree removal seeks at most four cut vertices. Enumerating compatible cutset choices leaves a forest solvable by include/exclude dynamic programming. Components not meeting the cutset cap retain exact subset enumeration at size <=16, otherwise they stage. This preserves a bounded unsupported path rather than silently running unrestricted exponential optimization. Graph extraction and semantic priority estimation are not performed.','',
            f"On {d['cases']} random small graphs, independent subset enumeration finds {d['oracle_failures']} optimum/consistency failures and no utility regression versus the forest-plus-small-enumeration policy. There are {d['permutation_failures']} failures in {d['permutation_checks']} input-order checks. All {len(d['large'])} large fixtures are checked against analytic optima; {d['large_failures']} fail. The primary target is **{status(d).lower()}**.",'',
            '| Topology | Vertices | Previous policy utility | Priority-greedy utility | Cutset utility | Oracle |','|---|---:|---:|---:|---:|---:|']
    for x in d['large']:
        out.append(f"| {x['kind']} | {x['n']} | {x['previous_policy']['utility']} | {x['greedy']['utility']} | {x['proposed']['utility']} | {x['oracle']} |")
    out += ['',f"The dense 17-clique control stages {len(d['dense_control']['staged'])} vertices. The semantic negative control assigns a false assertion priority 9 and a conflicting true assertion priority 8: the exact optimizer selects `{','.join(d['misleading_priority_control']['result']['selected'])}`. Thus optimal supplied utility and structural consistency do not establish factual truth. The previous-policy comparator is a faithful reimplementation of the forest/<=16-enumeration staging rule, not an external solver benchmark.",'',
            '![H4. Analytic cycle and wheel optima beyond the previous large-cycle staging boundary.](figures/04_cycle_capacity.png)','',
            '## 6. H5: Dependency-local incremental maintenance','',
            'The in-memory prototype caches solved component states. Each update validates the entire graph and discovers its new components. It reuses a cached solution only when component membership, every priority and every adjacency set are unchanged. Consequently bridge insertion, bridge deletion, vertex removal and changed weights invalidate affected solutions; unchanged components remain reusable. Invalid updates are rejected before stored state is altered. This is not a durable database transaction protocol.','',
            f"Across {e['mutation_cases']} seeded mutations, deliberate bridge controls and the locality/stress workloads, there are {e['mismatches']} selected/staged/utility mismatches against full H4 recomputation. The fixed local workload contains {e['local_workload']['components']} components of {e['local_workload']['vertices_per_component']} vertices and {e['local_workload']['updates']} local weight updates. Including an identical cold build, solver-submitted vertex visits fall from {e['local_workload']['full_solver_vertices']:,} to {e['local_workload']['incremental_solver_vertices']:,}, a {e['local_workload']['saving']:.2%} reduction. The primary target is **{status(e).lower()}**.",'',
            f"The connected-graph stress control saves {e['connected_control']['saving']:.2%}: every update dirties the only component. Critically, global snapshot validation and component discovery remain outside the solver-vertex metric and still run for every update. No equal percentage reduction in total CPU time, end-to-end complexity, database I/O or service latency is claimed.",'',
            '![H5. Solver work under local versus connected updates, including the cold build.](figures/05_incremental_work.png)','',
            '## 7. Uncertainty, limitations and research implications','',
            f"H1/H2 intervals use {r['bootstrap']['draws']:,} paired source-group bootstrap draws, seed {r['bootstrap']['seed']}. Development fits, selected multiplier and review ID sets remain fixed. H1 resamples identical nonempty accepted groups; H2 resamples all evaluation source groups. The 95% and 99% percentile intervals are descriptive, non-simultaneous and omit fitting uncertainty. Published evaluation-set reuse prevents independent confirmation. H3-H5 counts refer to controlled algorithm cases, not additional Jev observations.",'',
            'The structural extensions can be considered opt-in infrastructure candidates under their explicit caps and supplied inputs. Their apparent improvements do not cure candidate-generation failures, missing relation qualifiers, correlated model errors or incorrect provenance. The decisive next semantic test still requires a policy frozen before observing a new source-disjoint, independently adjudicated corpus, plus matched evidence and resource budgets for external systems such as KARMA. Real reviewer studies and prospective service-cost/latency measurements remain unexecuted.','',
            '## 8. Reproducibility','',
            '```bash','python -B -m graph_synthesis.reliability.run','python -B -m unittest discover -s graph_synthesis/reliability/tests -v','python -B -m graph_synthesis.reliability.run --check','python -B -m graph_synthesis.reliability.report --figures --update-paper','python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf','```','',
            'The machine-readable results preserve development fold exclusions, all calibration candidates, group predictions, review IDs, sensitivity assumptions, random fixtures, mutation events, oracle outputs and source hashes. Five SVG/PNG figure pairs and summary.csv are regenerated from results.json. The extension manifest binds source, results, figures and validation records. Original raw calls and the archived original manuscript are untouched. The complete current manuscript retains all preceding studies and their limitations.','']
    return '\n'.join(out)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'jev-reliability-20260921'
    directory = HERE/'figures';directory.mkdir(exist_ok=True)
    def save(fig, name, caption):
        fig.text(.08,.03,caption,ha='left',va='bottom',fontsize=9)
        fig.tight_layout(rect=(.02,.16,.99,.99))
        fig.savefig(directory/(name+'.svg'),metadata={'Date':None})
        fig.savefig(directory/(name+'.png'),dpi=200,metadata={'Software':'Jev reliability research'})
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H1']
    bars=ax.bar(['Original risk','Out-of-group calibrated'],[h['baseline']['brier'],h['proposed']['brier']])
    ax.bar_label(bars,fmt='%.4f');ax.set(ylabel='Source-contamination Brier (lower is better)',title='H1 | Calibration evaluated on identical source groups')
    ax.set_ylim(0,max(h['baseline']['brier'],h['proposed']['brier'])*1.3)
    save(fig,'01_group_calibration',f"Selected multiplier {h['multiplier']:g}; development-only fitting; already inspected evaluation data.\nCalibration is not a deployed group-risk guarantee.")
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H2']
    for key,label,marker in [('two_view','Two-view risk features','o'),('single_view','Single-view risk features','s')]:
        ax.plot([b['budget'] for b in h['budgets']],[b['policies'][key]['primary']['expected_contaminated_groups'] for b in h['budgets']],marker=marker,label=label)
    ax.set(xlabel='Reviewed edges',ylabel='Contaminated source groups',title='H2 | Idealized review at equal budgets',xticks=[10,20,30,40]);ax.legend()
    save(fig,'02_review_economy',f"Single-view acquisition saves {h['token_saving']:.2%} of recorded input tokens.\nPerfect-review simulation only; actual reviewer cost and accuracy are unknown.")
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H3']['fan']
    ax.bar(['Prior lower bound','Exact probability','Independent analytic oracle'],[h['bounds']['lower'],h['exact']['lower'],h['oracle']])
    ax.axhline(.95,linestyle='--',label='Admission threshold 0.95');ax.set(ylim=(0,1.1),ylabel='Supplied-model probability',title='H3 | Shared lineage without duplicate confidence inflation');ax.legend()
    save(fig,'03_lineage','Shared 0.99 event with eight alternative 0.5 events; supplied independent primitives.\nIncorrect lineage remains a falsifying control, not a solved extraction problem.')
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H4']
    for kind,marker in [('cycle','o'),('wheel','s')]:
        rows=[x for x in h['large'] if x['kind']==kind]
        ax.plot([x['n'] for x in rows],[x['proposed']['utility'] for x in rows],marker=marker,label=kind.title()+': solver = oracle')
    ax.plot([17,32,64,128,256],[0]*5,linestyle='--',label='Prior policy: staged')
    ax.set(xlabel='Vertices per conflict component',ylabel='Supplied-priority utility',title='H4 | Small cutsets extend exact cyclic-graph capacity');ax.legend()
    save(fig,'04_cycle_capacity','Ten analytic fixtures, cap 256 vertices and four cut vertices.\nConsistency and priority optimality do not establish semantic truth.')
    fig,ax=plt.subplots(figsize=(8.5,4.8));h=r['H5']
    bars=ax.bar(['Local-component updates','Single connected component'],[100*h['local_workload']['saving'],100*h['connected_control']['saving']])
    ax.bar_label(bars,fmt='%.2f%%');ax.set(ylim=(0,112),ylabel='Reduction in solver-submitted vertices (%)',title='H5 | Incremental benefit depends on update locality')
    save(fig,'05_incremental_work','Includes the identical cold build. Global graph validation/discovery still run.\nThis work metric is not end-to-end CPU time, latency or database I/O.')


def replace_after_anchor(text, body):
    text=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*','',text,flags=re.S)
    if text.count(ANCHOR)!=1:
        raise ValueError('Expected exactly one risk-control section anchor')
    before,after=text.split(ANCHOR,1)
    return before+ANCHOR+'\n\n'+START+'\n\n'+body.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def update_paper(r):
    def rebase(match):
        url=match.group(1)
        if '://' in url or url.startswith('#'):return ']('+url+')'
        path=(HERE/url).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Link outside repository')
        return '](../'+path.relative_to(ROOT).as_posix()+')'
    section=re.sub(r'\]\(([^)]+)\)',rebase,render(r))
    path=ROOT/'manuscript/paper-current.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'),section),encoding='utf-8',newline='\n')
    outcomes='; '.join(f"H{i} {'met' if r[f'H{i}']['primary_target_met'] else 'did not meet'} its frozen target" for i in range(1,6))
    note=('## Five reliability and structural improvements after PR #16\n\n'
          '[Executed report](graph_synthesis/reliability/RESULTS.md), [frozen protocol](graph_synthesis/reliability/PROTOCOL.md), '
          '[five figures](graph_synthesis/reliability/figures/) and [complete updated paper](manuscript/paper-current.pdf). '
          +outcomes+'. H1 scores captured predictions; H2 simulates review; H3-H5 test controlled algorithms. '
          'No fresh Jev calls, independent semantic-accuracy claim or production-policy change. Negative results and assumption-breaking controls are retained.')
    path=ROOT/'CURRENT_RESULTS.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'),note),encoding='utf-8',newline='\n')


def manifest():
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*'))
           if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact-manifest.json'}
    write(HERE/'artifact-manifest.json',{'sha256':files,'note':'Reliability extension only, excluding self-reference. Mutable shared paper uses its build manifest.'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures',action='store_true');parser.add_argument('--update-paper',action='store_true')
    args=parser.parse_args();r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    (HERE/'RESULTS.md').write_text(render(r),encoding='utf-8',newline='\n')
    with (HERE/'summary.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['hypothesis','title','primary_target_met','fresh_service_calls'])
        for i,title in enumerate(TITLES,1):writer.writerow([f'H{i}',title,r[f'H{i}']['primary_target_met'],0])
    if args.figures:figures(r)
    if args.update_paper:update_paper(r)
    manifest();print('Generated reliability report, table, requested figures and additive manuscript section')


if __name__=='__main__':main()
