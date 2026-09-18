"""Generate five evidence-linked figures and additive, reproducible paper sections."""
from __future__ import annotations
import argparse
import csv
import re
from pathlib import Path
from .run import HERE, ROOT, read, write, sha

START='<!-- RISK_CONTROL_RESEARCH_START -->'
END='<!-- RISK_CONTROL_RESEARCH_END -->'
ANCHOR='<!-- ADAPTIVE_RESEARCH_END -->'
NAMES={'single':'Single rich prompt','contrastive':'Compact prompt','targeted':'Original targeted',
       'safe_targeted':'Dependency-safe fallback','compact_confidence':'Compact confidence route',
       'compact_disagreement':'Compact disagreement route','value_route':'Learned value route',
       'group_gate':'Group-risk gate','invalid_only':'Invalid-only check gate','qualifier_veto':'Direct qualifier veto'}
TITLES=['Compact-only value routing','Source-group risk gate','Support-only qualifier veto',
        'Budget-optimal review','Forest-aware conflict solver']


def ci(values):
    return '['+', '.join(f'{100*v:+.2f}' for v in values)+'] pp'


def render(r):
    m=r['observed'];h1,h2,h3,h4,h5=(r[f'H{i}'] for i in range(1,6))
    a,b=h4['budgets'][1]['policies']['optimal'],h4['budgets'][1]['policies']['greedy']
    out=['# Risk control, targeted verification and structural tractability in Jev graph synthesis','',
         'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026','',
         '## Abstract','',
         f"Five refinements of the expanded Jev experiments are evaluated against frozen operational targets. A development-learned routing policy falls back to the rich prompt, achieving no token saving. A source-group risk gate reduces wrong accepted edges from {m['single']['wrong_edges']} to {m['group_gate']['wrong_edges']}, but retains only {h2['correct_retention']:.2%} of the baseline correct edges. Direct qualifier verification produces no valid semantic veto and performs worse descriptively at matched accepted volume. Exact review allocation satisfies its controlled optimization tests but does not improve the observed-label reviewer simulation. A forest-aware conflict solver meets all controlled targets and processes the tested acyclic components of up to 256 assertions that the previous 16-assertion-limited optimizer stages. These findings separate risk reduction, coverage loss, objective optimization and structural consistency from semantic truth. No fresh Jev calls, independent semantic-validation result or production-policy change is claimed.",'',
         '## 1. Motivation, scope and provenance','',
         'The [preceding adaptive extension](../adaptive/RESULTS.md) showed that additional verification can reduce operational errors without reducing wrong graph edges. It also exposed the cost of acquiring redundant views and the limited component size of exact conflict enumeration. We therefore test compact-only learned routing, source-group risk-constrained recovery, direct use of qualifier checks without adjudication, budget-optimal review with imperfect detection, and exploitation of acyclic conflict structure. These are new experiments and integrations in this package, not claims of newly invented statistical or optimization mathematics.','',
         f"The [protocol](PROTOCOL.md) was committed as `{r['protocol_commit']}` before execution, against baseline `{r['baseline_commit']}`. Earlier public results and the test set had already informed hypothesis selection. The extension is exploratory, not independent preregistration. The captured multicall study supplies {r['development']['n']} development candidates in {r['development']['groups']} source groups and {r['test']['n']} evaluation candidates in {r['test']['groups']} source groups. Fitting uses development labels only; execution functions accept no gold labels. Source-group overlap, source hashes and raw-response reconstruction are checked before analysis. The evaluation cases are not a fresh holdout.",'',
         f"**Fresh service calls in this extension: {r['fresh_service_calls']}.** H1-H3 execute counterfactual policies over authentic saved requests and responses. H4 combines observed source groups with explicitly assumed reviewer behavior; H5 uses controlled graphs and independent finite or analytic oracles. The earlier 3,024 physical calls are not recounted as new inference. Recorded token totals charge every call that the hypothetical policy would require, including failed and preliminary calls. They do not measure prospective service latency, new invoices or human-review cost.",'',
         'A correct accepted edge has a positive label (SUPPORTS or REFUTES) equal to the gold label. A wrong polarity is both a wrong accepted edge and a missed gold edge. NOT_ENOUGH_INFO is not a written edge. Operational errors and abstentions remain distinct and remain in full classification denominators. A contaminated source group contains at least one wrong accepted edge; source groups are dependence units, not measured database-connected components.','',
         '## 2. Frozen falsification criteria','',
         '| Hypothesis | Required primary conjunction | Outcome |','|---|---|---|']
    targets=['At least 40% token saving; at least 98% correct-edge retention; no extra wrong edges',
             'Nonempty qualifying risk gate; at least 90% correct-edge retention; all-group contamination at most 15%',
             'At least 20% fewer matched-volume wrong edges; at least 95% correct-edge retention; tokens at most 1.5 times single',
             'At budget 20, strictly fewer expected contaminated observed groups than sensitivity-aware greedy; no lower correct-edge retention',
             'Zero supported-oracle failures; no small-component utility regression; all ten large forest fixtures optimal without staging']
    for i,title in enumerate(TITLES,1):
        out.append(f"| H{i}: {title} | {targets[i-1]} | {'Met, controlled algorithms only' if r[f'H{i}']['primary_target_met'] else 'Not met'} |")
    out+=['','The criteria are conjunctions: satisfying one clause does not make a hypothesis pass. An engineering target pass is not a general statistical discovery. The evidence types must not be pooled into a semantic success percentage.','',
          '## 3. H1: Compact-only expected-value routing','',
          'To avoid the second preliminary call used by disagreement routing, the policy learns whether a rich call is worth obtaining from compact label and the fixed score-at-least-0.90 indicator alone. Development utility is +1 for a correct positive edge, -5 for a wrong positive edge and zero for a nonedge. Each bin estimates rich-minus-compact utility with two global-prior pseudo-observations. Seven frozen token-cost penalties are considered. Invalid compact calls always escalate; unseen bins also escalate. The cheapest development-feasible action table must retain at least 98% of rich-prompt correct edges and introduce no extra wrong edges. Direct-rich is an explicit fallback that does not pay compact overhead.','',
          'All seven learned candidates produce 31 correct and three wrong development edges, versus 32 correct and four wrong for direct-rich. Their 31/32 = 96.875% retention fails the 98% constraint despite better supplied utility and lower cost. The selected policy is consequently direct-rich. The choice was not changed after inspecting test outcomes.','',
          '| Policy | Correct / wrong edges | Required calls | Recorded input tokens |','|---|---:|---:|---:|']
    for name in ('single','contrastive','compact_confidence','compact_disagreement','value_route'):
        x=m[name];out.append(f"| {NAMES[name]} | {x['correct_edges']} / {x['wrong_edges']} | {x['required_calls']} | {x['input_tokens']:,} |")
    out+=['',f"H1 retains {h1['correct_retention']:.2%} of the baseline correct edges and saves {h1['token_saving']:.2%} of tokens. Its primary target is not met. The raw compact prompt's earlier efficiency result is not a newly validated routed-policy result. The guard exposes a real tradeoff: the available development evidence does not identify a compact-only action table satisfying the frozen recall constraint. All paired differences versus single-rich are exactly zero because the selected policies coincide.",'',
          '![H1. Actual token cost of the development-selected fallback and prior routing comparators.](figures/01_value_routing.png)','',
          '## 4. H2: Source-group risk-constrained recovery','',
          'The previous dependency-safe fallback is gated at five fixed positive-score thresholds: 0, 0.90, 0.95, 0.99 and 1. For each development source group, loss is one if any accepted edge is wrong and zero otherwise, including groups with no accepted edge. For k contaminated groups out of n, a one-sided exact binomial upper bound is obtained by solving P(Binomial(n, U) <= k) = 0.01. This is alpha = 0.05/5 for five candidates. A candidate qualifies if its upper bound is at most 0.15 and its accepted set is nonempty. The qualifying candidate with greatest development accepted volume is selected, with lower-threshold tie-breaking. No qualifying candidate would cause explicit stage-all, which cannot satisfy the nonempty target.','',
          'This diagnostic is motivated by [Learn then Test](https://arxiv.org/abs/2110.01052) and [risk-controlling prediction sets](https://arxiv.org/abs/2101.02703). Binomial sampling assumptions, representative independent calibration groups and untouched policy-selection evidence are not established by repeated analysis of this research set. The arithmetic bound is therefore not presented as a prospective deployment certificate. In particular, a bound on all-group contamination is not a bound on edge error or on contamination conditional on a nonempty graph.','',
          '| Cutoff | Accepted (dev) | Wrong groups / 40 | Upper bound | Pass |','|---:|---:|---:|---:|---|']
    for x in h2['fit']['candidates']:
        out.append(f"| {x['threshold']:.2f} | {x['accepted']} | {x['wrong_groups']} / {x['groups']} | {x['upper']:.2%} | {'Yes' if x['qualifies'] else 'No'} |")
    out+=['',f"The selected threshold is {h2['fit']['threshold']:.2f}. Its development count is zero contaminated groups out of 40, giving U = 1 - 0.01^(1/40) = {h2['fit']['candidates'][1]['upper']:.2%}. This is not zero risk.",'',
          '| Policy | Correct / wrong edges | Precision | Correct retention vs single | Input tokens |','|---|---:|---:|---:|---:|']
    for name in ('single','safe_targeted','group_gate'):
        x=m[name];out.append(f"| {NAMES[name]} | {x['correct_edges']} / {x['wrong_edges']} | {x['precision']:.2%} | {x['correct_edges']/m['single']['correct_edges']:.2%} | {x['input_tokens']:,} |")
    out+=['',f"The test gate yields {m['group_gate']['contaminated_groups']} contaminated groups out of {r['test']['groups']} ({h2['all_group_contamination']:.2%}) overall, but {m['group_gate']['contaminated_groups']} out of {h2['nonempty_groups']} ({h2['conditional_contamination']:.2%}) among groups with accepted edges. It stages {m['group_gate']['abstentions']} candidates and retains only {h2['correct_retention']:.2%} of single-rich correct edges, below the 90% target. It also retains the fallback's full recorded acquisition cost. Lower contamination is partly bought through reduced coverage; it does not establish a superior all-purpose graph compiler.",'',
          '![H2. Precision improvement is accompanied by a large loss of correct accepted edges.](figures/02_risk_tradeoff.png)','',
          '## 5. H3: Direct, SUPPORTS-only qualifier veto','',
          'Only a base1 SUPPORTS answer obtains the six existing qualifier checks. A valid MISMATCH probability of at least 0.90 in any dimension stages that edge. Other base labels remain unchanged: a mismatch can be legitimate evidence for REFUTES. An invalid check vector remains an operational error; it is never normalized. The adjudicator is never requested. The invalid-only ablation runs the same checks but never vetoes a valid answer. This distinguishes semantic filtering from accidental rejection caused by invalid responses.','',
          '| Policy | Correct / wrong edges | Operational errors | Calls | Input tokens |','|---|---:|---:|---:|---:|']
    for name in ('single','targeted','invalid_only','qualifier_veto'):
        x=m[name];out.append(f"| {NAMES[name]} | {x['correct_edges']} / {x['wrong_edges']} | {x['errors']} | {x['required_calls']} | {x['input_tokens']:,} |")
    out+=['',f"There are {h3['valid_vetoes']} valid semantic vetoes and {h3['invalid_checks']} invalid SUPPORTS check calls. The veto policy is identical to the invalid-only ablation on this capture. Its natural-point reduction in wrong accepted edges must therefore not be attributed to successful qualifier reasoning.",'',
          f"At the fixed matched volume of {h3['matched_k']} accepted edges:",'',
          '| Policy | Correct / wrong | Precision |','|---|---:|---:|']
    for name in ('single','qualifier_veto'):
        x=h3['matched'][name];out.append(f"| {NAMES[name]} | {x['correct_edges']} / {x['wrong_edges']} | {x['precision']:.2%} |")
    out+=['',f"The qualifier policy retains {m['qualifier_veto']['correct_edges']/m['single']['correct_edges']:.2%} of single-rich correct edges, below 95%, while using {m['qualifier_veto']['input_tokens']/m['single']['input_tokens']:.3f} times its tokens. Matched-volume errors increase rather than decrease. The matched precision difference has descriptive 95% interval {ci(h3['matched_intervals']['precision']['95'])} and 99% interval {ci(h3['matched_intervals']['precision']['99'])}; both include zero. Its natural recall difference has 95% interval {ci(h3['paired_vs_single']['recall']['95'])}. The frozen primary conjunction fails. This does not falsify all qualifier checking; it rejects the specified high-confidence veto using these saved checks.",'',
          '![H3. Equal-volume comparison; invalid-only and semantic-veto policies coincide.](figures/03_qualifier_veto.png)','',
          '## 6. H4: Budget-optimal review with imperfect detection','',
          'The development-only risk model from the previous extension supplies edge risks p. With assumed reviewer sensitivity s = 0.75, a reviewed edge contributes clean probability 1-p+sp rather than 1-p. Group contamination is one minus the product of these factors. A group option for k reviews chooses its k highest estimated risks; dynamic programming allocates an exact global budget across those options. The comparator is sensitivity-aware greedy review using the same objective. A second comparator preserves the prior ideal-review greedy order. The false-removal probability of a correct reviewed edge is assumed to be 0.05 and is evaluated separately; it is not included in the allocation objective.','',
          f"Independent subset enumeration on {len(h4['oracle_fixtures'])} eight-edge fixtures finds {h4['oracle_failures']} optimization failures. In the explicit complementarity counterexample, the optimum reviews both high-risk edges in one group, with modeled loss {h4['counterexample']['losses']['optimal']:.6f}, versus {h4['counterexample']['losses']['greedy']:.6f} for greedy. At the tested real-data budgets, the optimum never has worse modeled loss, with a small strict gain at budget 40. These controlled facts satisfy the algorithmic secondary target, not the empirical primary target.",'',
          '| Review budget | Greedy: expected contaminated groups | Optimal: expected contaminated groups | Expected correct edges (both) |','|---:|---:|---:|---:|']
    for x in h4['budgets']:
        g=x['policies']['greedy']['primary'];o=x['policies']['optimal']['primary']
        out.append(f"| {x['budget']} | {g['expected_contaminated_groups']:.4f} | {o['expected_contaminated_groups']:.4f} | {o['expected_correct_edges']:.2f} |")
    out+=['',f"At the primary budget 20, both select the same 20 edges and leave {a['primary']['expected_contaminated_groups']:.4f} expected contaminated observed groups and {a['primary']['expected_correct_edges']:.2f} expected correct edges. The required strict improvement is absent. More importantly, the fitted independent-risk model predicts only {a['model_contamination']:.4f} contaminated groups for that selection. Its discrepancy from the observed-label simulation is evidence against treating the estimated objective as a calibrated description of these test outcomes.",'',
          f"Risk-feature acquisition costs {h4['risk_feature_input_tokens']:,} recorded input tokens for single-plus-compact decisions, before any reviewer cost. results.json includes fixed-selection sensitivities s in {{0.5, 0.75, 1}} and false-removal rates in {{0, 0.01, 0.05}}. These are analytic expectations under assumed independent reviewer detection, not measured human-review trials. No accuracy or cost claim about actual reviewers follows.",'',
          '![H4. Optimization does not improve the observed-label simulation; model predictions are optimistic.](figures/04_review_gap.png)','',
          '## 7. H5: Forest-aware conflict optimization','',
          'The previous exact optimizer stages conflict components larger than 16 assertions. The new opt-in solver detects acyclic components and uses include/exclude tree dynamic programming to maximize the sum of nonnegative integer priorities. Cyclic components of at most 16 retain exact subset enumeration; larger cyclic components and any component exceeding 256 assertions are staged. Unsupported scopes, qualifiers or priorities are staged explicitly. Ties are deterministic within components. Building the conflict graph remains quadratic in input size; no unbounded database-scale or measured-latency claim is made.','',
          f"The solver has {h5['oracle_failures']} optimum/consistency failures on {h5['random_cases']} weighted eight-assertion fixtures, {h5['unweighted_oracle_failures']} on {h5['unweighted_oracle_cases']} corresponding unweighted fixtures, and {h5['permutation_failures']} failures across {h5['permutation_checks']} input-order checks. Independent integer-time active-fact enumeration supplies the small-graph oracle. Analytic star and path optima validate larger components. This supplements, rather than replaces, the previous bounded oracle evidence.",'',
          '| Structure | Assertions | Prior optimizer utility | Priority-greedy utility | Forest-aware / oracle utility |','|---|---:|---:|---:|---:|']
    for x in h5['large']:
        out.append(f"| {x['kind'].title()} | {x['n']} | {x['prior']['utility']} | {x['greedy']['utility']} | {x['forest']['utility']} / {x['oracle_utility']} |")
    out+=['',f"All ten large fixtures are optimal and consistent without staging. The previous optimizer stages every assertion in each of those over-limit components. The 17-node odd-cycle control stages {len(h5['odd_cycle_control']['staged'])} vertices; the 257-assertion over-limit forest stages {len(h5['over_limit_control']['staged'])} assertions. The odd cycle tests the generic conflict-graph backend; it is not a claim about extraction of that topology from scientific documents.",'',
          'The semantic negative control remains decisive: of two conflicting assertions with supplied priorities 9 and 8, the higher-priority assertion is assigned false by the controlled truth label. The optimizer still selects it. Exact constraint satisfaction and maximum supplied utility cannot establish factual truth or turn Jev confidence into a calibrated reliability weight. The primary controlled target is met, but no default production graph policy changes.','',
          '![H5. Acyclic structure permits bounded exact processing beyond the previous cap.](figures/05_forest_capacity.png)','',
          '## 8. Uncertainty and inference boundaries','',
          f"H1 and H3 use {r['bootstrap']['draws']:,} paired source-group bootstrap draws, seed {r['bootstrap']['seed']}. The fitted policies and matched accepted-ID sets remain fixed. The 95% and 99% percentile intervals are descriptive, are not simultaneous confidence intervals, exclude fitting uncertainty, and do not undo previous test exposure. All policies in a comparison use the same resampled groups. An operational target miss is retained even if one endpoint looks favorable.",'',
          '| Comparison / endpoint | Descriptive 95% interval | Descriptive 99% interval |','|---|---:|---:|']
    for title,d in [('H1: recall minus single',h1['paired_vs_single']['recall']),
                    ('H3: recall minus single',h3['paired_vs_single']['recall']),
                    ('H3: wrong-edge rate minus single',h3['paired_vs_single']['wrong_edge_rate']),
                    ('H3: matched precision minus single',h3['matched_intervals']['precision'])]:
        out.append(f"| {title} | {ci(d['95'])} | {ci(d['99'])} |")
    out+=['','H2 has a separate development calibration calculation, not a bootstrap deployment guarantee. H4 expectations depend on an unvalidated risk model and assumed reviewer behavior. H5 tests software and combinatorial optimization with supplied inputs and priorities, not model extraction of correct qualifiers or lineage. All five hypotheses were informed by prior results on related or identical data. The reported null and unfavorable results limit the conclusions.','',
          '## 9. Implications and the next decisive experiment','',
          'The main new positive finding is structural tractability: acyclic conflict sets need not inherit an exponential-enumeration size limit. The main semantic lesson is that restrictive verification can appear safer by suppressing useful output. Development constraints can reject economical routes; lower group contamination can hide coverage loss; invalid check failures can mimic semantic filtering; and exact review optimization can optimize a poorly calibrated objective. These are distinct failure modes and require distinct measurement.','',
          'The next semantic test should freeze an end-to-end candidate-generation, qualifier-extraction and acceptance policy, then evaluate new source-disjoint documents with human-adjudicated edge truth and prospective token, latency and review-cost measurements. External systems such as KARMA require matched input evidence and resource budgets before any superiority comparison. This extension neither runs such a baseline nor demonstrates autonomous graph-synthesis readiness. The current evidence supports opt-in engineering experiments, not a claim that all five improvements work.','',
          '## 10. Reproducibility and claim traceability','',
          '```bash','python -B -m unittest discover -s graph_synthesis/risk_control/tests -v',
          'python -B -m graph_synthesis.risk_control.run --check',
          'python -B -m graph_synthesis.risk_control.report --figures --update-paper',
          'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf','```','',
          '[results.json](results.json) records all targets, fits, intervals, selected IDs, controlled fixtures and source hashes. [predictions.json](predictions.json) retains every development/test policy decision and physical-call attribution. [summary.csv](summary.csv), five SVG/PNG figures and this text are generated from that evidence. [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md) locates each claim. The artifact manifest binds new source, outputs and validation logs; the archived original evidence and preceding experiment packages remain unchanged. The current full paper is an additive author-review draft, not a claim of independent peer review.','']
    return '\n'.join(out)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.hashsalt':'jev-risk-control-20260920','font.family':'DejaVu Sans','font.size':10})
    destination=HERE/'figures';destination.mkdir(exist_ok=True)
    def save(fig,name,caption):
        fig.text(.02,.02,caption,fontsize=9,va='bottom')
        fig.tight_layout(rect=(0,.12,1,1))
        fig.savefig(destination/(name+'.svg'),metadata={'Date':None},bbox_inches='tight')
        fig.savefig(destination/(name+'.png'),dpi=220,bbox_inches='tight')
        plt.close(fig)
    m=r['observed']
    fig,ax=plt.subplots(figsize=(8.8,4.5));names=['contrastive','compact_confidence','compact_disagreement','single','value_route']
    y=list(range(len(names)));bars=ax.barh(y,[m[n]['input_tokens']/1000 for n in names])
    ax.set_yticks(y,[NAMES[n] for n in names]);ax.invert_yaxis();ax.set_xlim(0,1170)
    for bar,n in zip(bars,names):
        x=m[n];ax.text(bar.get_width()+10,bar.get_y()+bar.get_height()/2,f"{x['correct_edges']} correct / {x['wrong_edges']} wrong",va='center',fontsize=9)
    ax.axvline(.60*m['single']['input_tokens']/1000,linestyle='--',label='40% saving target')
    ax.set_xlabel('Recorded input tokens (thousands)');ax.set_title('H1 | Learned routing selects the no-saving fallback');ax.legend(loc='lower right')
    save(fig,'01_value_routing','263 previously observed candidates; correct/wrong counts at natural acceptance.\nThe new policy is selected on development only; tokens are not measured latency.')
    fig,ax=plt.subplots(figsize=(8.8,4.5));names=['single','safe_targeted','group_gate']
    for n,offset in zip(names,[(8,7),(-185,10),(8,-25)]):
        x=m[n];ax.scatter(x['correct_edges'],x['wrong_edges'],s=75,label=NAMES[n]);ax.annotate(f"{NAMES[n]}\n{x['precision']:.1%} precision",(x['correct_edges'],x['wrong_edges']),xytext=offset,textcoords='offset points')
    ax.axvline(.90*m['single']['correct_edges'],linestyle='--',label='90% correct-retention target')
    ax.set(xlim=(95,145),ylim=(7,26),xlabel='Correct accepted edges (higher is better)',ylabel='Wrong accepted edges (lower is better)',title='H2 | Lower error counts come with lower useful coverage')
    ax.legend(loc='upper left',fontsize=8)
    save(fig,'02_risk_tradeoff','Selected gate: 102 correct / 11 wrong; only 77.27% baseline correct-edge retention.\nGroup-risk arithmetic is diagnostic, not a prospective deployment guarantee.')
    fig,ax=plt.subplots(figsize=(8.8,4.5));v=r['H3'];labels=['Single rich','Direct qualifier veto','Invalid-only ablation']
    wrong=[v['matched']['single']['wrong_edges'],v['matched']['qualifier_veto']['wrong_edges'],v['matched']['qualifier_veto']['wrong_edges']]
    bars=ax.bar(labels,wrong)
    for bar,value in zip(bars,wrong):ax.text(bar.get_x()+bar.get_width()/2,value+.25,str(value),ha='center')
    ax.set(ylim=(0,21),ylabel='Wrong edges at 138 accepted edges',title='H3 | No valid semantic vetoes; no matched-volume gain')
    save(fig,'03_qualifier_veto','0 valid semantic vetoes; 12 invalid SUPPORTS check calls. The ablation is identical.\nMatched precision difference, descriptive 95% interval: -5.87 to +0.07 percentage points.')
    fig,ax=plt.subplots(figsize=(8.8,4.5));rows=r['H4']['budgets'];xs=[x['budget'] for x in rows]
    for name,marker,ls in [('greedy','o','-'),('optimal','x','--')]:
        ax.plot(xs,[x['policies'][name]['primary']['expected_contaminated_groups'] for x in rows],marker=marker,linestyle=ls,markersize=8,label=f'Observed-label simulation: {name}')
    ax.plot(xs,[x['policies']['optimal']['model_contamination'] for x in rows],marker='s',linestyle=':',label='Fitted-risk objective: optimal')
    ax.set(xlabel='Review budget (edges)',ylabel='Expected contaminated source groups',ylim=(0,15),xticks=xs,title='H4 | Greedy and optimal tie; fitted risk is optimistic');ax.legend(fontsize=9)
    save(fig,'04_review_gap','Assumed sensitivity 75%; false removal 5%. At budget 20: observed-label expectation\n10.6875 vs fitted-risk prediction 4.0491. These are not human-review measurements.')
    fig,ax=plt.subplots(figsize=(8.8,4.5))
    for kind,marker in [('star','o'),('path','s')]:
        rows=[x for x in r['H5']['large'] if x['kind']==kind]
        ax.plot([x['n'] for x in rows],[x['forest']['utility'] for x in rows],marker=marker,label=f'{kind.title()}: forest solver = oracle')
    ax.plot([17,32,64,128,256],[0]*5,marker='x',linestyle='--',label='Previous solver: all staged')
    ax.set(xlabel='Assertions in a single conflict component',ylabel='Selected supplied-priority utility',title='H5 | Exact forest processing beyond the 16-assertion cap',xticks=[17,64,128,256]);ax.legend(fontsize=9)
    save(fig,'05_forest_capacity','Ten controlled stars/paths; bounded at 256 assertions; large cyclic components stage.\nZero oracle/consistency failures. Supplied-weight optimality does not establish truth.')


