"""Regenerate five figures and an additive, evidence-bounded full-paper section."""
from __future__ import annotations
import argparse
import csv
import json
import re
from statistics import mean
from .run import HERE, ROOT, sha, write

START = '<!-- UNCERTAINTY_RESEARCH_START -->'
END = '<!-- UNCERTAINTY_RESEARCH_END -->'
ANCHOR = '<!-- STRUCTURAL_RESEARCH_END -->'
TITLES = ['Dependence-agnostic lineage', 'Skeptical repair backbone', 'Query-loss-directed review',
          'Minimum-collateral retraction', 'Grounded recursive evidence']
FIGURES = ['01_dependence', '02_repair_backbone', '03_query_review', '04_retraction', '05_grounding']


def review_means(h):
    rows = []
    for j, budget in enumerate((1, 2)):
        rows.append({'budget': budget, **{p: mean(c['budgets'][j][p]['loss'] for c in h['cases'])
                                         for p in ('risk', 'entropy', 'proposed')},
                     'noisy_proposed': mean(c['budgets'][j]['noisy_proposed_loss'] for c in h['cases']),
                     'noisy_risk': mean(c['budgets'][j]['noisy_risk_loss'] for c in h['cases'])})
    return rows


def render(r):
    a, b, c, d, e = [r[f'H{i}'] for i in range(1, 6)]
    status = lambda h: 'Met' if h['primary_target_met'] else 'Not met'
    out = ['# Uncertainty, repair ambiguity and grounded evidence in Jev graph synthesis', '',
           'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026', '',
           '## Abstract', '',
           f"Five controlled experiments address assumptions exposed by the preceding reliability study. Dependence-agnostic lineage yields {a['false_admissions']} lower-bound false admissions versus {a['independent_false_admissions']} under an independence model on {len(a['cases'])} supplied joint-distribution fixtures. Skeptical repair keeps {b['necessary_assertions']} necessary assertions rather than {b['selected_assertions']} assertions from deterministic single optima; this is an explicit ambiguity/coverage tradeoff. Query-loss-directed review lowers aggregate residual query Brier loss by {c['relative_loss_reduction']:.2%} versus primitive-risk ranking at two ideal reviews. Minimum-collateral retraction lowers collateral by {d['relative_collateral_reduction']:.2%} on {d['matched_feasible_cases']} matched feasible fixtures. Grounded materialization matches finite-model entailment across {e['snapshot_evaluations']:,} snapshots and removes cyclic phantom support. All results are conditional engineering outcomes, not new Jev accuracy measurements. Wrong marginals, false priorities, misspecified review priors, incomplete provenance and false base assertions remain falsifying controls.", '',
           '## 1. Research question, prior evidence and novelty boundary', '',
           'The [preceding reliability study](../reliability/RESULTS.md) demonstrated that exact lineage arithmetic cannot repair false independence, priority-optimal graph repair can choose a false assertion, and incremental correctness depends on explicit dependencies. Its review experiments measured source contamination rather than loss in downstream queries. These observations motivate the present five hypotheses. We do not rerun calibration, voting, routing or the previous cycle-cutset benchmark under new names.', '',
           f"The [protocol](PROTOCOL.md) was committed as `{r['protocol_commit']}` before execution, against baseline `{r['baseline_commit']}`. The seed {r['seed']} is an arbitrary integer, not a collection date. Existing results informed the hypotheses; this is exploratory follow-up, not independent preregistration. **Fresh Jev calls: {r['fresh_service_calls']}. New scientific documents: {r['new_scientific_documents']}.** No default compiler or production graph policy changes. Every benchmark here uses supplied algorithmic fixtures or decision-theoretic models, not extraction from new papers or observed human review.", '',
           'These specific integrations were not found in the reviewed package protocols. A bounded search cannot establish that an idea has never been attempted anywhere. Possible-world probabilistic reasoning is established prior art ([Grosof](https://arxiv.org/abs/1304.3418), [Bacchus](https://arxiv.org/abs/1304.2341)); so are [repair-based query answering](https://doi.org/10.1016/j.tcs.2022.09.005), [query causality](https://arxiv.org/abs/0912.5340), [minimal-deletion resilience](https://arxiv.org/abs/1507.00674), [value of information](https://pmc.ncbi.nlm.nih.gov/articles/PMC7612603/) and [Horn-rule semantics](https://www.w3.org/TR/rif-core/). The contribution is a new package-level implementation and falsification suite, not invention of those methods. No head-to-head comparison with [KARMA](https://arxiv.org/abs/2502.06472) is performed.', '',
           '| Hypothesis | Frozen primary target | Outcome | Evidence population |',
           '|---|---|---|---|']
    targets = ['No containment/oracle/false-admission errors; prevent shared-source control and retain valid singleton',
               'Exact all-optima agreement; preserve unique optimum; stage arbitrary tie members',
               'Zero oracle regret and at least 20% lower query loss at budget two',
               'Exact feasible objective, no protected loss, at least 25% less matched collateral',
               'Exact finite-model entailment, eliminate unsupported cycles, preserve grounded backup']
    populations = ['128 joint fixtures + 16 rational oracles', '128 conflict graphs + 512 order checks',
                   '64 independent-event/query fixtures', '128 proof-lineage fixtures', '96 rule programs / 1,152 snapshots']
    for i in range(5):
        out.append(f'| H{i+1}: {TITLES[i]} | {targets[i]} | {status(r[f"H{i+1}"])} | {populations[i]} |')
    out += ['', 'Meeting an engineering target is not evidence that five new semantic improvements have been discovered. Generator-specific effects and assumption-breaking controls must be read together.', '',
            '## 2. H1: Dependence-agnostic lineage admission', '',
            'A conclusion has a monotone disjunctive-normal-form proof: any listed conjunction of primitive events is sufficient. The former exact-lineage method multiplied independent primitive probabilities. Here the one-atom marginals are supplied, but dependence is left unspecified. With one nonnegative mass per Boolean world, impose total mass one and each marginal as an equality. Minimize and maximize the conclusion indicator over this feasible polytope. The resulting interval asks what is justified across all joint distributions compatible with those premises.', '',
            'The numerical prototype uses [SciPy linear programming](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html), at most eight used atoms, primal feasibility checks, repaired dual objective bounds and a 1e-8 outward allowance. These are numerical bounds, not formal real-arithmetic certificates. Failed or over-cap solves return dependence-free Frechet conjunction and union bounds. Duplicate and subsumed proofs are removed. No raw Jev score is promoted to a calibrated source reliability.', '',
            f"Across {len(a['cases'])} seeded joint-distribution fixtures there are {a['containment_failures']} containment errors, {a['invariance_failures']} duplicate/order errors and {a['false_admissions']} false lower-bound admissions at threshold 0.95. Exact independent-world evaluation instead gives {a['independent_false_admissions']} false admissions. On {len(a['oracle_cases'])} two/three-atom cases, a separate rational vertex-enumeration oracle finds {a['oracle_failures']} discrepancies beyond 1e-8. Mean interval width is {a['mean_analytic_width']:.6f} for the analytic fallback and {a['mean_credal_width']:.6f} for the LP bounds. Primary target: **{status(a).lower()}**.", '',
            '| Control | Result | Interpretation |', '|---|---|---|',
            '| Two 0.8-marginal events are actually identical | Independence gives 0.96; robust interval [0.8, 1.0]; actual 0.8 | Stage, rather than admit at 0.95 |',
            '| Accurate singleton marginal 0.99 | Lower bound 0.99 | A justified high-probability admission is retained |',
            '| Nine used atoms | Analytic fallback | No over-cap exactness claim |',
            '| Supplied singleton 0.99, actual 0.5 | Lower bound still 0.99 | Wrong marginals invalidate the premises |', '',
            'This is improved resistance to an unjustified independence assumption, not a guarantee against inaccurate priors, incomplete proofs or unknown extraction errors. A wide interval is intentionally retained when dependence is unidentified.', '',
            '![H1. False admissions at threshold 0.95 on supplied joint-distribution fixtures.](figures/01_dependence.png)', '',
            '## 3. H2: Skeptical optimal-repair backbone', '',
            'A one-best conflict optimizer selects one maximum-priority independent set, resolving ties by identifier. A tie-break is not evidence for one assertion over another. The proposed policy partitions assertions into necessary (in every optimum), possible (in at least one optimum) and excluded (in none). Only necessary assertions are unambiguously admissible under that objective. Constrained re-optimization produces an including and excluding witness for each ambiguous assertion.', '',
            'The solver is bounded to connected components of at most 16 vertices. Larger components stage explicitly and the returned full-graph utility is unknown, while solved-component results remain labeled as partial. This improves ambiguity representation, not scalability relative to the previous 256-vertex cutset solver. Priorities and conflicts are supplied; neither is inferred from semantic truth.', '',
            f"On {len(b['cases'])} seeded graphs, independent exhaustive subset enumeration finds {b['oracle_failures']} utility/membership/witness errors and {b['unique_optimum_losses']} unique-optimum losses. There are {b['invariance_failures']} failures over 512 order checks. Multiple optimal repairs occur in {b['ambiguous_cases']} cases. Deterministic single repairs select {b['selected_assertions']} assertions in total; the skeptical backbone retains {b['necessary_assertions']}, withholding {b['selected_assertions']-b['necessary_assertions']} tie-dependent selections. Primary target: **{status(b).lower()}**.", '',
            'An equal-priority conflicting pair is ambiguous while an isolated positive-priority assertion remains necessary. A 32-cycle is unsupported at the new cap. Critically, the unique false-priority control (false=9, true=8) still makes the false assertion necessary. Skepticism about optimization ties does not validate priorities or facts; coverage and supplied-priority utility can decrease.', '',
            '![H2. Selected versus necessary assertions across the supplied conflict graphs.](figures/02_repair_backbone.png)', '',
            '## 4. H3: Query-loss-directed evidence review', '',
            'Reviewing the most likely wrong primitive need not improve the answers that matter. Given supplied independent-event probabilities and three Boolean queries, choose a nonadaptive set of one or two primitive reviews minimizing expected residual query Brier loss. Perfect review reveals each selected event truthfully. The objective is the sum of expected conditional Bernoulli variances, equivalently expected squared error of the posterior query probabilities. Enumerate all review subsets within an eight-atom cap. No realized truth label enters selection.', '',
            'Compare against lowest primitive truth probability (highest error risk for an asserted primitive), highest primitive entropy, and no review. A separate world/observation squared-error computation checks every subset and optimum. The primary effect is against risk ranking; entropy is an additional, more uncertainty-aligned comparator, not silently omitted.', '',
            '| Reviews per fixture | Risk ranking | Entropy ranking | Query-directed | Query-directed with unmodeled 10% review noise |',
            '|---:|---:|---:|---:|---:|']
    for row in review_means(c):
        out.append(f"| {row['budget']} | {row['risk']:.6f} | {row['entropy']:.6f} | {row['proposed']:.6f} | {row['noisy_proposed']:.6f} |")
    ctrl = c['controls']['misspecified_prior']
    out += ['', f"Values are mean residual *summed* Brier loss for three queries per fixture, not classification error rates. Across {len(c['cases'])} fixtures, budget-two total loss falls from {c['budget2_risk_total_loss']:.6f} to {c['budget2_proposed_total_loss']:.6f}, a {c['relative_loss_reduction']:.2%} reduction. Oracle failures: {c['oracle_failures']}. Primary target: **{status(c).lower()}**. The paired mean difference has a descriptive 95% fixture-bootstrap interval [{c['paired_fixture_difference_95'][0]:.6f}, {c['paired_fixture_difference_95'][1]:.6f}] (2,000 draws). This interval describes the artificial generator only, not scientific-paper performance or human reviewers.", '',
            f"**Assumption-breaking result:** the misspecified-prior control makes the chosen review's actual loss {ctrl['actual_proposed_loss']:.4f}, worse than risk ranking's {ctrl['actual_risk_loss']:.4f}. The noisy-review rows keep the selector/posterior fixed while reviews undergo independent 10% bit flips; the model does not know this noise. Thus perfect-review gains are not robust guarantees. Costs are review counts only. No reviewer time, money, Jev-token cost or live service latency is inferred.", '',
            '![H3. Downstream query loss under equal ideal-review counts.](figures/03_query_review.png)', '',
            '## 5. H4: Minimum-collateral assertion retraction plans', '',
            'After external adjudication designates a conclusion for withdrawal, which candidate commitments should be staged? A plan must hit every supplied sufficient proof of the target while leaving at least one proof for each protected conclusion. Branching on an unhit target proof explores candidate withdrawals. Lexicographically minimize other lost conclusions, withdrawal cost, withdrawal count and sorted identifiers. Positive costs and monotone proof semantics justify pruning dominated partial plans. The cap is 14 atoms; unsupported or infeasible plans return no mutation.', '',
            'This is an opt-in plan over candidate commitments, not deletion of source documents or a claim that the selected commitments are false. Compare with withdrawing the union of every target-proof atom and a cost-first greedy hitting set. The independent oracle enumerates every possible withdrawal subset.', '',
            f"| Method | Feasible plans / 128 | Collateral on the same matched {d['matched_feasible_cases']} cases |", '|---|---:|---:|',
            f"| Union withdrawal | {d['union_feasible_cases']} | {d['union_collateral']} |",
            f"| Cost-first greedy | {d['greedy_feasible_cases']} | Not the frozen primary comparator |",
            f"| Minimum-collateral | {d['proposed_feasible_cases']} | {d['proposed_collateral']} |", '',
            f"There are {d['oracle_failures']} oracle/objective errors, {d['protected_losses']} protected/feasibility violations and {d['invariance_failures']} order errors. On the {d['matched_feasible_cases']} cases where both proposed and union plans are feasible, total collateral falls from {d['union_collateral']} to {d['proposed_collateral']}, or {d['relative_collateral_reduction']:.2%}. Primary target: **{status(d).lower()}**. The proposed method finds {d['proposed_feasible_cases']} feasible cases; the remaining {len(d['cases'])-d['proposed_feasible_cases']} are infeasible under the supplied protection constraints, matching exhaustive enumeration. Coverage is reported separately so abstention cannot masquerade as quality.", '',
            'The impossible-protection control stages rather than sacrificing the protected fact. The omitted-proof control leaves the target supported by an undisclosed alternative after a seemingly valid retraction. Incorrect external target adjudication can withdraw true commitments. These failures are not fixed by combinatorial optimality; complete lineage and correct intervention goals are essential.', '',
            '![H4. Collateral at matched feasible coverage; total feasibility is reported separately.](figures/04_retraction.png)', '',
            '## 6. H5: Grounded recursive evidence materialization', '',
            'Local support counts can leave a cycle apparently supported after its only external evidence disappears: A supports B and B supports A. For finite ground positive Horn rules, restart a worklist from current base assertions, decrement per-rule body counters as grounded atoms arrive, and fire a head only after every body atom is grounded. The process computes the least fixed point. It does not treat previously derived assertions as current bases. A separately implemented oracle intersects all finite interpretations satisfying the supplied bases and rules.', '',
            f"Across {len(e['cases'])} seeded programs and {e['snapshot_evaluations']:,} base snapshots, there are {e['oracle_failures']} finite-model disagreements and {e['invariance_failures']} duplicate/order disagreements. The local-support comparator leaves {e['naive_phantom_occurrences']} phantom assertion occurrences over these snapshots; these are repeated assertion/snapshot occurrences, not unique facts or observed model hallucinations. Comparator updates begin from the preceding correct state, isolating each withdrawal failure rather than accumulating prior mistakes. Primary target: **{status(e).lower()}**.", '',
            '| Cycle size | Phantom assertions after sole seed withdrawal: local support | Grounded materialization | Grounded with independent backup |',
            '|---:|---:|---:|---:|']
    for row in e['controls']['cycles']:
        out.append(f"| {row['n']} | {len(row['naive_after_withdrawal'])} | {len(row['proposed_after_withdrawal']['active'])} | {len(row['alternative_support']['active'])-1} |")
    out += ['', 'The backup column excludes the external backup atom itself. Every unsupported cycle is removed and every independently re-anchored cycle survives. Unseeded self-support also produces no fact. However, a false base assertion still grounds its rule consequences: entailment is conditional on the supplied bases and rules, not verification of real-world truth. Body-visit counts measure this in-memory materialization work, not database I/O, end-to-end update speed or Jev latency. This work recomputes grounding; it does not claim an incremental complexity improvement.', '',
            '![H5. Unsupported cycle members retained after the only external seed is removed.](figures/05_grounding.png)', '',
            '## 7. Interpretation, limitations and next falsification boundary', '',
            'The results support five bounded engineering capabilities: represent unidentified dependence honestly; distinguish necessary from arbitrary optimal selections; aim ideal reviews at downstream queries; minimize intervention collateral under explicit protection; and reject cyclic self-support without an external base. They do not establish new relation-extraction accuracy, calibrated real-world primitive reliabilities, automatic conflict discovery, trustworthy adjudication or better performance than KARMA. Exact small-instance objectives and known query priors favor these exhaustive prototypes, whose cost and coverage limits are explicit.', '',
            'All five primary criteria are conjunctions frozen before execution and are evaluated without changing their thresholds. They are not five independent scientific discoveries or a pooled success rate. H1/H2/H4/H5 use finite-oracle tests rather than statistical population tests. H3 uses one descriptive, unadjusted generator-level bootstrap interval; it is not a prospective semantic confidence interval. Negative controls remain alongside favorable primary results.', '',
            'A future semantic test must freeze policy and resource budgets before new source-disjoint, independently adjudicated graph data are observed. It must measure both correct retained edges and wrong edges, downstream query loss, intervention harm, actual reviewer errors, incomplete provenance, marginal misspecification and cap-driven staging. That study has not been performed here.', '',
            '## 8. Reproducibility and artifact integrity', '',
            '```bash',
            'python -m pip install -r graph_synthesis/uncertainty/requirements.txt',
            'python -B -m graph_synthesis.uncertainty.run',
            'python -B -m unittest discover -s graph_synthesis/uncertainty/tests -v',
            'python -B -m graph_synthesis.uncertainty.run --check',
            'python -m pip install -r graph_synthesis/requirements-figures.txt',
            'python -B -m graph_synthesis.uncertainty.report --figures --update-paper',
            'python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf',
            '```', '',
            'The [machine-readable results](results.json) preserve fixture inputs, oracle values, all review-subset scores, repair witnesses, retraction feasibility, snapshot outcomes, controls and source/protocol hashes. The [execution notes](EXECUTION_NOTES.md) distinguish implementation/test corrections from endpoint changes. The extension manifest binds code, protocol, results, tests, logs, report, CSV and five SVG/PNG pairs. The mutable complete manuscript is bound by its separate build manifest. Earlier study blocks and archived raw evidence are preserved; no original manuscript is overwritten.', '']
    return '\n'.join(out)


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'uncertainty-20260918'
    directory = HERE/'figures'; directory.mkdir(exist_ok=True)
    def save(fig, name, note):
        fig.text(.08, .025, note, fontsize=9, va='bottom')
        fig.tight_layout(rect=(0, .13, 1, 1))
        fig.savefig(directory/(name+'.png'), dpi=180)
        fig.savefig(directory/(name+'.svg'), metadata={'Date': None})
        plt.close(fig)
    a, b, c, d, e = [r[f'H{i}'] for i in range(1, 6)]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    values = [a['independent_false_admissions'], a['false_admissions']]
    bars = ax.bar(['Assumed independence', 'Dependence-agnostic lower bound'], values)
    ax.bar_label(bars); ax.set(ylim=(0, max(values+[1])*1.2), ylabel='False admissions at threshold 0.95',
                              title='H1 | Unknown dependence is not independent evidence')
    save(fig, FIGURES[0], '128 supplied joint-distribution fixtures; zero fresh Jev calls.\nValid marginals remain an assumption; numerical bounds are not formal certificates.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    values = [b['selected_assertions'], b['necessary_assertions']]
    bars = ax.bar(['One deterministic optimum', 'Necessary in every optimum'], values)
    ax.bar_label(bars); ax.set(ylim=(0, max(values)*1.18), ylabel='Total selected assertions across fixtures',
                              title='H2 | Expose tie-dependent choices instead of treating them as certain')
    save(fig, FIGURES[1], f"128 supplied conflict graphs; {b['ambiguous_cases']} have multiple optima.\nWithheld assertions reflect ambiguity, not proven errors; false priorities can still win.")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    means = review_means(c); zero = mean(x['no_review_loss'] for x in c['cases'])
    for key, label, marker in [('risk', 'Primitive error risk', 'o'), ('entropy', 'Primitive entropy', 's'), ('proposed', 'Query-loss objective', '^')]:
        ax.plot([0, 1, 2], [zero]+[x[key] for x in means], marker=marker, label=label)
    ax.set(xticks=[0, 1, 2], ylim=(0, None), xlabel='Perfect primitive reviews per fixture',
           ylabel='Mean residual summed Brier loss (three queries)', title='H3 | Allocate review to downstream query uncertainty')
    ax.legend()
    save(fig, FIGURES[2], '64 independent-event fixtures; supplied correct priors and perfect review.\nThe paper retains noisy-review and misspecified-prior counterexamples.')
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    values = [d['union_collateral'], d['proposed_collateral']]
    bars = ax.bar(['Withdraw all target-proof atoms', 'Minimum-collateral plan'], values)
    ax.bar_label(bars); ax.set(ylim=(0, max(values+[1])*1.2), ylabel='Total other conclusions lost',
                              title='H4 | Retract target support without unnecessary collateral')
    save(fig, FIGURES[3], f"Same {d['matched_feasible_cases']} cases where both plans preserve protected conclusions.\nOverall feasible plans: union {d['union_feasible_cases']}/128, proposed {d['proposed_feasible_cases']}/128. Complete lineage assumed.")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    rows = e['controls']['cycles']; sizes = [x['n'] for x in rows]
    ax.plot(sizes, [len(x['naive_after_withdrawal']) for x in rows], marker='o', label='Local support-count pruning')
    ax.plot(sizes, [len(x['proposed_after_withdrawal']['active']) for x in rows], marker='s', label='Grounded least fixed point')
    ax.set(xlabel='Cycle size', ylabel='Unsupported cycle assertions retained',
           title='H5 | Circular support does not replace external grounding', ylim=(-2, 70))
    ax.legend()
    save(fig, FIGURES[4], 'Controlled seed-withdrawal cases; independent backup support is preserved.\n1,152 random snapshots also match finite-model entailment; false bases remain unsafe.')


def replace_after_anchor(text, body):
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError('Malformed uncertainty section markers')
    text = re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*', '', text, flags=re.S)
    if text.count(ANCHOR) != 1:
        raise ValueError('Expected exactly one preceding reliability section anchor')
    before, after = text.split(ANCHOR, 1)
    return before+ANCHOR+'\n\n'+START+'\n\n'+body.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def update_paper(r):
    def rebase(match):
        url = match.group(1)
        if '://' in url or url.startswith('#'):
            return ']('+url+')'
        path = (HERE/url).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Link outside repository')
        return '](../'+path.relative_to(ROOT).as_posix()+')'
    section = re.sub(r'\]\(([^)]+)\)', rebase, render(r))
    path = ROOT/'manuscript/paper-current.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'), section), encoding='utf-8', newline='\n')
    note = ('## Five uncertainty and grounding improvements\n\n'
            '[Executed report](graph_synthesis/uncertainty/RESULTS.md), [frozen protocol](graph_synthesis/uncertainty/PROTOCOL.md), '
            '[five figures](graph_synthesis/uncertainty/figures/) and [complete updated paper](manuscript/paper-current.pdf). '
            +'; '.join(f"H{i} {'met' if r[f'H{i}']['primary_target_met'] else 'did not meet'} its frozen target" for i in range(1, 6))
            +'. All five are controlled algorithmic/decision-theoretic tests, not new Jev accuracy observations. '
            'Dependence uncertainty, repair ambiguity, query-directed review, collateral-aware retraction and recursive grounding are tested with explicit failure controls. '
            'No fresh Jev calls, new scientific documents, globally unprecedented algorithm claim or production-policy changes.')
    path = ROOT/'CURRENT_RESULTS.md'
    path.write_text(replace_after_anchor(path.read_text(encoding='utf-8'), note), encoding='utf-8', newline='\n')


def manifest():
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(HERE.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.name != 'artifact-manifest.json'}
    write(HERE/'artifact-manifest.json', {'sha256': files,
          'note': 'Uncertainty extension only, excluding self. The mutable shared paper has its own build manifest.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true'); parser.add_argument('--update-paper', action='store_true')
    args = parser.parse_args(); r = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    (HERE/'RESULTS.md').write_text(render(r), encoding='utf-8', newline='\n')
    with (HERE/'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['hypothesis', 'title', 'primary_target_met', 'fresh_service_calls'])
        for i, title in enumerate(TITLES, 1):
            writer.writerow([f'H{i}', title, r[f'H{i}']['primary_target_met'], r['fresh_service_calls']])
    if args.figures:
        figures(r)
    if args.update_paper:
        update_paper(r)
    manifest(); print('Generated uncertainty report, table, figures and requested additive paper section')


if __name__ == '__main__':
    main()
