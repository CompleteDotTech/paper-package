"""Evidence-derived figures and an additive complete-manuscript update."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
from .run import ROOT, HERE, sha, write

START = '<!-- CERTIFICATES_RESEARCH_START -->'
END = '<!-- CERTIFICATES_RESEARCH_END -->'
ANCHOR = '<!-- RELIABILITY_RESEARCH_END -->'
TITLES = ['Source random-effects forecasting', 'Dependence-aware lineage bounds', 'Bipartite flow certificates', 'Repair-invariant queries', 'Delta-indexed graph updates']
CLASSES = ['Previously inspected saved-response forecasts', 'Supplied finite probability models', 'Supplied conflict graphs and integer priorities', 'Priority-relative graph-repair semantics', 'In-memory controlled graph mutations']


def outcome(h):
    return 'Met' if h['primary_target_met'] else 'Not met'


def insert(text, body):
    text = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*', '', text, flags=re.S)
    if text.count(ANCHOR) != 1:
        raise ValueError('Expected exactly one reliability-section anchor')
    before, after = text.split(ANCHOR, 1)
    return before + ANCHOR + '\n\n' + START + '\n\n' + body.strip() + '\n\n' + END + '\n\n' + after.lstrip()


def render(r):
    a, b, c, d, e = [r[f'H{i}'] for i in range(1, 6)]
    old, new = a['scores']['pooled_independent'], a['scores']['random_effects']
    ci = lambda xs: '[' + ', '.join(f'{v:+.6f}' for v in xs) + ']'
    out = ['# Dependence-aware certificates for Jev graph synthesis', '',
           'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026', '',
           '## Abstract', '',
           f"Five frozen exploratory tests extend the graph pipeline beyond independent-source assumptions and a single chosen repair. A development-fitted beta-binomial source model changes contamination Brier from {old['brier']:.6f} to {new['brier']:.6f}, a {a['brier_relative_improvement']:.2%} reduction; its primary target is {outcome(a).lower()}. Dependence-aware probability bounds prevent {b['false_admissions_prevented']}/20 independence-induced false admissions in supplied correlated-source controls. Integer flow certificates recover all seven analytic bipartite optima, including 2,048-vertex cycles previously staged. Query classification agrees with finite enumeration, and delta-indexed updates match full recomputation across {e['mutations']} random mutations. Declared boundary graph-element visits fall by {e['local_workload']['saving']:.2%} on the fixed local-update workload, but by {e['connected_control']['saving']:.2%} on its connected control. These are conditional algorithm and saved-response findings, not new Jev semantic-accuracy evidence or a comparison against KARMA.", '',
           '## 1. Motivation, novelty boundary and frozen methodology', '',
           'The preceding [reliability study](../reliability/RESULTS.md) exposed three limitations: its calibration multiplier worsened Brier; exact lineage probabilities remained conditional on independent primitives; and incremental maintenance still scanned the global snapshot. Its conflict optimizer also returned one optimum and staged components outside its cutset/cap limits. The five extensions here test these specific gaps without changing candidate extraction, accepted Jev edges or production policy.', '',
           'The inspected repository inventory did not contain these five integrated experiments. This is a **repository-scoped new-experiment claim, not a worldwide first-attempt claim**. Beta-binomial random effects, extremal-probability linear programs, weighted bipartite covers, consistent query answering across repairs and incremental maintenance all have antecedents. A targeted primary-source search and its references are recorded in the [protocol](PROTOCOL.md). Established ingredients do not become novel algorithms merely through new names or integration.', '',
           f"Protocol commit `{r['protocol_commit']}` precedes this suite's implementation/execution; the inspected baseline is `{r['baseline_commit']}`. Hypotheses were informed by already public results, so this is exploratory follow-up rather than independent preregistration. H1 reuses {r['development']['n']} development candidates in {r['development']['groups']} groups and {r['test']['n']} previously inspected evaluation candidates in {r['test']['groups']} disjoint groups. Saved calls are reconstructed and hashes checked before use. **Fresh service calls: {r['fresh_service_calls']}.** H2-H5 use controlled fixtures rather than additional Jev observations.", '',
           '| Hypothesis | Frozen primary requirement | Result | Evidence class |',
           '|---|---|---|---|']
    targets = ['At least 10% lower Brier than same-marginal independence, absolute bias <=0.03, and no regression versus prior feature risk',
               'Zero finite-oracle/bound/invariance failures; prevent all 20 correlated-source false admissions',
               'Zero finite-oracle/certificate failures, no small-case regression, all seven large analytic optima recovered',
               'Zero classification/witness failures; preserve all oracle-certain answers and reject the tie-control false certainty',
               'Zero mutation mismatches/invalid-state changes; at least 75% fewer declared boundary visits on the frozen local workload']
    for i in range(1, 6):
        out.append(f'| H{i}: {TITLES[i-1]} | {targets[i-1]} | {outcome(r[f"H{i}"])} | {CLASSES[i-1]} |')
    out += ['', 'These outcomes must not be combined into a semantic success percentage. A failed conjunction remains failed even when one endpoint improves.', '',
            '## 2. H1: Source-random-effects contamination forecasts', '',
            'For each source, n counts base1 SUPPORTS/REFUTES decisions and k counts disagreements with the stored gold relation label. Empty accepted groups are excluded. The development-only marginal error estimate is (sum(k)+0.5)/(sum(n)+1). A grid of intraclass correlations {0,0.01,0.05,0.1,0.2,0.4,0.6,0.8} is selected by beta-binomial development log likelihood with a lower-correlation tie rule. At positive rho, alpha=mu(1/rho-1) and beta=(1-mu)(1/rho-1); contamination is 1-B(alpha,beta+n)/B(alpha,beta). The rho=0 comparator has the identical marginal estimate and uses 1-(1-mu)^n. Predictions consume only source exposure counts, not evaluation labels.', '',
            f"Development selects mu={a['fit']['mu']:.6f} and rho={a['fit']['rho']:g}. All {len(a['leave_group_out'])} source-excluded development sensitivity fits are retained; held-out source IDs do not enter their training fits. Evaluation uses {new['n']} nonempty source groups, of which {a['test_singleton_groups']} are singletons. Singletons cannot distinguish these dependence models at fixed marginal error rate.", '',
            '| Forecast | Brier | Clipped log loss | Predicted contaminated | Observed contaminated | Bias |',
            '|---|---:|---:|---:|---:|---:|']
    for key, name in [('prior_features', 'Prior feature-risk model'), ('prior_multiplier', 'Prior development-selected multiplier'), ('pooled_independent', 'Same-marginal independence'), ('random_effects', 'Source random effects')]:
        s = a['scores'][key]
        out.append(f"| {name} | {s['brier']:.6f} | {s['log_loss']:.6f} | {s['mean_predicted']:.2%} | {s['mean_observed']:.2%} | {s['bias']:+.2%} |")
    out += ['', f"The new-minus-same-marginal Brier difference is {a['paired_brier']['point']:+.6f}; its descriptive paired 95% interval is {ci(a['paired_brier']['95'])}, and its 99% interval is {ci(a['paired_brier']['99'])}. The frozen conjunction is **{outcome(a).lower()}**. The forecast can improve relative to its matched marginal comparator while still failing the improvement threshold or regressing versus the richer prior feature model. No accepted edge is changed.", '',
            'Positive correlation lowers the probability of at least one error at fixed marginal error probability and exposure, because errors cluster rather than spread across groups. It does not universally make an underpredicted contamination rate more accurate. The fitted exchangeable beta-binomial model is neither a distribution-shift guarantee nor a calibration certificate.', '',
            '![H1. All forecasts scored on the same 98 nonempty evaluation source groups.](figures/01_source_risk.png)', '',
            '## 3. H2: Lineage bounds without assumed independence', '',
            'A monotone DNF formula is evaluated over at most 1,024 Boolean worlds for at most ten atoms. Nonnegative world masses sum to one and satisfy supplied marginal and optional conjunction constraints. Two linear programs minimize and maximize the DNF truth indicator. They use SciPy HiGHS; solver failures, infeasibility and capacity excess return [0,1] with no admission certificate. These probabilities are supplied model inputs, not Jev scores reinterpreted as fact probabilities.', '',
            'For a minimization objective c, equality matrix A, target b and returned dual y, c dot z >= b dot y + min(0,min(c-A-transpose y)) for every feasible simplex vector z. The implementation subtracts an additional 1e-9 times (1+sum(abs(y))) outward pad. It saves primal support, duals and residuals. This is a checked, outward-padded floating-point bound conditional on supplied constraints, **not formal interval-arithmetic verification or an unconditional truth guarantee**.', '',
            f"The {len(b['random_cases'])} seeded arbitrary-joint fixtures have {b['failures']} containment, constraint-monotonicity, invariance or control failures. The {len(b['frechet_grid'])} two-event OR/AND grid cases match their analytic Frechet bounds within 1e-8. Mean interval width is {b['mean_width_marginals']:.6f} using marginals alone and {b['mean_width_with_joint']:.6f} with one valid conjunction constraint. The primary target is **{outcome(b).lower()}**.", '',
            '| Two 0.8-marginal sources supporting an OR | Probability or interval | Admission at 0.95 |',
            '|---|---:|---|',
            '| Assume independence without justification | 0.96 | Yes; false under perfect correlation |',
            '| Actual perfectly correlated sources | 0.80 | No |',
            '| Marginals only, arbitrary dependence | Approximately [0.80,1.00] | No |',
            '| Explicit joint probability 0.80 | Approximately [0.80,0.80] | No |',
            '| Explicit joint probability 0.64 | Approximately [0.96,0.96] | Yes, conditional on this constraint |', '',
            f"Across 20 marginal settings, the method prevents {b['false_admissions_prevented']} false admissions from an unjustified independence assumption. It also withholds {b['independent_true_admissions_withheld_without_joint']} genuinely high-probability admissions when only marginals are provided, and recovers {b['known_independence_admissions_recovered']} when the correct joint constraint is supplied. That conservatism is a real information tradeoff, not free accuracy. Infeasible and 11-atom cases stage. The false-premise control supplies 0.99 for an actually 0.50-probability atom; the resulting conditional bound still admits it. Arithmetic cannot repair incorrect evidence metadata.", '',
            '![H2. The correlated-source negative control separates assumed independence from valid lower bounds.](figures/02_dependence_bounds.png)', '',
            '## 4. H3: Integer-flow certificates for bipartite conflicts', '',
            'A bipartite conflict component is reduced to minimum weighted vertex cover: source-to-left and right-to-sink capacities are supplied priorities, and conflict arcs have capacity one greater than total priority. An integer max-flow/min-cut certificate gives a minimum cover; its complement is a maximum-weight independent set. The verifier reconstructs the original network, checks capacity bounds and conservation, proves flow equals cut capacity, checks the cover/independent-set relationship and verifies the reported utility. No hidden tie-breaking weight perturbation changes the objective.', '',
            'The new route supports components up to 2,048 vertices and 50,000 edges. Non-bipartite components use the actual prior cutset solver with its original limits; unsupported cases stage rather than silently accepting a heuristic solution. These are explicit conflict graphs, not newly extracted relationships.', '',
            f"All {len(c['random_bipartite'])} small bipartite cases match independent subset enumeration and their flow certificates. Another {len(c['general_small'])} small general graphs have no utility regression. Reordering or repeating edges preserves outputs. Total failures: {c['failures']}. The primary target is **{outcome(c).lower()}**.", '',
            '| Analytic topology | Vertices | Edges | Previous utility | New utility | Oracle utility |',
            '|---|---:|---:|---:|---:|---:|']
    for row in c['large']:
        out.append(f"| {row['kind'].replace('_',' ')} | {row['n']} | {row['edges']} | {row['prior_utility']} | {row['result']['utility']} | {row['oracle']} |")
    out += ['', 'Complete-bipartite fixtures assign priority 3 on one balanced side and 2 on the other; cycles use unit priorities. Prior zero utility means staged, not an incorrect accepted graph. The 2,050-cycle and 50,176-edge complete-bipartite controls stage; a 17-cycle still uses the prior exact route, while the dense 17-clique remains unsupported. A false assertion of priority 9 still defeats a true conflicting assertion of priority 8. Certified optimality concerns supplied priorities, not semantic truth.', '',
            '![H3. Previously staged analytic conflict components are solved exactly with integer certificates.](figures/03_bipartite_capacity.png)', '',
            '## 5. H4: Queries invariant across admissible graph repairs', '',
            'Let U be maximum supplied priority. Admissible repairs are all independent sets with utility at least U-epsilon, using epsilon=0 and floor(0.05U). For a conjunction of up to eight required vertices, constrained inclusion tests whether some admissible repair contains the conjunction. Constrained exclusion of each required vertex tests whether any admissible repair falsifies it. Answers are certain, ambiguous or impossible, with an explicit counterexample for ambiguity. Staged optimization propagates unsupported status rather than false certainty.', '',
            f"Across {len(d['cases'])} seeded general graphs and two tolerance settings, classifications and witnesses have {d['failures']} oracle failures. Every oracle-certain answer is retained and larger tolerance creates no new certain answers. Among exact-optimum random cases, {d['random_single_optimum_false_certainty']} affirmative answers from one selected optimum are not invariant across all optima. The explicit equal-weight conflict control also returns an alternative repair that falsifies the chosen optimum's affirmative answer. Primary target: **{outcome(d).lower()}**.", '',
            '| Repair tolerance | Certain conjunctions | Ambiguous conjunctions | Impossible conjunctions |',
            '|---|---:|---:|---:|']
    for key, label in [('exact', 'Exact maximum priority'), ('tolerant', 'Within floor(5% of optimum)')]:
        counts = d['counts'][key]
        out.append(f"| {label} | {counts['certain']} | {counts['ambiguous']} | {counts['impossible']} |")
    out += ['', 'Some sampled conjunctions are empty and hence tautological; these counts describe the fixture distribution, not a population query-success rate. Conflicting conjunctions are impossible. Zero-priority optional vertices can be ambiguous. The high-priority false assertion is still repair-certain under its supplied objective: repair certainty must not be presented as factual certainty.', '',
            '![H4. Query status across exact and near-optimal admissible repairs.](figures/04_repair_queries.png)', '',
            '## 6. H5: Delta-indexed maintenance without global snapshot rescans', '',
            'The in-memory index validates an initial graph and maintains private adjacency, priorities, component membership and cached solutions. An explicit mutation API supports weight changes, vertex insertion/deletion and edge insertion/deletion. It copies, validates, discovers and solves only affected old components and their replacements before publication. Bridge insertion joins two scopes; bridge or vertex deletion discovers splits inside the affected old scope. Unaffected solutions are reused. Mutations return selection/staging deltas and aggregate utility rather than forcing a full graph materialization. Snapshot audit is a separate operation.', '',
            f"Independent full-snapshot mutation and optimization checks find {e['failures']} failures across {e['mutations']} seeded mutations, deliberate bridge controls and locality/stress workloads. Each of the five mutation types appears {e['operation_counts']['weight']} times in the randomized test. Invalid mutations produce {e['invalid_state_changes']} state changes; tests also inject a solver exception before publication. This is not a concurrent or durable database transaction protocol.", '',
            '| Workload, including cold build | Delta-index boundary visits | Full-rescan boundary visits | Reduction |',
            '|---|---:|---:|---:|']
    for key, name in [('local_workload', '512 eight-vertex components; 128 local updates'), ('connected_control', 'One 64-vertex component; 128 updates')]:
        v = e[key]
        out.append(f"| {name} | {v['local_work']:,} | {v['full_work']:,} | {v['saving']:.2%} |")
    out += ['', f"The frozen primary target is **{outcome(e).lower()}**. The comparator uses the same optimizer but copies, validates, discovers and prepares every component on every update. The boundary metric counts declared passes for graph copying, validation, discovery, solver input, mutation validation and publication. It explicitly excludes sorting, optimizer-internal work, certificate-check work and the audit materialization. Therefore the percentage is **not** a measured reduction in all CPU operations, service latency or database I/O. It improves on the previous study's solver-vertex-only scope, but is still an instrumented boundary measure.", '']
    timing_path = HERE / 'timings.json'
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding='utf-8'))
        out += ['### Separate single-host timing measurements', '',
                'Three repetitions alternate policy order. Timings include cold construction and 64 updates, but exclude snapshot comparison for both policies. Medians below are descriptive, not a primary endpoint or a portable speed guarantee. All individual measurements and environment details are retained in [timings.json](timings.json).', '',
                '| Components | Vertices | Delta-index median seconds | Full-rescan median seconds | Ratio |',
                '|---:|---:|---:|---:|---:|']
        for row in timing['cases']:
            local, full = row['median_seconds']['local'], row['median_seconds']['full']
            out.append(f"| {row['components']} | {row['vertices']} | {local:.6f} | {full:.6f} | {full/local:.2f}x |")
        out += ['']
    out += ['![H5. Benefits depend on component locality; the connected control has no counted-work saving.](figures/05_delta_locality.png)', '',
            '## 7. Interpretation, uncertainty and falsifying controls', '',
            'H1 uses 4,000 paired source-group bootstrap draws with seed 20260922 and fixed fitted policies. The 95% and 99% percentile intervals are descriptive, not simultaneous; they omit fitting uncertainty and cannot undo repeated use of the same evaluation corpus. Neither a favorable score nor a passed point threshold would establish out-of-distribution calibration. H2-H5 finite/analytic fixtures test implementation behavior under supplied assumptions rather than estimates of Jev accuracy.', '',
            'The retained negative controls are essential: incorrect marginal probabilities defeat lineage certificates; false priorities defeat semantic interpretation of flow certificates and repair certainty; uncertain dependence withholds some valid admissions; unsupported topologies stage; and connected updates remove locality savings. The structural methods remain opt-in research prototypes. Candidate-generation recall, semantic relation qualifiers, source independence discovery and real database behavior are not solved by this suite.', '',
            'The next independent semantic claim still requires a policy frozen before inspecting a new source-disjoint, independently adjudicated corpus, and matched evidence/resource budgets against an implemented external system such as KARMA. This suite does not claim that such a comparison ran.', '',
            '## 8. Reproducibility and artifact integrity', '',
            '```bash',
            'python -m pip install -r graph_synthesis/certificates/requirements.txt',
            'python -B -m graph_synthesis.certificates.run --timings',
            'python -B -m unittest discover -s graph_synthesis/certificates/tests -v',
            'python -B -m graph_synthesis.certificates.run --check',
            'python -B -m graph_synthesis.certificates.report --figures --update-paper',
            'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf',
            '```', '',
            'The [machine-readable results](results.json) preserve fit candidates, held-source exclusions, predictions, complete fixture inputs, joint-world probabilities, LP witnesses, graph certificates, mutation events, oracle outputs and source hashes. Timings are deliberately separate from deterministic replay. Five SVG/PNG figure pairs and a summary CSV are regenerated from recorded results; the extension manifest hashes its source and artifacts. Original raw evidence and the archived manuscript remain unchanged, and the complete current manuscript retains every preceding study.', '',
            '## 9. Primary foundations', '',
            '- [SciPy beta-binomial definition](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.stats.betabinom.html) and [HiGHS linear programming and dual marginals](https://docs.scipy.org/doc/scipy-1.17.0/reference/optimize.linprog-highs.html).',
            '- [Optimal Union Probability Interval Is NP-Hard](https://arxiv.org/abs/2605.03556), situating finite-world extremal-probability programs and their complexity.',
            '- [Distributed CONGEST Approximation of Weighted Vertex Covers and Matchings](https://arxiv.org/abs/2111.10577), an antecedent for weighted bipartite cover formulations.',
            '- [Computational Complexity of Preferred Subset Repairs on Data-Graphs](https://arxiv.org/abs/2402.09265) and [Consistent Query Answers in the Presence of Universal Constraints](https://arxiv.org/abs/0809.1551).',
            '- [A Feature-based Classification of Model Repair Approaches](https://arxiv.org/html/1504.03947v1) and the [TypeSafe typed-decision interface](https://docs.typesafe.ai/introduction).', '',
            'These sources motivate established components; they do not validate this implementation or certify worldwide novelty.']
    return '\n'.join(out) + '\n'


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams['svg.hashsalt'] = 'jev-certificates-20260922'
    directory = HERE / 'figures'
    directory.mkdir(exist_ok=True)
    def save(fig, name, note):
        fig.text(.5, .025, note, ha='center', va='bottom', fontsize=9)
        fig.tight_layout(rect=(0, .15, 1, 1))
        fig.savefig(directory / (name + '.svg'), metadata={'Date': None})
        fig.savefig(directory / (name + '.png'), dpi=200, metadata={'Software': 'Jev certificate research'})
        plt.close(fig)
    h = r['H1']
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    keys = ['prior_features', 'prior_multiplier', 'pooled_independent', 'random_effects']
    bars = ax.bar(['Prior features', 'Prior multiplier', 'Same-marginal\nindependence', 'Source random\neffects'], [h['scores'][k]['brier'] for k in keys])
    ax.bar_label(bars, fmt='%.4f')
    ax.set(ylabel='Group-contamination Brier (lower is better)', ylim=(0, .18), title='H1 | Dependence helps one comparator, not the frozen target')
    save(fig, '01_source_risk', f"{h['scores']['random_effects']['n']} previously inspected nonempty source groups; rho={h['fit']['rho']:g} fit on development only.\nImprovement threshold and stronger prior comparator remain part of the conjunction.")
    h = r['H2']['dependence_controls'][0]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bars = ax.bar(['Unjustified\nindependence', 'Actual correlated\nprobability', 'Dependence-aware\nlower bound'], [h['independence_assumed'], h['correlated_truth'], h['unknown_dependence']['lower']])
    ax.bar_label(bars, fmt='%.2f')
    ax.axhline(.95, linestyle='--', label='Admission threshold 0.95')
    ax.set(ylabel='Supplied-model probability', ylim=(0, 1.12), title='H2 | Unknown dependence prevents a false high-confidence admission')
    ax.legend(loc='lower right')
    save(fig, '02_dependence_bounds', 'Two perfectly correlated sources each have marginal probability 0.80.\nMarginals alone imply approximately [0.80, 1.00], not 0.96; bad supplied probabilities remain unsafe.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for kind, label, marker in [('complete_bipartite', 'Complete bipartite: solver = analytic optimum', 's'), ('even_cycle', 'Even cycles: solver = analytic optimum', 'o')]:
        rows = [x for x in r['H3']['large'] if x['kind'] == kind]
        ax.plot([x['n'] for x in rows], [x['result']['utility'] for x in rows], marker=marker, label=label)
    rows = r['H3']['large']
    ax.plot([x['n'] for x in rows], [x['prior_utility'] for x in rows], linestyle='--', label='Prior policy: all staged')
    ax.set(xscale='log', xlabel='Vertices in one conflict component (log scale)', ylabel='Supplied-priority utility', title='H3 | Exact integer-flow route expands supported graph capacity')
    ax.legend(fontsize=9)
    save(fig, '03_bipartite_capacity', 'Seven analytic fixtures; complete bipartite priorities 3 versus 2, cycle priorities 1.\nCapacity is not evidence of better semantic relation extraction.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    x = np.arange(3)
    for offset, key, label in [(-.2, 'exact', 'Exact-optimum repairs'), (.2, 'tolerant', 'Within floor(5% of optimum)')]:
        bars = ax.bar(x + offset, [r['H4']['counts'][key][k] for k in ('certain', 'ambiguous', 'impossible')], width=.4, label=label)
        ax.bar_label(bars)
    ax.set(xticks=x, xticklabels=['Certain', 'Ambiguous', 'Impossible'], ylabel='Conjunctive query fixtures', ylim=(0, 90), title='H4 | Certainty is evaluated across repairs, not one chosen graph')
    ax.legend()
    save(fig, '04_repair_queries', '128 fixed small-graph queries; includes empty conjunctions.\nRepair-relative certainty remains conditional on supplied priorities, not factual truth.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    h = r['H5']
    bars = ax.bar(['512-component local workload', 'Single connected component'], [100 * h['local_workload']['saving'], 100 * h['connected_control']['saving']])
    ax.bar_label(bars, fmt='%.2f%%')
    ax.set(ylabel='Reduction in declared boundary visits (%)', ylim=(0, 115), title='H5 | Delta-index benefits disappear when every update touches the graph')
    save(fig, '05_delta_locality', 'Cold build plus 128 updates; counts include validation/discovery/publication boundaries.\nOptimizer internals and sorting are excluded; these are not end-to-end latency percentages.')


def update_paper(r):
    def rebase(match):
        url = match.group(1)
        if '://' in url or url.startswith('#'):
            return '](' + url + ')'
        path = (HERE / url).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Link outside repository')
        return '](../' + path.relative_to(ROOT).as_posix() + ')'
    body = re.sub(r'\]\(([^)]+)\)', rebase, render(r))
    path = ROOT / 'manuscript/paper-current.md'
    path.write_text(insert(path.read_text(encoding='utf-8'), body), encoding='utf-8', newline='\n')
    outcomes = '; '.join(f"H{i} {outcome(r[f'H{i}']).lower()}" for i in range(1, 6))
    note = ('## Five dependence-aware certificate experiments after PR #17\n\n'
            '[Executed report](graph_synthesis/certificates/RESULTS.md), [frozen protocol](graph_synthesis/certificates/PROTOCOL.md), '
            '[five figures](graph_synthesis/certificates/figures/) and [complete updated paper](manuscript/paper-current.pdf). '
            + outcomes + '. Source-random-effects forecasting is saved-response reuse; lineage bounds, flow certificates, repair queries and delta updates are controlled algorithms. '
            'No fresh Jev calls, worldwide novelty claim, new semantic-accuracy claim or production-policy change. Negative and assumption-breaking controls are retained.')
    path = ROOT / 'CURRENT_RESULTS.md'
    path.write_text(insert(path.read_text(encoding='utf-8'), note), encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true')
    parser.add_argument('--update-paper', action='store_true')
    args = parser.parse_args()
    r = json.loads((HERE / 'results.json').read_text(encoding='utf-8'))
    (HERE / 'RESULTS.md').write_text(render(r), encoding='utf-8', newline='\n')
    with (HERE / 'summary.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['hypothesis', 'title', 'primary_target', 'evidence_class'])
        for i in range(1, 6):
            writer.writerow([f'H{i}', TITLES[i-1], outcome(r[f'H{i}']), CLASSES[i-1]])
    if args.figures:
        figures(r)
    if args.update_paper:
        update_paper(r)
    paths = sorted(p for p in HERE.rglob('*') if p.is_file() and p.name != 'artifact-manifest.json' and '__pycache__' not in p.parts)
    write(HERE / 'artifact-manifest.json', {'sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}})
    print('Certificate report, figures and manuscript section generated from recorded evidence')


if __name__ == '__main__':
    main()