def replace_after_anchor(text,section):
    text=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*','',text,flags=re.S)
    if text.count(ANCHOR)!=1:
        raise ValueError('Expected exactly one adaptive section anchor')
    before,after=text.split(ANCHOR,1)
    return before+ANCHOR+'\n\n'+START+'\n\n'+section.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def update_paper(r):
    text=render(r)
    # Local links are rebased without touching other studies or external citations.
    def rebase(match):
        url=match.group(1)
        if '://' in url or url.startswith('#'):
            return ']('+url+')'
        path=(HERE/url).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Report link escapes repository')
        return '](../'+path.relative_to(ROOT).as_posix()+')'
    section=re.sub(r'\]\(([^)]+)\)',rebase,text)
    paper=ROOT/'manuscript/paper-current.md'
    paper.write_text(replace_after_anchor(paper.read_text(encoding='utf-8'),section),encoding='utf-8',newline='\n')
    note='## Five risk-controlled improvements after PR #15\n\n[Executed report](graph_synthesis/risk_control/RESULTS.md), [frozen protocol](graph_synthesis/risk_control/PROTOCOL.md), [five figures](graph_synthesis/risk_control/figures/) and [updated full paper](manuscript/paper-current.pdf). No new Jev calls. Learned routing falls back to single-rich; group-risk gating loses too much correct-edge coverage; direct qualifier vetoes yield no valid semantic filtering; optimal review ties observed outcomes. The forest-aware solver meets its controlled target on components up to 256 assertions. Negative results, explicit risk assumptions and the false-priority semantic control are retained. No production-policy changes.'
    current=ROOT/'CURRENT_RESULTS.md'
    current.write_text(replace_after_anchor(current.read_text(encoding='utf-8'),note),encoding='utf-8',newline='\n')


def manifest():
    paths={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(HERE.rglob('*'))
           if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact-manifest.json'}
    write(HERE/'artifact-manifest.json',{'note':'New risk-control source, evidence, figures and validation only; excludes self-reference. Earlier packages remain unchanged.','sha256':paths})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--figures',action='store_true');parser.add_argument('--update-paper',action='store_true');args=parser.parse_args()
    r=read(HERE/'results.json');(HERE/'RESULTS.md').write_text(render(r),encoding='utf-8',newline='\n')
    with (HERE/'summary.csv').open('w',encoding='utf-8',newline='') as stream:
        fields=['policy','correct_edges','wrong_edges','precision','recall','macro_f1','errors','abstentions','required_calls','input_tokens','contaminated_groups']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for name,x in r['observed'].items():writer.writerow({'policy':name,**{k:x[k] for k in fields[1:]}})
    if args.figures:figures(r)
    if args.update_paper:update_paper(r)
    manifest();print('Generated risk-control report, tables, requested figures and additive paper update')


if __name__=='__main__':main()
