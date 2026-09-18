"""Generate evidence-linked prose, five figures and additive manuscript updates."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

from .run import HERE, ROOT, read, sha, write

START = '<!-- ADAPTIVE_RESEARCH_START -->'
END = '<!-- ADAPTIVE_RESEARCH_END -->'
NAMES = {'single':'Single rich prompt','contrastive':'Compact prompt','targeted':'Original targeted',
         'repeat_vote':'Three repeats','compact_confidence':'Compact confidence route',
         'compact_disagreement':'Compact disagreement route','safe_targeted':'Dependency-safe fallback',
         'flat_vote':'Flat seven-view vote','capped_vote':'Redundancy-capped vote'}
TITLES = ['Compact disagreement routing','Dependency-safe fallback','Redundancy-capped voting','Group-aware review','Joint conflict optimization']


def ci_text(interval):
    return '['+', '.join(f'{100*x:+.2f}' for x in interval)+'] pp'


def render(r):
    m=r['observed']; h1,h2,h3,h4,h5=(r[f'H{i}'] for i in range(1,6))
    out=['# Adaptive verification and joint conflict resolution for Jev graph synthesis','',
         'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026','',
         '## Abstract','',
         f"Following the multicall study, we execute five falsifiable improvements rather than assume that additional model calls improve graph quality. Compact disagreement routing saves {h1['token_saving']:.2%} of recorded input tokens, preserves the single baseline's wrong-edge count, and recovers one additional correct edge, but misses its frozen 40% saving target. Dependency-safe fallback eliminates operational failures while admitting more incorrect relationships. Development-learned redundancy capping does not establish a matched-volume advantage. Group-aware review reduces source-group contamination under an explicitly simulated reviewer, and joint conflict optimization improves supplied priority utility in bounded controlled graphs. None of these results establishes independent semantic generalization, safe autonomous writes or superiority to KARMA.",'',
         '## Research question and provenance','',
         f"The protocol was committed in `{r['protocol_commit']}` before executing this extension, against baseline `{r['baseline_commit']}`. Prior multicall test results were already inspected to formulate the hypotheses. This is an exploratory follow-on, not independent preregistration. H1-H3 replay authentic saved responses; H4 simulates review on observed source groups; H5 executes algorithms against an independent finite oracle. **Fresh service calls in this extension: {r['fresh_service_calls']}.** The prior 3,024 calls are not counted as new inference.",'',
         f"The original split remains {r['development']['n']} development candidates in {r['development']['groups']} source groups and {r['test']['n']} test candidates in {r['test']['groups']} groups. H3 clusters and H4 risk estimates use development labels only. Every decision policy receives gold-free inputs. Hash checks, raw response reconstruction, group isolation and the original offline replay run before the new analysis. These published test items are not a new holdout.",'',
         'The motivating evidence is the [multicall report](../../experiments/jev-multicall-20260918/REPORT.md) and [previous follow-up](../followup/RESULTS.md). The [frozen protocol](PROTOCOL.md) specifies all five conjunctions below. Typed output validity, semantic correctness and graph-level consistency remain separate properties. See the [TypeSafe documentation](https://docs.typesafe.ai/introduction) and [KARMA paper](https://arxiv.org/abs/2502.06472) for the respective bounded-decision and broader enrichment contexts; neither is a newly executed external baseline.','',
         '## Frozen operational targets','',
         '| Hypothesis | Target | Outcome and evidence boundary |','|---|---|---|']
    criteria=['40% token saving; 98% correct-edge retention; no extra wrong edges',
              '75% fewer operational failures; 98% retention; no extra wrong edges',
              '20% fewer matched-volume errors than flat voting; 95% retention',
              'Fewer contaminated groups than individual-risk review at budget 20; no lower retention',
              'Zero oracle errors; never below greedy utility; strict gain on at least 10% of random fixtures']
    evidence=['Saved-response counterfactual','Saved-response counterfactual','Development-fit response replay','Simulated ideal reviewer only','Finite controlled graph oracle only']
    for i in range(1,6):
        outcome='Met' if r[f'H{i}']['primary_target_met'] else 'Not met'
        out.append(f'| H{i}: {TITLES[i-1]} | {criteria[i-1]} | {outcome}; {evidence[i-1]} |')
    out+=['','A target pass is a point-estimate engineering result, not a statistically established general improvement. Do not pool these different evidence types into a success rate.','',
          '## H1: Compact disagreement-triggered escalation','',
          'The compact contrastive prompt and the short evidence-only blind1 reviewer are evaluated first. Agreement keeps the compact answer; disagreement or invalid output invokes the rich base1 answer. The two views still share Jev and source evidence. The ablation replaces disagreement with the fixed 0.90 compact-confidence threshold. Every required preliminary, fallback and failed call is charged.','',
          '| Policy | Correct / wrong edges | Precision | Recall | Required calls | Input tokens |','|---|---:|---:|---:|---:|---:|']
    for arm in ('single','contrastive','compact_confidence','compact_disagreement'):
        a=m[arm];out.append(f"| {NAMES[arm]} | {a['correct_edges']} / {a['wrong_edges']} | {a['precision']:.2%} | {a['recall']:.2%} | {a['required_calls']} | {a['input_tokens']:,} |")
    out+=['',f"Disagreement routing retains {h1['correct_retention']:.2%} of baseline correct edges and saves {h1['token_saving']:.2%} of tokens. Its quality point targets are met but the 40% cost target is not. It also requires more physical calls than the single baseline, so token savings cannot be presented as measured latency savings. The confidence ablation is slightly cheaper; disagreement gains one correct edge in this capture, not an established general advantage.",'',
          '![H1: recorded tokens versus recovered correct edges](figures/01_routing.png)','',
          '## H2: Dependency-safe fallback for invalid typed checks','',
          'An invalid base1 call falls back to the independent standalone compact request. With a valid base1 answer, invalid check vectors preserve base1 and do not authorize adjudication. Valid prerequisites permit adjudication; an invalid adjudicator falls back to base1. “Standalone” means not conditioned on the invalid checks, not statistically independent. The policy neither normalizes invalid vectors nor invents unobserved responses.','',
          '| Policy | Correct / wrong edges | Operational errors | Input tokens |','|---|---:|---:|---:|']
    for arm in ('single','targeted','safe_targeted'):
        a=m[arm];out.append(f"| {NAMES[arm]} | {a['correct_edges']} / {a['wrong_edges']} | {a['errors']} | {a['input_tokens']:,} |")
    out+=['',f"Operational failures fall from {m['targeted']['errors']} to {m['safe_targeted']['errors']}. However, the recovered coverage raises incorrect edges to {m['safe_targeted']['wrong_edges']} versus {m['single']['wrong_edges']} for the single baseline. The frozen safety conjunction is therefore not met. A valid typed answer is not necessarily a correct graph edge; failure recovery must be evaluated alongside semantic harm.",'',
          '![H2: recovery and semantic error accounting](figures/02_fallback.png)','',
          '## H3: Redundancy-capped voting','',
          'Development error overlap clusters the seven views, using a fixed 0.80 same-wrong-label intersection/union threshold. Each cluster casts at most one vote. Positive acceptance requires a strict majority and at least two supporting clusters. At least one valid view is required in every cluster; otherwise the policy remains an operational error. These are empirical error-redundancy clusters, not independent sources or calibrated evidence units.','',
          'Learned clusters: '+ '; '.join('`'+', '.join(group)+'`' for group in h3['fit']['clusters'])+'.','',
          f"At the natural operating point, capped voting yields {m['capped_vote']['correct_edges']} correct edges, {m['capped_vote']['wrong_edges']} wrong edges, {m['capped_vote']['abstentions']} abstentions and {m['capped_vote']['errors']} errors. At a fixed {h3['matched_k']} accepted edges:",'',
          '| Policy | Correct / wrong | Precision | Input tokens for all candidate decisions |','|---|---:|---:|---:|']
    for arm in ('single','flat_vote','capped_vote'):
        a=h3['matched'][arm];out.append(f"| {NAMES[arm]} | {a['correct_edges']} / {a['wrong_edges']} | {a['precision']:.2%} | {a['input_tokens']:,} |")
    out+=['',f"The capped-versus-flat matched precision difference has a descriptive 95% interval of {ci_text(h3['paired_vs_flat']['precision']['95'])} and 99% interval of {ci_text(h3['paired_vs_flat']['precision']['99'])}. Both include zero. The 20% error-reduction target is not met; the single baseline also has fewer matched-volume mistakes. All seven calls are charged. Error diversity alone is insufficient evidence of useful or economical corroboration.",'',
          '![H3: equal-volume incorrect edges](figures/03_corroboration.png)','',
          '## H4: Group-aware review allocation','',
          'Development-only shrinkage estimates edge error risk from label, the 0.90 score indicator, and disagreement with the compact view. Individual review sorts by that risk. Group-aware review greedily maximizes the estimated reduction in source-group contamination: an edge risk times the product of the remaining edges\' estimated correctness. This independence-shaped product is only a ranking heuristic; it is not a risk certificate under correlated errors. Selection sees no test labels.','',
          'The primary simulated reviewer removes wrong accepted edges, retains correct accepted edges and adds no missing edge. A source group is contaminated when any remaining accepted edge has the wrong label. These groups are source-dependence units, not measured database topology.','',
          '| Review budget | Individual: wrong edges / contaminated groups | Group-aware: wrong edges / contaminated groups | Correct edges retained (both) |','|---|---:|---:|---:|']
    for b in h4['budgets']:
        a,c=(b['policies'][n]['primary'] for n in ('individual','group'))
        out.append(f"| {b['budget']} | {a['expected_wrong_edges']:.0f} / {a['expected_contaminated_groups']:.0f} | {c['expected_wrong_edges']:.0f} / {c['expected_contaminated_groups']:.0f} | {a['expected_correct_edges']:.0f} |")
    out+=['','At budget 20, the ideal-review point target is met. The advantage is budget-dependent: the policies tie at budgets 10 and 40. Human-review accuracy and cost were not measured. Both rankings use the same observed features; obtaining those features entails single-plus-compact decisions for every candidate, not free additional evidence.', '',
          f"The recorded feature-acquisition total is {h4['risk_feature_input_tokens']:,} input tokens, before any actual review cost. Under a 5% false-removal rate, the following analytic sensitivity analysis applies at budget 20:",'',
          '| Wrong-edge detection sensitivity | Individual: expected contaminated groups / correct edges | Group-aware: expected contaminated groups / correct edges |','|---|---:|---:|']
    primary=h4['budgets'][1]['policies']
    for sensitivity in (.5,.75,1.):
        a,c=(next(x for x in primary[n]['sensitivity'] if x['sensitivity']==sensitivity and x['false_removal']==.05) for n in ('individual','group'))
        out.append(f"| {sensitivity:.0%} | {a['expected_contaminated_groups']:.2f} / {a['expected_correct_edges']:.2f} | {c['expected_contaminated_groups']:.2f} / {c['expected_correct_edges']:.2f} |")
    out+=['','These expectations assume independent reviewer detection across reviewed wrong edges and the specified false-removal rate; they are not additional observed trials. Full sensitivity combinations and selected IDs are in results.json.','',
          '![H4: contaminated source groups at fixed review budgets](figures/04_review.png)','',
          '## H5: Joint optimization of conflict components','',
          'The previous interval/scope guard detects incompatible assertions but does not choose a consistent batch. The new opt-in optimizer builds a conflict graph, separates connected components, and enumerates all subsets within components of at most 16 assertions. It chooses the maximum supplied priority sum among compatible assertions, with deterministic ID tie-breaking. Unsupported assertions and larger components are staged. This exponential method is deliberately bounded, not a database-scale algorithm.','',
          f"On {h5['random_cases']} seeded eight-assertion fixtures, it matches an independent integer-time active-fact oracle with {h5['oracle_failures']} oracle/consistency failures. There are {h5['permutation_failures']} failures across {h5['permutation_checks']:,} input-order checks. Joint utility strictly exceeds priority-first greedy on {h5['strict_improvements']}/{h5['random_cases']} fixtures ({h5['strict_improvements']/h5['random_cases']:.2%}); it is never lower.",'',
          '| Method | Aggregate supplied priority utility |','|---|---:|']
    for name,label in [('input_greedy','Input-order greedy'),('priority_greedy','Priority-first greedy'),('joint','Joint bounded optimizer')]:
        out.append(f"| {label} | {sum(x[name]['utility'] for x in h5['fixtures']):,} |")
    out+=['',f"An explicit counterexample gives greedy utility {h5['counterexample']['priority_greedy']['utility']} versus joint utility {h5['counterexample']['joint']['utility']}: one wide interval can block two compatible narrower assertions with greater combined priority. The 17-assertion over-limit control stages all 17 and writes none.",'',
          '**Falsifying semantic control:** two conflicting assertions have supplied weights 9 and 8, but the higher-weight assertion is labeled false by the controlled truth assignment. The optimizer selects the false assertion. Constraint consistency and maximum supplied utility therefore do not establish semantic truth. Priorities are not Jev-calibrated truth probabilities, and mis-specified priorities can favor the wrong graph.','',
          '![H5: bounded joint versus greedy utility](figures/05_joint.png)','',
          '## Uncertainty, failure criteria and interpretation','',
          'H1-H3 use 4,000 paired source-group bootstrap draws with seed 20260919. Policies, development fits and matched-volume ID sets remain fixed during resampling. The 95% and wider 99% percentile intervals are descriptive and exploratory; they are not simultaneous confidence intervals for all endpoints, do not include fitting uncertainty, and do not erase previous test exposure. Different accepted-set denominators can vary during a group bootstrap. Operational errors and abstentions remain in the full classification denominator, and wrong polarity is both an incorrect accepted edge and a missed gold edge.','',
          '| Prespecified comparison | 95% interval | 99% interval |','|---|---:|---:|']
    for label,interval in [('H1: recall difference vs single',h1['paired_vs_single']['recall']),('H2: wrong-edge rate difference vs single',h2['paired_vs_single']['wrong_edge_rate']),('H3: matched precision difference vs flat vote',h3['paired_vs_flat']['precision'])]:
        out.append(f"| {label} | {ci_text(interval['95'])} | {ci_text(interval['99'])} |")
    out+=['','The evidence favors treating token efficiency, operational resilience, semantic accuracy and graph maintenance as separate optimization goals. Compact routing remains an efficiency candidate; fallback needs explicit error-risk constraints; repeated or correlated votes are not independent corroboration. Group-level review and bounded joint optimization warrant broader tests, but their controlled gains must not be promoted to independent Jev-accuracy claims. No default policy is changed.','',
          '## Reproducibility and next falsification gates','',
          '```bash','python -B -m unittest discover -s graph_synthesis/adaptive/tests -v',
          'python -B -m graph_synthesis.adaptive.run --check',
          'python -B -m graph_synthesis.adaptive.report --figures --update-paper',
          'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf','```','',
          'results.json contains all five outcomes, source hashes, group intervals, clusters, review selections, sensitivity settings and controlled graph fixtures. predictions.json preserves every new policy outcome and required-call attribution for all development and test cases. summary.csv and five SVG/PNG figures are generated from those records. The artifact manifest binds source, outputs and validation logs. Original evidence and the archived original manuscript remain unchanged.','',
          'Independent source-disjoint semantic validation, prospective routed-service latency, real reviewer studies, correct qualifier/lineage extraction and matched-resource external baselines remain unexecuted. Candidate generation and open-ended relation discovery are outside this extension. The next decisive experiment should freeze a policy on these development results and test it on previously unseen source groups or a new corpus, without selecting the policy after seeing that evaluation.','']
    return '\n'.join(out)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt']='jev-adaptive-20260919'
    output=HERE/'figures';output.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(output/(name+'.svg'),metadata={'Date':None,'Creator':'Jev adaptive research'})
        fig.savefig(output/(name+'.png'),dpi=210,metadata={'Software':'Jev adaptive research'})
        plt.close(fig)
    m=r['observed']
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    for i,(arm,label) in enumerate([('single','Rich single'),('contrastive','Compact'),('compact_confidence','Confidence route'),('compact_disagreement','Disagreement route')]):
        a=m[arm];x=a['input_tokens']/1e6;y=a['correct_edges']
        ax.scatter([x],[y],s=80,marker=['o','s','^','D'][i])
        ax.annotate(f"{label}\n{a['wrong_edges']} wrong; {a['required_calls']} calls",(x,y),xytext=(8,10 if i!=2 else -35),textcoords='offset points',fontsize=9)
    ax.set(xlabel='Recorded input tokens (millions)',ylabel='Correct accepted edges',
           title='H1 | Compact routing trades tokens against edge recovery\nCounterfactual policy accounting; not measured routed latency',xlim=(.24,1.28),ylim=(127.5,135.3))
    ax.grid(alpha=.2);save(fig,'01_routing')
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    arms=['single','targeted','safe_targeted']
    for j,(key,label) in enumerate([('correct_edges','Correct edges'),('wrong_edges','Wrong edges'),('errors','Operational errors')]):
        x=[i+(j-1)*.24 for i in range(3)];vals=[m[a][key] for a in arms]
        ax.bar(x,vals,width=.24,label=label,hatch=['','//','xx'][j])
        for xx,value in zip(x,vals):ax.text(xx,value+2,str(value),ha='center',fontsize=9)
    ax.set_xticks(range(3),['Single','Original targeted','Safe fallback'])
    ax.set(ylabel='Candidates / edges',ylim=(0,177),title='H2 | Recovering valid answers can increase incorrect edges\nAll 263 test cases retained in the operational denominator')
    ax.legend(loc='upper center',ncol=3,fontsize=9);save(fig,'02_fallback')
    fig,ax=plt.subplots(figsize=(8.4,5.1))
    vals=[r['H3']['matched'][a]['wrong_edges'] for a in ('single','flat_vote','capped_vote')]
    ax.bar(['Single','Flat seven-view vote','Redundancy-capped vote'],vals)
    for i,value in enumerate(vals):ax.text(i,value+.35,str(value),ha='center')
    ax.set(ylabel='Wrong accepted edges (lower is better)',ylim=(0,max(vals)+5),
           title=f"H3 | Matched output volume: {r['H3']['matched_k']} edges\nCapping is not independent corroboration; its interval includes zero")
    save(fig,'03_corroboration')
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    for name,label in [('individual','Individual-risk ranking'),('group','Group-aware ranking')]:
        budgets=r['H4']['budgets']
        ax.plot([b['budget'] for b in budgets],[b['policies'][name]['primary']['expected_contaminated_groups'] for b in budgets],marker='o',label=label)
    ax.axvline(20,linestyle=':',alpha=.4)
    ax.set(xlabel='Accepted edges reviewed',ylabel='Remaining contaminated source groups',xticks=[10,20,30,40],ylim=(0,16),
           title='H4 | Review allocation targets groups, not only edge risk\nSimulated perfect reviewer; no new model judgments or human study')
    ax.legend();ax.grid(alpha=.2);save(fig,'04_review')
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    counts=Counter((x['priority_greedy']['utility'],x['joint']['utility']) for x in r['H5']['fixtures'])
    ax.scatter([a for a,b in counts],[b for a,b in counts],s=[18+12*n for n in counts.values()],alpha=.65)
    maximum=max(max(x) for x in counts)+3
    ax.plot([0,maximum],[0,maximum],linestyle='--',label='Equal utility')
    ax.set(xlabel='Priority-first greedy utility',ylabel='Joint optimizer utility',xlim=(0,maximum),ylim=(0,maximum),
           title=f"H5 | {r['H5']['strict_improvements']}/128 strict priority-utility gains\nFinite synthetic weights; utility is not semantic accuracy")
    ax.legend();ax.grid(alpha=.2);save(fig,'05_joint')


def replace_section(text, section):
    if (START in text) != (END in text):
        raise ValueError('Unbalanced adaptive manuscript markers')
    if START in text:
        before, remainder=text.split(START,1)
        _,after=remainder.split(END,1)
        text=before+after.lstrip('\n')
    return section+'\n\n'+text.lstrip('\n')


def update_paper(r):
    body=render(r)
    body=body.replace('](figures/','](../graph_synthesis/adaptive/figures/')
    body=body.replace('](PROTOCOL.md)','](../graph_synthesis/adaptive/PROTOCOL.md)')
    body=body.replace('](../../experiments/','](../experiments/').replace('](../followup/','](../graph_synthesis/followup/')
    section=START+'\n\n'+body+'\n'+END
    path=ROOT/'manuscript/paper-current.md'
    path.write_text(replace_section(path.read_text(encoding='utf-8'),section),encoding='utf-8',newline='\n')
    path=ROOT/'CURRENT_RESULTS.md';text=path.read_text(encoding='utf-8')
    if START in text:
        before,remainder=text.split(START,1);_,after=remainder.split(END,1);text=before+after.lstrip('\n')
    header,rest=text.split('\n\n',1)
    note=(START+'\n\n## Five adaptive improvements after multicall verification\n\n'
          '[Executed report](graph_synthesis/adaptive/RESULTS.md), [frozen protocol](graph_synthesis/adaptive/PROTOCOL.md), '
          '[five figures](graph_synthesis/adaptive/figures/) and [full updated paper](manuscript/paper-current.pdf). '
          'No fresh Jev calls. Compact disagreement routing saves '+f"{r['H1']['token_saving']:.2%}"+
          ' of recorded tokens but misses its frozen 40% target; invalid-check fallback removes operational failures but increases wrong edges; '
          'redundancy-capped voting fails its matched-volume target. Group-aware review meets its ideal-review target, and joint conflict optimization '
          'meets its finite-oracle target. Those controlled results are not independent semantic-accuracy evidence. No production policy changes.\n\n'+END+'\n\n')
    path.write_text(header+'\n\n'+note+rest,encoding='utf-8',newline='\n')


def manifest():
    files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*'))
           if p.is_file() and '__pycache__' not in str(p) and p.name!='artifact-manifest.json'}
    write(HERE/'artifact-manifest.json',{'sha256':files,'note':'Adaptive source and outputs, excluding this self-reference; prior evidence is not rewritten.'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures',action='store_true')
    parser.add_argument('--update-paper',action='store_true')
    args=parser.parse_args();r=read(HERE/'results.json')
    (HERE/'RESULTS.md').write_text(render(r),encoding='utf-8',newline='\n')
    with (HERE/'summary.csv').open('w',newline='',encoding='utf-8') as stream:
        fields=['policy','correct_edges','wrong_edges','precision','recall','macro_f1','errors','abstentions','required_calls','input_tokens','contaminated_groups']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for name,m in r['observed'].items():writer.writerow({'policy':name,**{key:m[key] for key in fields[1:]}})
    if args.figures:figures(r)
    if args.update_paper:update_paper(r)
    manifest()
    print(json.dumps({'report':'graph_synthesis/adaptive/RESULTS.md','figures':5 if args.figures else 'unchanged'}))


if __name__=='__main__':main()
