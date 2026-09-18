"""Generate the executed source/structure report and additive manuscript section."""
from __future__ import annotations
import argparse
import csv
import json
import re
from .run import HERE, ROOT, sha, write

START = '<!-- SOURCE_STRUCTURAL_RESEARCH_START -->'
END = '<!-- SOURCE_STRUCTURAL_RESEARCH_END -->'
ANCHOR = '<!-- RELIABILITY_RESEARCH_END -->'
TITLES = ['Direct source-event shrinkage', 'Setup-cost-aware review', 'Frontier-bounded lineage',
          'Certified bipartite conflict solving', 'Revision-checked evidence cache']


def status(h):
    return 'Met' if h['primary_target_met'] else 'Not met'


def ci(values, percent=False):
    factor = 100 if percent else 1
    return '[' + ', '.join(f'{factor*x:+.4f}' for x in values) + ']' + (' pp' if percent else '')


def render(r):
    a, b, c, d, e = [r[f'H{i}'] for i in range(1, 6)]
    raw, scaled, direct = [a['scores'][k] for k in ('raw_product', 'scaled_product', 'direct_source')]
    primary = b['primary']['policies']
    greedy, batch = [primary[k]['evaluation'] for k in ('greedy', 'source_batch')]
    local, global_case = e['local_workload'], e['global_source_control']
    out = ['# Source risk, review budgets and structural certificates for Jev graph synthesis', '',
           'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026', '',
           '## Abstract', '',
           f"Five follow-up hypotheses test whether the limitations exposed by PR #17 can be reduced. Direct source-event shrinkage increases evaluation Brier from {raw['brier']:.6f} to {direct['brier']:.6f}; the calibration target is {status(a).lower()}. Setup-cost-aware review leaves {batch['expected_contaminated_groups']:.4f} expected contaminated groups versus {greedy['expected_contaminated_groups']:.4f} for greedy review at the same hypothetical budget; its target is {status(b).lower()}. Frontier lineage evaluation, certified bipartite conflict optimization and revision-checked source invalidation meet their controlled algorithmic targets. The cache reduces fact reevaluations by {local['saving']:.2%} on local updates, but by {global_case['saving']:.2%} when a shared source affects every fact. These are replay, simulation and algorithm results, not new Jev calls, human-review measurements or independent semantic validation.", '',
           '## 1. Research questions and frozen evaluation', '',
           'The [preceding reliability study](../reliability/RESULTS.md) found that a group-risk multiplier improved mean bias but worsened Brier, and that single-view review features could save acquisition tokens. Its structural experiments also exposed a 16-atom lineage boundary, a four-vertex conflict-cutset boundary, and update-locality limits. This extension changes the risk model, explicitly prices review setup, and broadens the tractable structural cases. It applies established shrinkage, dynamic programming, max-flow/min-cut and dependency indexing rather than claiming a new mathematical algorithm.', '',
           f"The [protocol](PROTOCOL.md) was committed before execution as `{r['protocol_commit']}`, against baseline `{r['baseline_commit']}`. Previous evaluation outcomes informed the hypotheses: this is an exploratory, pre-execution commitment, not an independent preregistration. H1/H2 reuse {r['development']['n']} development candidates in {r['development']['groups']} connected source groups and {r['test']['n']} evaluation candidates in {r['test']['groups']} groups. The original claim/document/duplicate-abstract grouping is preserved. A source group is not necessarily one document. In H2, setup is therefore charged per connected group, not per physical document opened. These hypothetical units cannot establish actual reviewer costs.", '',
           f"Raw responses and input hashes are verified before reconstruction. Development and evaluation groups are disjoint; policy inference receives no evaluation gold. **Fresh service calls: {r['fresh_service_calls']}.** Earlier public test-set inspection still prevents independent confirmation. No production graph policy is changed.", '',
           '| Hypothesis | Frozen primary criterion | Outcome | Evidence class |',
           '|---|---|---|---|']
    criteria = ['10% lower Brier than both prior models; absolute bias <=0.03',
                'At least 0.5 fewer expected contaminated groups; <=0.1 extra correct removals; budget respected',
                'No finite-oracle or invariance errors; ten large analytic cases exact; one interval tightened',
                'No small-case regression; ten certified large optima; at least four utility gains',
                'No stale values or atomicity failures; at least 90% fewer local fact reevaluations']
    classes = ['Archived prediction scoring', 'Label-evaluated review simulation', 'Supplied independent-event model',
               'Supplied conflict graphs and priorities', 'Sequential in-memory mutations']
    for i in range(1, 6):
        out.append(f'| H{i}: {TITLES[i-1]} | {criteria[i-1]} | {status(r[f"H{i}"])} | {classes[i-1]} |')
    out += ['', 'Passing three algorithmic targets does not amount to a three-out-of-five semantic success rate. The two unsuccessful predictive/review hypotheses and all assumption-breaking controls remain part of the results.', '',
            '## 2. H1: Direct source-event shrinkage', '',
            'The response variable is whether a connected group contains any incorrect base1-accepted SUPPORTS or REFUTES edge. Empty accepted groups are excluded. The proposed estimator uses two binary features: at least two accepted edges, and any accepted score below 0.90 (a missing score is treated conservatively as low). For cell c, the estimate is (errors_c + alpha * prior)/(n_c + alpha), with a Beta(1,1)-smoothed global group-error prior. Alpha is chosen from {1,4,16} by leave-one-development-group-out Brier; exact ties favor stronger shrinkage. This targets the group event directly instead of multiplying estimated edge-correctness probabilities.', '',
            '| Model | Brier | Log loss | Predicted risk | Observed risk | Bias |',
            '|---|---:|---:|---:|---:|---:|']
    for title, x in [('Prior product', raw), ('Prior scaled product', scaled), ('Direct source event', direct)]:
        out.append(f"| {title} | {x['brier']:.6f} | {x['log_loss']:.6f} | {x['mean_predicted']:.2%} | {x['mean_observed']:.2%} | {x['bias']:+.2%} |")
    out += ['', f"There are {len(a['folds'])} nonempty development groups and {direct['n']} nonempty evaluation groups. The chosen alpha is {a['alpha']}; the preceding development-selected multiplier is {a['previous_multiplier']:g}. Direct-minus-product Brier has descriptive 95% interval {ci(a['paired_brier']['raw_product']['95'])} and 99% interval {ci(a['paired_brier']['raw_product']['99'])}. Against the scaled product, the intervals are {ci(a['paired_brier']['scaled_product']['95'])} and {ci(a['paired_brier']['scaled_product']['99'])}. Neither a lower Brier nor the required bias is achieved: **{status(a).lower()}**.", '',
            'The small number of contaminated development groups makes cell estimation difficult. Directly predicting the desired event is a plausible modeling choice, but it is not a guarantee of better calibration. This experiment does not justify deploying the new estimator.', '',
            '![H1. Source-event Brier on identical accepted evaluation groups; lower is better.](figures/01_source_risk.png)', '',
            '## 3. H2: Review allocation with group setup costs', '',
            'Both policies use the preceding single-view edge-risk fit. The comparator follows its group-aware greedy edge order and admits each edge only if the remaining budget covers the edge plus any newly required group setup. The proposed multiple-choice knapsack offers each group either no review or its top-k risk-ranked edges. It maximizes the increase in predicted group-clean probability under independent edge errors and independent reviewer detection. Gold labels enter only the subsequent outcome calculation. The optimizer is exact over these prefix options, not over every possible human review action.', '',
            'The primary budget is 40 units: opening a connected group costs 2 and reviewing one edge costs 1. Detection is 0.75 and false removal of a correct reviewed edge is 0.01. These parameters are supplied assumptions, not observed reviewer behavior. Expected contamination counts a group if at least one incorrect accepted edge remains; a reviewer cannot add an omitted correct edge.', '',
            '| Policy | Spent | Reviewed | Wrong reviewed | Expected contaminated groups | Expected correct removals |',
            '|---|---:|---:|---:|---:|---:|']
    for title, k in [('Group-greedy', 'greedy'), ('Source-batched knapsack', 'source_batch')]:
        x, v = primary[k], primary[k]['evaluation']
        out.append(f"| {title} | {x['spent']} | {len(x['selected'])} | {v['reviewed_wrong']} | {v['expected_contaminated_groups']:.4f} | {v['expected_correct_removed']:.2f} |")
    out += ['', f"The proposed policy reviews more edges but leaves {batch['expected_contaminated_groups']-greedy['expected_contaminated_groups']:.2f} more expected contaminated groups, not at least 0.5 fewer. Its primary target is **{status(b).lower()}**. The proposed-minus-greedy expected contamination-rate difference has descriptive 95% interval {ci(b['paired_contamination_rate']['95'], True)} and 99% interval {ci(b['paired_contamination_rate']['99'], True)} across all {r['test']['groups']} evaluation groups.", '',
            f"There are {b['oracle_failures']} failures in {len(b['oracle_fixtures'])} independently enumerated small knapsack tests and {b['budget_failures']} budget violations in {len(b['scenarios'])} fixed sensitivity scenarios. The full grid crosses budgets {{20,40,80}}, setup costs {{0,1,2,5}}, detection {{0.5,0.75,1}} and false removal {{0,0.01,0.05}}. A perfectly correlated within-group detection control gives {primary['source_batch']['correlated_detection']['expected_contaminated_groups']:.2f} versus {primary['greedy']['correlated_detection']['expected_contaminated_groups']:.2f} expected contaminated groups at the primary setting. It also fails to reverse the unfavorable ordering.", '',
            f"Both policies use the same {b['feature_input_tokens']:,} recorded single-view input tokens, charged separately from hypothetical review units. Correct optimization of a misspecified risk objective need not improve label-evaluated outcomes. No human-time, dollar-cost, reviewer-quality or semantic noninferiority claim follows.", '',
            '![H2. Simulated contamination at equal total budgets, with fixed setup and reviewer assumptions.](figures/02_review_budget.png)', '',
            '## 4. H3: Frontier-bounded exact lineage', '',
            'A fact is a disjunction of proof conjunctions over supplied independent Bernoulli primitives. After removing duplicate and subsumed proofs, the proposed iterative dynamic program processes sorted primitive IDs. It remembers only processed atoms used in unfinished proofs. Once a proof succeeds, its probability mass is absorbed into the success total, preventing double-counting of shared evidence. Constants, impossible primitives and certain primitives are explicit cases. This is a bounded-width inference strategy, not an assertion that document sources are independent.', '',
            'The new path caps used atoms at 256, canonical proofs at 1,024, frontier width at 12 and state transitions at 65,536. Exceeding a cap delegates to the previous small-component exact/bounded routine. Partially evaluated mass is never reported as an exact answer. These caps bound the new frontier evaluation, not all validation, canonicalization or fallback work.', '',
            f"Independent assignment enumeration finds {c['oracle_failures']} errors beyond 1e-12 on {c['random_cases']} random fixtures with 2-10 atoms. There are {c['invariance_failures']} failures in {c['invariance_checks']} order/duplicate checks and {c['false_admissions']} false lower-bound admissions at threshold 0.95. All {len(c['large'])} large path/cycle cases match an independent no-adjacent-success recurrence; {c['tightened_large']} tighten the previous interval. The primary controlled target is **{status(c).lower()}**.", '',
            '| Lineage | Atoms | Prior interval | Exact probability | Frontier width | Transitions |',
            '|---|---:|---|---:|---:|---:|']
    for x in c['large']:
        p, q = x['previous'], x['proposed']
        out.append(f"| {x['kind']} | {x['n']} | [{p['lower']:.4f}, {p['upper']:.4f}] | {q['lower']:.6f} | {q['width']} | {q['transitions']} |")
    out += ['', 'Each large fixture uses primitive probability 0.1 and adjacent-pair proofs. Dense 17-atom lineage triggers the width fallback; a 257-atom input and a deliberately tiny state budget exercise other guards. The shared-source control still yields 0.96 instead of the actual 0.8 when one source is incorrectly encoded as two independent primitives. Better exact inference cannot repair false provenance, and the supplied probabilities are not calibrated Jev truth probabilities.', '',
            '![H3. Prior conservative intervals and exact frontier probabilities on large connected lineages.](figures/03_frontier_lineage.png)', '',
            '## 5. H4: Certified bipartite conflict optimization', '',
            'The input is an explicit undirected conflict graph with nonnegative integer priorities. On a bipartite component, maximum-weight independent set is reduced to minimum-weight vertex cover and solved by an integer max-flow/min-cut routine. The result includes a feasible flow and a vertex cover of equal weight. A separate verifier checks endpoints, capacities, conservation, cover feasibility, selection consistency and objective equality. This certificate proves the supplied combinatorial objective, not the truth of selected assertions.', '',
            'Components remain capped at 256 vertices. Nonbipartite components delegate to the preceding cycle-cutset policy. A 2,000,000 residual-edge-inspection budget bounds the new flow solver; exhaustion delegates rather than certifying an unfinished answer. No external graph-system benchmark or extracted real-world conflict graph is substituted for these controlled cases.', '',
            f"There are {d['oracle_failures']} finite-oracle/consistency/regression failures among {d['random_cases']} random small graphs and {d['invariance_failures']} failures in {d['invariance_checks']} input-order checks. All {len(d['large'])} large cases attain independently known optima with valid certificates; {d['improved_large']} improve supplied utility over the prior staging policy. The primary controlled target is **{status(d).lower()}**.", '',
            '| Conflict family | Vertices | Prior utility | Certified utility | Analytic optimum |',
            '|---|---:|---:|---:|---:|']
    for x in d['large']:
        out.append(f"| {x['kind']} | {x['n']} | {x['previous']['utility']} | {x['proposed']['utility']} | {x['oracle']} |")
    out += ['', 'Square grids use unit priorities and have optimum ceil(vertices/2). Complete balanced bipartite fixtures use priority 5 on one side and 3 on the other, with optimum five times the side size. These are specifically tractable families that exceeded the preceding four-cutset allowance, not representative samples of arbitrary graph-synthesis conflicts. Dense nonbipartite 17-clique staging, zero priorities, invalid inputs, work-budget exhaustion and damaged flow certificates are retained as controls. A false assertion of priority 9 still defeats a conflicting true assertion of priority 8; structural optimality is not factual accuracy.', '',
            '![H4. Certified optimization reaches analytic objectives where the previous bounded policy staged.](figures/04_bipartite_certificate.png)', '',
            '## 6. H5: Revision-checked evidence invalidation', '',
            'The prototype indexes each primitive to the facts whose canonical proofs depend on it. Probability changes reevaluate only those facts; proof replacement, insertion and deletion maintain the reverse index. Revocation is an explicit probability-zero update. Optimistic revision checks, input validation and all potentially failing evaluations run before state mutation. Stale revisions, invalid changes and injected evaluation failures are rejected without changing the prior snapshot. This is sequential in-memory behavior, not concurrent database isolation, crash recovery or durability.', '',
            f"Across {e['mutation_cases']} seeded source/proof/fact mutations, explicit retraction and restoration controls, and both work-count workloads, there are {e['mismatches']} cache/full-recomputation mismatches. All {len(e['atomic_controls'])} atomic rejection controls pass. The primary controlled target is **{status(e).lower()}**.", '',
            '| Workload | Facts | Updates | Full evaluations | Incremental evaluations | Reduction | Index touches |',
            '|---|---:|---:|---:|---:|---:|---:|']
    for title, x in [('Local source updates', local), ('Global shared source', global_case)]:
        out.append(f"| {title} | {x['facts']} | {x['updates']} | {x['full_evaluations']:,} | {x['incremental_evaluations']:,} | {x['saving']:.2%} | {x['index_touches']:,} |")
    out += ['', 'Both counts include the cold build. Each local fact has two proofs over three private primitives; the global control makes every fact depend on one shared source. Dependency-index touches count index construction/maintenance separately. These metrics omit general interpreter, allocation, validation and snapshot-comparison work; no matching percentage reduction in total CPU time, database I/O or service latency is claimed. A fact reevaluation can itself have variable lineage complexity.', '',
            '![H5. Fact reevaluation work falls for local evidence updates, not global dependencies.](figures/05_source_cache.png)', '',
            '## 7. Interpretation and limits', '',
            f"H1/H2 use {r['bootstrap']['draws']:,} paired source-group bootstrap draws, seed {r['bootstrap']['seed']}, with fixed fitted models, chosen hyperparameters and review selections. The 95% and 99% percentile intervals are descriptive, non-simultaneous and omit fitting uncertainty. H1 uses the {direct['n']} identical nonempty accepted evaluation groups; H2 uses all {r['test']['groups']} groups. Earlier reuse of these evaluation labels means the intervals are not prospective validation of hypotheses selected from previous results.", '',
            'The central finding is a separation: broader exact structural inference and safe local invalidation are achievable under supplied assumptions, while better source-risk estimates and useful cost-aware review are not established by these data. The structural methods remain opt-in research infrastructure. They do not remedy missing candidate edges, wrong relation qualifiers, correlated Jev errors, false provenance or untrustworthy priorities. A future semantic study should freeze policy before seeing an independently adjudicated, source-disjoint corpus, use matched information/resource budgets, and measure actual reviewer behavior and end-to-end latency. No advantage over KARMA or another external system is established here.', '',
            '## 8. Reproduction and attribution', '',
            '```bash',
            'python -B -m graph_synthesis.source_structural.run',
            'python -B -m unittest discover -s graph_synthesis/source_structural/tests -v',
            'python -B -m graph_synthesis.source_structural.run --check',
            'python -B -m graph_synthesis.source_structural.report --figures --update-paper',
            'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf',
            '```', '',
            'The [machine-readable results](results.json) contain folds, fitted cell counts, individual group probabilities, review selections, all sensitivity settings, finite/analytic oracles, flow certificates, mutation traces and source hashes. The [summary table](summary.csv), five SVG/PNG figure pairs and this report are generated from those results. The extension manifest binds code, evidence, figures and captured validation logs; the current paper has a separate build manifest. The original frozen study and all previous executed sections are preserved.', '',
            'Primary-source context: [TypeSafe documentation](https://docs.typesafe.ai/introduction) describes typed decisions and probability outputs; [Amarilli et al., Connecting Knowledge Compilation Classes and Width Parameters](https://arxiv.org/abs/1811.02944) provides bounded-width knowledge-compilation context; the [NetworkX minimum-cut documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.flow.minimum_cut.html) states the max-flow/min-cut relation. These sources motivate established techniques, not the numerical results reported here. Our finite and analytic checks are included in the repository; no claim of mathematical novelty is made.', '']
    return '\n'.join(out)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'jev-source-structure-20260922'
    directory = HERE / 'figures'
    directory.mkdir(exist_ok=True)
    def save(fig, name, caption):
        fig.text(.08, .025, caption, ha='left', va='bottom', fontsize=9)
        fig.tight_layout(rect=(.02, .16, .99, .99))
        fig.savefig(directory / (name + '.svg'), metadata={'Date': None})
        fig.savefig(directory / (name + '.png'), dpi=200, metadata={'Software': 'Jev source-structure research'})
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    h = r['H1']
    values = [h['scores'][k]['brier'] for k in ('raw_product', 'scaled_product', 'direct_source')]
    bars = ax.bar(['Prior product', 'Prior scaled product', 'Direct source event'], values)
    ax.bar_label(bars, fmt='%.4f')
    ax.set(ylim=(0, .18), ylabel='Group Brier (lower is better)', title='H1 | Direct source modeling does not improve risk scoring')
    save(fig, '01_source_risk', 'Identical 98 accepted evaluation groups; development-only shrinkage selection.\nPreviously inspected data. Frozen improvement target not met.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    h = r['H2']
    rows = [x for x in h['scenarios'] if x['setup'] == 2 and x['sensitivity'] == .75 and x['false_removal'] == .01]
    for key, label, marker in [('greedy', 'Group-greedy', 'o'), ('source_batch', 'Source-batched knapsack', 's')]:
        ax.plot([x['budget'] for x in rows], [x['policies'][key]['evaluation']['expected_contaminated_groups'] for x in rows], marker=marker, label=label)
    ax.set(xlabel='Total hypothetical setup-plus-edge budget', ylabel='Expected contaminated groups',
           title='H2 | More reviewed edges need not improve outcomes', xticks=[20, 40, 80])
    ax.legend()
    save(fig, '02_review_budget', 'Setup 2 units/group; 1 unit/edge; detection 0.75; false removal 0.01.\nLabel-evaluated simulation, not an observed human-review study.')
    fig, ax = plt.subplots(figsize=(8.5, 5.7))
    rows = r['H3']['large']
    for i, row in enumerate(rows):
        ax.plot([row['previous']['lower'], row['previous']['upper']], [i, i], linewidth=4, alpha=.4,
                label='Prior interval' if i == 0 else None)
    ax.plot([x['proposed']['lower'] for x in rows], list(range(len(rows))), 'o', label='Exact frontier = analytic oracle')
    ax.set(yticks=list(range(len(rows))), yticklabels=[f"{x['kind']} / {x['n']} atoms" for x in rows],
           xlim=(0, 1.05), xlabel='Supplied-model probability', title='H3 | Small frontier, exact large connected lineage')
    ax.invert_yaxis()
    ax.legend(loc='upper right', fontsize=9)
    save(fig, '03_frontier_lineage', 'Adjacent-pair proofs; supplied independent primitive probabilities 0.1.\nAll ten intervals tighten; this does not validate document independence.')
    fig, ax = plt.subplots(figsize=(8.5, 5.7))
    rows = r['H4']['large']
    ax.barh(list(range(len(rows))), [x['proposed']['utility'] for x in rows], label='Certified optimum')
    ax.scatter([x['previous']['utility'] for x in rows], list(range(len(rows))), marker='x', label='Prior bounded policy')
    ax.set(yticks=list(range(len(rows))), yticklabels=[f"{x['kind']} / {x['n']} vertices" for x in rows],
           xlabel='Supplied priority utility', title='H4 | Bipartite structure removes a staging boundary')
    ax.invert_yaxis()
    ax.legend(loc='upper right', fontsize=9)
    save(fig, '04_bipartite_certificate', 'Each objective matches an analytic optimum and a feasible-flow/cover certificate.\nTractable controlled graph families; structural utility is not factual correctness.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    local, global_case = r['H5']['local_workload'], r['H5']['global_source_control']
    bars = ax.bar(['Local / full', 'Local / indexed', 'Global / full', 'Global / indexed'],
                  [local['full_evaluations'], local['incremental_evaluations'], global_case['full_evaluations'], global_case['incremental_evaluations']])
    ax.bar_label(bars, fmt='%d', padding=3)
    ax.set(yscale='log', ylim=(100, 70000), ylabel='Fact reevaluations (log scale)',
           title='H5 | Local dependency invalidation saves work')
    save(fig, '05_source_cache', f"Includes cold build: local reduction {local['saving']:.2%}; global-source reduction {global_case['saving']:.2%}.\nFact evaluations are not end-to-end CPU time, latency or database I/O.")


def replace_after_anchor(text, body):
    text = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', '', text, flags=re.S)
    if text.count(ANCHOR) != 1:
        raise ValueError('Expected exactly one reliability section anchor')
    before, after = text.split(ANCHOR, 1)
    return before + ANCHOR + '\n\n' + START + '\n\n' + body.strip() + '\n\n' + END + '\n\n' + after.lstrip()


def update_paper(r):
    def rebase(match):
        url = match.group(1)
        if '://' in url or url.startswith('#'):
            return '](' + url + ')'
        path = (HERE / url).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Link outside repository')
        return '](../' + path.relative_to(ROOT).as_posix() + ')'
    section = re.sub(r'\]\(([^)]+)\)', rebase, render(r))
    path = ROOT / 'manuscript/paper-current.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'), section), encoding='utf-8', newline='\n')
    outcomes = '; '.join(f"H{i} {'met' if r[f'H{i}']['primary_target_met'] else 'did not meet'} its frozen target" for i in range(1, 6))
    note = ('## Five source-aware and structural improvements after PR #17\n\n'
            '[Executed report](graph_synthesis/source_structural/RESULTS.md), [frozen protocol](graph_synthesis/source_structural/PROTOCOL.md), '
            '[five figures](graph_synthesis/source_structural/figures/) and [complete updated paper](manuscript/paper-current.pdf). '
            + outcomes + '. Direct group-risk modeling and setup-cost-aware review fail their targets. '
            'Frontier lineage, certified bipartite optimization and revision-checked evidence invalidation meet controlled algorithmic targets. '
            'No fresh Jev calls, independent semantic validation, real reviewer cost measurements or production-policy changes. '
            'Negative results, correlated-detection and global-source controls are retained.')
    path = ROOT / 'CURRENT_RESULTS.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'), note), encoding='utf-8', newline='\n')


def manifest():
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.name != 'artifact-manifest.json'}
    write(HERE / 'artifact-manifest.json', {'sha256': files,
          'note': 'Source-structure extension; excludes self-reference. Mutable shared manuscript uses its build manifest.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true')
    parser.add_argument('--update-paper', action='store_true')
    args = parser.parse_args()
    r = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
    (HERE / 'RESULTS.md').write_text(render(r), encoding='utf-8', newline='\n')
    with (HERE / 'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['hypothesis', 'title', 'primary_target_met', 'fresh_service_calls'])
        for i, title in enumerate(TITLES, 1):
            writer.writerow([f'H{i}', title, r[f'H{i}']['primary_target_met'], 0])
    if args.figures:
        figures(r)
    if args.update_paper:
        update_paper(r)
    manifest()
    print('Generated source-structure report, table, figures and additive complete-paper section')


if __name__ == '__main__':
    main()
