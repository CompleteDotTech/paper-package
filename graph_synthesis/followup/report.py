"""Evidence-derived report, figures, and additive current-manuscript update."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEW = 'fewshot_contract'
START = '<!-- FOLLOWUP_RESEARCH_START -->'
END = '<!-- FOLLOWUP_RESEARCH_END -->'


def render(r: dict) -> str:
    task_names = {'entity_resolution':'Entity', 'relation_support':'Relation'}
    arm_names = {'baseline_noul':'base', 'baseline_choice':'base', 'fewshot_contract':'few-shot'}
    run_names = {'original':'old', 'rerun':'new'}
    a = r['H1']['tasks']['relation_support'][FEW]
    b = r['H2']['tasks']['relation_support']
    c = r['H3']['tasks']['relation_support'][FEW]
    d,e = r['H4'],r['H5']
    lines = ['# Five follow-up improvements: executed research', '',
             'This study builds on the ten-theory suite and the September 18 service rerun. '
             '**No fresh Jev requests were made in this follow-up.** H1-H3 replay captured observations; '
             'H4-H5 execute controlled algorithms against finite oracles. These are different evidence types, '
             'not five independent tests of improved model accuracy.', '',
             f"Baseline `{r['base_commit']}`; protocol committed as `{r['protocol_commit']}` before suite execution. "
             'Prior results were already known, so this is exploratory, not independent preregistration. '
             'Policies were not retuned after viewing the following outcomes.', '',
             '## Summary of fixed operational targets', '',
             '| Hypothesis | Evidence | Primary target met? |', '|---|---|---|']
    for h,title,kind in [('H1','Guarded probability calibration','Captured Jev replay'),
                          ('H2','Edge-aware economical routing','Captured-token routing counterfactual'),
                          ('H3','Cross-run stability gate','Paired captured observations'),
                          ('H4','Scope and interval conflicts','Finite controlled oracle'),
                          ('H5','Duplicate/shared-lineage bounds','Finite independent-event oracle')]:
        lines.append(f"| {h}: {title} | {kind} | {r[h]['primary_target_met']} |")
    lines += ['', 'A target pass is a point-estimate engineering result, not a statistically established general improvement. '
              'Do not pool the indicators into a success rate.', '',
              '## H1: Guarded probability calibration', '',
              'Tables label the original capture old and the September 18 rerun new; base denotes the baseline formulation.', '',
              'The fresh rerun showed that optimizing log loss could worsen Brier score. '
              'The proposed change fits a temperature on half of the original calibration components, then chooses '
              'a raw/temperature mixture on the other half with a no-worse-Brier constraint. Both components of '
              'this mixture preserve label order. No rerun labels enter the fit.', '',
              f"For the primary relation few-shot arm, selected temperature is {a['fit']['temperature']} and mixture weight is "
              f"{a['fit']['weight']}; fit/guard valid observations are {a['fit']['fit_n']}/{a['fit']['guard_n']}.", '',
              '| Task / arm | Run | Raw log loss | Temp log loss | Guard log loss | Raw Brier | Temp Brier | Guard Brier |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for task,arms in r['H1']['tasks'].items():
        for arm,x in arms.items():
            for run,v in x['runs'].items():
                lines.append(f"| {task_names[task]} / {arm_names[arm]} | {run_names[run]} | {v['raw']['log_loss']:.4f} | {v['temperature_only']['log_loss']:.4f} | "
                             f"{v['guarded']['log_loss']:.4f} | {v['raw']['brier']:.4f} | {v['temperature_only']['brier']:.4f} | {v['guarded']['brier']:.4f} |")
    v = a['runs']['rerun']
    lines += ['', f"Primary target met: **{r['H1']['primary_target_met']}**. Rerun valid probability N={v['raw']['n']}; "
              f"failures={v['raw']['errors']}; label changes={v['argmax_flips']}. Guard-minus-raw descriptive paired "
              f"95% component intervals: log loss {v['guarded_minus_raw_descriptive_95']['log_loss']}; "
              f"Brier {v['guarded_minus_raw_descriptive_95']['brier']}.", '',
              'The no-harm constraint holds on the guard partition only. It is not an out-of-sample guarantee, '
              'and preserving labels means this intervention cannot improve classification accuracy. '
              'Temperature-only here is fitted on the same half-calibration data as the guarded method, '
              'not the larger full-calibration fit reported in the previous paper.', '',
              '![Probability trade-off](figures/01_calibration.svg)', '',
              '## H2: Edge-aware economical routing', '',
              'The earlier macro-F1/cost cascade could save tokens while admitting more wrong relationships. '
              'This follow-up explicitly constrains correct edges, wrong edges and precision during calibration-only '
              'selection. Positive and negative baseline labels have separate escalation thresholds; failed '
              'baseline calls escalate. Always-few-shot is an explicit fallback that avoids unnecessary baseline cost.', '',
              f"Primary selected policy: `{json.dumps(b['fit']['policy'],sort_keys=True)}`. '",
              f"Earlier macro-F1 rule, refitted on the same original calibration: threshold {b['macro_fit']['threshold']}.", '',
              '| Task | Run | Policy | Correct edges | Wrong edges | Precision | Input tokens | Macro-F1 |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for task,x in r['H2']['tasks'].items():
        for run,v in x['runs'].items():
            for policy in ('baseline','fewshot','macro_cascade','edge_cascade'):
                m = v[policy]
                precision = 'N/A' if m['precision'] is None else f"{m['precision']:.2%}"
                lines.append(f"| {task_names[task]} | {run_names[run]} | {policy.replace('_', ' ')} | {m['correct']} | {m['wrong']} | {precision} | {m['input_tokens']:,} | {m['macro_f1']:.4f} |")
    v = b['runs']['rerun']
    lines += ['', f"Primary target met: **{r['H2']['primary_target_met']}**. Input-token saving {v['input_token_saving']:.2%}; "
              f"correct-edge retention {v['correct_edge_retention']:.2%}. The joint target requires at least 20% saving, "
              '98% retention, and no extra wrong edges versus all-few-shot.', '',
              f"The edge-aware and all-few-shot rerun policies differ on {v['paired_vs_fewshot']['different_labels']} labels. "
              'These are recorded input-token counterfactuals, not measured new API latency or billing. '
              'Baseline requests are charged even when a fallback is needed. Calibration feasibility does not '
              'guarantee evaluation safety. A macro-F1-only success is not substituted for the stated graph target.', '',
              f"Descriptive paired 95% rate-difference intervals versus all-few-shot: correct edges {v['paired_vs_fewshot']['descriptive_95_rate_difference']['correct_edge_rate']}; wrong edges {v['paired_vs_fewshot']['descriptive_95_rate_difference']['wrong_edge_rate']}. This is not an equivalence test.", '',
              '![Routing edge outcomes](figures/02_routing.svg)', '',
              '## H3: Cross-run stability gate', '',
              'The intervention accepts only positive labels that agree across exact-input original/rerun observations. '
              'Compare it with rerun confidence ranking and a uniform-random subset at exactly the same accepted volume. '
              'Stability is not independent corroboration; the two calls share model identity and evidence.', '',
              '| Task / arm | Rerun correct / wrong | Stable correct / wrong | Matched confidence wrong | Random expected wrong | Retention |',
              '|---|---:|---:|---:|---:|---:|']
    for task,arms in r['H3']['tasks'].items():
        for arm,x in arms.items():
            full,stable = x['rerun_all'],x['stable']
            lines.append(f"| {task_names[task]} / {arm_names[arm]} | {full['correct']} / {full['wrong']} | {stable['correct']} / {stable['wrong']} | "
                         f"{x['confidence_matched']['wrong']} | {x['random_matched_expected_wrong']:.3f} | {x['correct_edge_retention']:.2%} |")
    lines += ['', f"Primary target met: **{r['H3']['primary_target_met']}**. The primary arm has {c['common_valid_pairs']} "
              f"common-valid pairs, {c['both_wrong']} double errors and {c['same_wrong']} agreements on a wrong label; "
              f"{c['stable_wrong_score_one']} stable wrong positive edges have rerun score exactly one. '",
              f"Two-run input cost is {c['two_run_input_tokens']:,} versus {c['one_run_input_tokens']:,} for the rerun alone.", '',
              'Uniform-subset counts are exact expectations, not new random experiments or a significance test. '
              'Small volume reductions are not evidence of superiority when matched-volume confidence does better. '
              'A same-data repeat does not double the number of independent documents.', '',
              '![Matched stability errors](figures/03_stability.svg)', '',
              '## H4: Scope- and interval-aware conflicts', '',
              'Exact qualifier equality can miss contradictory assertions valid over overlapping time ranges. '
              'The opt-in guard checks half-open integer interval intersection, compatible known scope, polarity, '
              'and explicitly declared functional predicates. Unsupported/missing qualifiers return unknown and must '
              'be staged rather than silently accepted. It does not select which contradictory assertion is true.', '',
              f"Executed {d['supported_cases']:,} exhaustive supported pairs, including {d['true_conflicts']:,} oracle conflicts. '",
              '| Guard | Missed conflicts | False conflict flags |','|---|---:|---:|']
    for name,m in d['strategies'].items():
        lines.append(f"| {name} | {m['missed_conflicts']} | {m['false_conflicts']} |")
    lines += ['', f"Unknown/malformed cases staged: {d['unknown_staged']}/{d['unknown_cases']}. Primary target met: **{d['primary_target_met']}**.", '',
              'The independent oracle enumerates integer instants. This exhausts the declared finite fixture space, '
              'not arbitrary interval semantics or extracted real-world qualifiers. No production GraphStore '
              'policy is changed, and correct qualifier extraction remains untested.', '',
              '![Interval conflict validation](figures/04_intervals.svg)', '',
              '## H5: Duplicate/shared-lineage probability bounds', '',
              'Alternative proofs cannot be treated as independent when they share sources. This intervention '
              'deduplicates identical atom sets, connects overlapping proofs, bounds each component using maximum '
              'and summed proof probabilities, and combines disjoint components only under the supplied independent-atom model. '
              'An independent finite-state enumeration supplies exact probabilities.', '',
              f"Executed {e['cases']:,} configurations from {e['parameter_settings']:,} parameter/proof settings with "
              '1, 2, 5 and 20 copies. These copies are interventions, not independent samples.', '',
              '| Aggregator | False admissions at 0.95 | Correct high-probability admissions |', '|---|---:|---:|']
    for name,m in e['strategies'].items():
        lines.append(f"| {name} | {m['false_high_admissions']} | {m['correct_high_admissions']} |")
    lines += ['', f"Bound violations: {e['bound_violations']}; duplication-invariance failures: {e['duplicate_invariance_failures']}. "
              f"Mean interval width {e['mean_interval_width']:.4f}, maximum {e['max_interval_width']:.4f}. "
              f"Exact high-probability configurations: {e['known_high_probability_cases']}. Primary target met: **{e['primary_target_met']}**.", '',
              f"The conservative lower-bound gate loses {e['strategies']['naive_or']['correct_high_admissions']-e['strategies']['lineage_lower']['correct_high_admissions']} correct high-probability admissions compared with naive aggregation; lower false confidence comes with a retention cost.", '',
              f"**Negative control:** falsely declaring two aliases for one source independent produces lower bound "
              f"{e['negative_control']['supplied_lower']:.2f} for actual probability {e['negative_control']['actual_probability']:.2f}, "
              'and incorrectly passes the 0.95 gate. Thus lineage discovery and provenance integrity are necessary, '
              'not optional implementation details.', '',
              'These probabilities concern synthetic sufficient-proof validity events, not actual scientific truth. '
              '**Raw Jev confidence is not a certified primitive-event probability.** The control shows what the '
              'algorithm can guarantee under supplied assumptions and exactly how those assumptions can fail.', '',
              '![Duplication and confidence inflation](figures/05_lineage.svg)', '',
              '## Source separation, uncertainty and limitations', '',
              f"Both original/rerun empirical evaluations contain 339 relation candidates and 413 entity pairs; "
              'they are repeated observations of the same items. Original calibration component counts and purge audit '
              'are in results.json. Group construction uses claim/document or record IDs, not gold identity groups. '
              'Exact response reconstruction and pinned SHA-256 checks run before every analysis.', '',
              'H1 and H2 intervals use 1,000 paired connected-component bootstrap draws with seed 20260918. They are '
              'descriptive 95% intervals, unadjusted for multiple comparisons. No p-value, confirmatory claim, '
              'external-model win, candidate-generation recall improvement or deployed graph-risk guarantee is inferred. '
              'Invalid responses remain operational errors, with explicit valid-only probability denominators. '
              'The source-disjoint independent corpus and matched KARMA comparison remain unexecuted.', '',
              '## Reproduction and implementation status', '',
              '```bash', 'python -B -m unittest discover -s graph_synthesis/followup/tests -v',
              'python -B -m graph_synthesis.followup.run --check',
              'python -B -m graph_synthesis.followup.report --figures --update-paper',
              'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf', '```', '',
              'All numerical findings are generated from results.json. Existing frozen evidence and the default '
              'compiler remain unchanged. The methods are opt-in research implementations, not validated production '
              'replacements. All conclusions remain an AI-assisted author-review draft. See [PROTOCOL.md](PROTOCOL.md) '
              'for the frozen criteria and [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md) for evidence boundaries.', '']
    return '\n'.join(lines).replace(". '",'.')


def interval_series(r: dict) -> list[tuple[str, dict]]:
    """Bind plotted labels to keys, never JSON/dictionary iteration order."""
    return [(label, r['H4']['strategies'][key]) for key, label in (
        ('exact_qualifier', 'Exact qualifiers'),
        ('qualifier_blind', 'Ignore qualifiers'),
        ('interval_scope', 'Interval + scope'))]


def figures(r: dict):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'jev-followup-20260918'
    out = HERE/'figures'
    out.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(out/(name+'.svg'),metadata={'Date':None})
        fig.savefig(out/(name+'.png'),dpi=220,metadata={'Software':'Jev follow-up benchmark'})
        plt.close(fig)
    v = r['H1']['tasks']['relation_support'][FEW]['runs']['rerun']
    fig,ax = plt.subplots(figsize=(8.4,5.2))
    for name,label in [('raw','Raw'),('temperature_only','Temperature only'),('guarded','Guarded mixture')]:
        x,y = v[name]['log_loss'],v[name]['brier']
        ax.scatter([x],[y],s=75,label=f'{label}: ({x:.3f}, {y:.3f})')
    ax.set(xlabel='Log loss (lower is better)',ylabel='Brier score (lower is better)',
           title='H1 | Same-data rerun: probability trade-off\nSciFact few-shot; valid responses only')
    ax.legend(loc='best');ax.grid(alpha=.2)
    save(fig,'01_calibration')
    v = r['H2']['tasks']['relation_support']['runs']['rerun']
    names = ['baseline','fewshot','macro_cascade','edge_cascade']
    fig,ax = plt.subplots(figsize=(8.8,5.4))
    correct,wrong = [v[n]['correct'] for n in names],[v[n]['wrong'] for n in names]
    ax.bar(range(4),correct,label='Correct emitted edges')
    ax.bar(range(4),wrong,bottom=correct,label='Wrong emitted edges',hatch='//')
    for i,n in enumerate(names):
        ax.text(i,correct[i]+wrong[i]+3,f"{v[n]['input_tokens']/1000:.0f}k tokens",ha='center',fontsize=9)
    ax.set_xticks(range(4),['Baseline','All few-shot','Macro-F1 cascade','Edge-aware cascade'])
    ax.set(ylabel='Emitted relationships',title='H2 | Graph outcomes and recorded-token counterfactuals\nSame-data rerun; unmatched output volume',ylim=(0,max(c+w for c,w in zip(correct,wrong))*1.22))
    ax.legend(loc='upper right'); save(fig,'02_routing')
    c = r['H3']['tasks']['relation_support'][FEW]
    fig,ax = plt.subplots(figsize=(8.2,5.1))
    vals = [c['stable']['wrong'],c['confidence_matched']['wrong'],c['random_matched_expected_wrong']]
    ax.bar(['Two-run stability','One-run confidence','Uniform random expectation'],vals)
    for i,x in enumerate(vals):ax.text(i,x+.2,f'{x:.2f}',ha='center')
    ax.set(ylabel='Wrong emitted edges (lower is better)',title=f"H3 | Matched volume: {c['stable']['accepted']} relationships\nSame-data rerun; random bar is an exact expectation",ylim=(0,max(vals)*1.2))
    save(fig,'03_stability')
    rows = interval_series(r)
    fig,ax = plt.subplots(figsize=(8.6,5.2))
    ax.bar([i-.18 for i in range(3)],[m['missed_conflicts'] for _,m in rows],width=.36,label='Missed conflicts')
    ax.bar([i+.18 for i in range(3)],[m['false_conflicts'] for _,m in rows],width=.36,label='False conflict flags',hatch='//')
    ax.set_xticks(range(3),[label for label,_ in rows])
    ax.set(ylabel='Errors versus finite oracle',title=f"H4 | Controlled interval validation\n{r['H4']['supported_cases']:,} supported pairs; not model accuracy")
    ax.legend(); save(fig,'04_intervals')
    grid = r['H5']['duplication_grid']
    fig,ax = plt.subplots(figsize=(8.4,5.2))
    for key,label in [('naive_mean','Naive noisy-OR'),('exact_mean','Exact event enumeration'),('lower_mean','Lineage-aware lower bound')]:
        ax.plot([v['copies'] for v in grid],[v[key] for v in grid],marker='o',label=label)
    ax.set(xlabel='Duplicate copies per proof',ylabel='Mean probability across controlled settings',
           title='H5 | Repeating evidence is not new support\nSupplied independent primitive events; correct lineage required',ylim=(0,1.04))
    ax.set_xticks([1,2,5,20]);ax.legend();ax.grid(alpha=.2);save(fig,'05_lineage')


def update_paper(r: dict):
    report = render(r)
    section = START+'\n\n'+report.replace('# Five follow-up improvements: executed research','# Follow-up: five evidence-driven improvements')
    section = section.replace('](figures/','](../graph_synthesis/followup/figures/').replace('](PROTOCOL.md)','](../graph_synthesis/followup/PROTOCOL.md)').replace('](CLAIM_EVIDENCE.md)','](../graph_synthesis/followup/CLAIM_EVIDENCE.md)')
    section += '\n'+END+'\n\n'
    path = ROOT/'manuscript/paper-current.md'
    current = path.read_text(encoding='utf-8')
    if START in current:
        first = current.index(START);last = current.index(END)+len(END)
        current = current[:first]+current[last:].lstrip('\n')
    marker = '# Original study (historical evidence; unchanged text)'
    if marker not in current:
        raise ValueError('Historical manuscript boundary missing')
    current = current.replace(marker,section+marker,1)
    path.write_text(current,encoding='utf-8')
    entry = ROOT/'CURRENT_RESULTS.md'
    text = entry.read_text(encoding='utf-8')
    note = '\n## Five follow-up improvements (PR #13)\n\n[Executed results](graph_synthesis/followup/RESULTS.md), [frozen protocol](graph_synthesis/followup/PROTOCOL.md), '
    note += '[five figures](graph_synthesis/followup/figures/), and the updated full paper distinguish same-data response replay from controlled algorithm tests. '
    note += 'No new service calls; negative results retained; no production-policy change.\n'
    if '\n## Five follow-up improvements (PR #13)' in text:
        text = text.split('\n## Five follow-up improvements (PR #13)')[0]
    entry.write_text(text.rstrip()+'\n'+note,encoding='utf-8')


def manifest():
    paths = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.name!='artifact-manifest.json']
    values = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    (HERE/'artifact-manifest.json').write_text(json.dumps({'sha256':values,'note':'Generated artifacts and source; excludes this self-referential manifest.'},indent=2,sort_keys=True)+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures',action='store_true')
    parser.add_argument('--update-paper',action='store_true')
    args = parser.parse_args()
    r = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    if args.figures:figures(r)
    if args.update_paper:update_paper(r)
    manifest()


if __name__ == '__main__':main()
