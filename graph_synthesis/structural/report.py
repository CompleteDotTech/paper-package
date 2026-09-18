"""Deterministic figures and an additive manuscript extension from executed JSON."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from .run import HERE, ROOT, write

START = '<!-- STRUCTURAL_RESEARCH_START -->'
END = '<!-- STRUCTURAL_RESEARCH_END -->'
ANCHOR = '<!-- RISK_CONTROL_RESEARCH_END -->'


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams['svg.hashsalt'] = 'jev-structural-20260921'
    out = HERE/'figures'; out.mkdir(exist_ok=True)
    def save(fig, name):
        fig.tight_layout(pad=1.4)
        fig.savefig(out/(name+'.svg'), metadata={'Date':None})
        fig.savefig(out/(name+'.png'), dpi=200, metadata={'Software':'Matplotlib'})
        plt.close(fig)
    k145 = r['acceptance']['budgets'][2]['policies']
    fig, ax = plt.subplots(figsize=(7.6,4.5))
    values = [k145[name]['wrong_edges'] for name in ('raw','balanced','unweighted')]
    bars = ax.bar(['Raw confidence','Source-balanced\nreliability','Unweighted\nreliability'], values)
    ax.bar_label(bars, padding=3)
    ax.axhline(.8*values[0], linestyle='--', label='Frozen target: at least 20% fewer errors')
    ax.set(ylabel='Wrong accepted edges / 145 accepted', ylim=(0,21), title='H1: Two fewer mistakes, but the primary target fails')
    ax.legend(loc='upper right', fontsize=8)
    save(fig,'01_reliability_ranking')

    fig, ax = plt.subplots(figsize=(7.6,4.5))
    names = [('raw','Raw confidence','o'),('balanced','Reliability ranking','s'),('diverse','Source-diverse','^')]
    for name, label, marker in names:
        rows = [x['policies'][name] for x in r['acceptance']['budgets']]
        ax.plot([x['represented_groups'] for x in rows], [x['correct_edges'] for x in rows], marker=marker, label=label)
        for budget, row in zip(r['acceptance']['budgets'], rows):
            ax.annotate(str(budget['k']), (row['represented_groups'], row['correct_edges']), xytext=(5,4), textcoords='offset points', fontsize=8)
    ax.set(xlabel='Source groups with at least one accepted edge', ylabel='Correct accepted edges', xlim=(64,105), ylim=(80,136), title='H2: Broader source coverage can sacrifice correct edges')
    ax.legend(loc='upper left', fontsize=8)
    save(fig,'02_source_coverage')

    fig, ax = plt.subplots(figsize=(7.6,4.5))
    budgets = r['H3']['budgets']
    for name, label, marker in [('independent','Independent-risk allocation','o'),('robust','Union-bound allocation','s')]:
        ax.plot([b['budget'] for b in budgets], [b['policies'][name]['observed']['expected_contaminated_groups'] for b in budgets], marker=marker, label=label)
    ax.plot([b['budget'] for b in budgets], [b['policies']['robust']['modeled']['upper'] for b in budgets], '--', label='Fitted upper-envelope objective (both tie)')
    ax.set(xlabel='Reviewed edges (assumed sensitivity 0.75)', ylabel='Expected contaminated source groups', ylim=(0,15), title='H3: Dependence robustness cannot repair poor risk estimates')
    ax.legend(fontsize=8, loc='lower left')
    save(fig,'03_review_allocation')

    fig, ax = plt.subplots(figsize=(7.6,4.5))
    rows = r['H4']['large']; xs = [x['atoms'] for x in rows]
    ax.plot(xs, [x['actual']['prior_bounds']['lower'] for x in rows], '--', label='Prior shared-lineage lower bound')
    ax.plot(xs, [x['actual']['prior_bounds']['upper'] for x in rows], ':', label='Prior shared-lineage upper bound')
    ax.plot(xs, [x['actual']['probability'] for x in rows], marker='o', label='Exact decomposition = analytic oracle')
    ax.axhline(.95, linestyle='-.', label='Admission threshold 0.95')
    ax.set_xscale('log', base=2)
    ax.set(xlabel='Supplied independent primitive atoms (shared-hub fixtures)', ylabel='Probability of at least one sufficient proof', ylim=(.45,1.04), title='H4: Exact lineage resolves conservative abstentions')
    ax.legend(fontsize=8, loc='center right')
    save(fig,'04_exact_lineage')

    fig, ax = plt.subplots(figsize=(7.6,4.5))
    rows = [x for x in r['H5']['large'] if x['weighted']]
    xs = [x['n'] for x in rows]
    ax.plot(xs, [x['actual']['utility'] for x in rows], marker='o', label='Cutset + forest dynamic programming')
    ax.plot(xs, [x['oracle'] for x in rows], linestyle='none', marker='x', markersize=8, label='Independent cycle oracle')
    ax.plot(xs, [x['prior']['utility'] for x in rows], '--', label='Prior solver (entire component staged)')
    ax.set(xlabel='Assertions in a weighted cycle', ylabel='Maximum supplied priority retained', title='H5: Exact cyclic processing through 256 assertions')
    ax.legend(fontsize=8, loc='upper left')
    save(fig,'05_cutset_capacity')


def render(r):
    ac = r['acceptance']; a = ac['budgets'][2]['policies']; d = ac['budgets'][0]['policies']
    review = r['H3']['budgets'][1]['policies']; h4,h5 = r['H4'],r['H5']
    ci = ac['budgets'][2]['intervals_vs_raw']['balanced']['precision']
    reduction = 1-a['balanced']['wrong_edges']/a['raw']['wrong_edges']
    lines = [
        '# Reliability ranking, source diversity and bounded exact inference for Jev graph synthesis', '',
        'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026', '',
        '## Abstract', '',
        f'Five refinements follow the latest risk-controlled experiments. Source-balanced reliability ranking reduces wrong accepted edges from {a["raw"]["wrong_edges"]} to {a["balanced"]["wrong_edges"]} at an equal volume of 145 edges, but the {100*reduction:.2f}% reduction misses the frozen 20% target. Source diversification covers more source groups but retains fewer correct edges and contaminates more groups. Dependence-robust review allocation meets its mathematical objective yet worsens the observed-label reviewer simulation at the primary budget. Bounded exact lineage inference recovers {h4["recovered_admissions"]} controlled high-probability admissions lost by conservative bounds, without an oracle error. Feedback-cutset conditioning extends exact conflict optimization to the tested cyclic components of up to 256 assertions. These last two successes concern supplied probability and priority models, not improved scientific extraction or factual truth. No fresh Jev calls, independent semantic validation or production-policy change is claimed.', '',
        '## 1. Research motivation and evidence boundary', '',
        'The [preceding risk-control study](../risk_control/RESULTS.md) exposed a useful distinction: reliable execution, estimated risk, structural consistency and factual correctness are different properties. Its economical routing guard rejected every learned candidate, source-risk gating lost substantial correct-edge coverage, qualifier checks supplied no valid veto, and review risk estimates were optimistic. The controlled forest solver succeeded but staged large cyclic components. The [earlier follow-up](../followup/RESULTS.md) supplied conservative probability bounds for shared proof lineage. These findings motivate different acceptance rankings and exact downstream inference instead of another correlated vote.', '',
        f'The [protocol](PROTOCOL.md) was committed as `{r["protocol_commit"]}` before these new policies were executed, against baseline `{r["baseline_commit"]}`. Earlier aggregate results and test cases had already been inspected. This is a frozen exploratory follow-up, not an independent preregistration. H1-H3 reuse authentic captured requests and responses: {r["development"]["n"]} development candidates in {r["development"]["groups"]} source groups and {r["test"]["n"]} evaluation candidates in {r["test"]["groups"]} groups. Fitting uses development labels only; selection interfaces receive no gold labels. Raw-response reconstruction, hashes and source-group separation pass before analysis.', '',
        '**Fresh service calls: 0.** The historical 3,024 calls are not counted again. H1-H2 are counterfactual selection over the single-rich capture. H3 is an analytic simulation using assumed reviewer sensitivity and false-removal rates. H4-H5 compare controlled algorithms with independent finite or analytic oracles. No benchmark here evaluates candidate discovery, source extraction, a live human reviewer, an external system such as KARMA, or unattended database writes.', '',
        'An accepted edge is a valid SUPPORTS or REFUTES prediction. It is correct only when its polarity equals the gold label. A wrong polarity is both a wrong accepted edge and a missed gold edge. NOT_ENOUGH_INFO and operational errors are not accepted edges. Source groups are dependence units derived from source identifiers, not measured graph-connected components. A represented group contains an accepted edge; a contaminated group contains at least one wrong accepted edge.', '',
        '## 2. Frozen primary criteria', '',
        '| Hypothesis | Required conjunction | Executed outcome |',
        '|---|---|---|',
        '| H1: Reliability ranking | At K=145: at least 20% fewer wrong edges, at least 95% natural correct-edge retention, no fewer source groups | Not met |',
        '| H2: Source-diverse acceptance | At K=100: at least 10% more source groups, at least 98% correct-edge retention, no extra contaminated groups | Not met |',
        '| H3: Dependence-robust review | At budget 20: strictly fewer expected contaminated observed groups, no fewer expected correct edges, no worse union-bound objective | Not met |',
        '| H4: Exact shared lineage | All finite/analytic oracles and invariance checks pass; recover at least one valid 0.95 admission without false admissions | Met, controlled algorithms only |',
        '| H5: Feedback-cutset conflicts | All finite/analytic oracles and order checks pass; no prior utility regression; all 16 large cycles exact and unstaged | Met, controlled algorithms only |', '',
        'Each target is a conjunction, not an invitation to substitute a favorable secondary metric. Target indicators are engineering criteria, not statistical discoveries. The two evidence types must not be pooled into a semantic success percentage.', '',
        '## 3. H1: Source-balanced empirical reliability ranking', '',
        'The policy changes acceptance order rather than requesting another answer. Six bins combine predicted polarity with score intervals [0,0.90), [0.90,0.99) and [0.99,1]. Every development source group with positive predictions contributes total edge weight one. A Beta(1,1)-smoothed global correctness mean supplies four pseudo-observations per bin. Unseen bins use the global mean. Selection orders estimated bin reliability, raw score and finally ID. The unweighted-fit ablation uses the same bins and smoothing without source balancing. No evaluation outcome chooses a parameter.', '',
        'This exploits label-conditional reliability differences without assuming that raw confidence is calibrated. The fitted global mean is 0.90; bin estimates range from about 0.683 to 0.968. These small-sample estimates are ranking features, not deployment-certified probabilities. Calibration and decision ranking are distinct: a score transformation can alter acceptance order without improving all proper scoring rules. See [Guo et al., On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html) for the general calibration distinction, not evidence validating this specific ranking.', '',
        '| Accepted budget | Policy | Correct / wrong edges | Represented / contaminated groups |',
        '|---:|---|---:|---:|']
    for row in ac['budgets']:
        for name in ('raw','balanced','unweighted'):
            p = row['policies'][name]
            lines.append(f'| {row["k"]} | {name} | {p["correct_edges"]} / {p["wrong_edges"]} | {p["represented_groups"]} / {p["contaminated_groups"]} |')
    lines += ['',
        f'At the primary budget, the balanced and unweighted variants both retain {a["balanced"]["correct_edges"]} correct edges, versus {a["raw"]["correct_edges"]} for confidence ranking. Balanced retention is {100*r["H1"]["correct_retention"]:.2f}% of the natural single-rich baseline\'s 132 correct edges. Represented groups remain 95. However, reducing 17 mistakes to 15 is only {100*reduction:.2f}%, below 20%, so H1 fails. At K=100 the balanced fit is worse than both raw confidence and the unweighted ablation. Source balancing therefore cannot be credited with a general improvement.', '',
        f'The fixed-selection balanced-minus-raw precision difference at K=145 has descriptive 95% interval [{100*ci["95"][0]:+.2f}, {100*ci["95"][1]:+.2f}] percentage points and 99% interval [{100*ci["99"][0]:+.2f}, {100*ci["99"][1]:+.2f}] points. The former touches zero and the latter crosses it. These intervals do not establish a resolved independent accuracy effect. All variants require the same 263 captured single-rich calls and 941,809 recorded input tokens; this is not a token-saving method.', '',
        '![H1. Wrong edges at equal accepted volume; the frozen 20% reduction remains unmet.](figures/01_reliability_ranking.png)', '',
        '## 4. H2: Diminishing-return source diversification', '',
        'The separate diversity policy repeatedly selects the positive prediction maximizing raw_score / (1 + already_selected_in_source), with raw-score and ID tie-breaking. It does not train on labels or change predictions. The premise is that spreading a limited acceptance budget across sources might improve useful coverage without sacrificing correctness.', '',
        '| Accepted budget | Confidence: correct / wrong; groups / contaminated | Diverse: correct / wrong; groups / contaminated |',
        '|---:|---:|---:|']
    for row in ac['budgets']:
        b,p = row['policies']['raw'],row['policies']['diverse']
        lines.append(f'| {row["k"]} | {b["correct_edges"]} / {b["wrong_edges"]}; {b["represented_groups"]} / {b["contaminated_groups"]} | {p["correct_edges"]} / {p["wrong_edges"]}; {p["represented_groups"]} / {p["contaminated_groups"]} |')
    lines += ['',
        f'At K=100, coverage rises from {d["raw"]["represented_groups"]} to {d["diverse"]["represented_groups"]} represented groups ({100*(d["diverse"]["represented_groups"]/d["raw"]["represented_groups"]-1):.2f}%), but correct edges fall from {d["raw"]["correct_edges"]} to {d["diverse"]["correct_edges"]}. Retention is only {100*d["diverse"]["correct_edges"]/d["raw"]["correct_edges"]:.2f}%, below 98%. Contaminated groups increase from {d["raw"]["contaminated_groups"]} to {d["diverse"]["contaminated_groups"]}. H2 fails despite the favorable coverage count. At larger budgets the correctness penalty narrows, but no diagnostic budget replaces the primary test.', '',
        'The mechanism is visible in the policy: a high-confidence second edge in one source can be displaced by a less reliable first edge in another. Coverage is a design preference, not a free accuracy gain. Source-group coverage is not graph-node recall, relationship diversity or recovered scientific knowledge. The ranking still consumes the same full single-rich acquisition budget.', '',
        '![H2. Budget labels show the tradeoff between represented sources and correct edges.](figures/02_source_coverage.png)', '',
        '## 5. H3: Review allocation robust to dependence, conditional on valid marginals', '',
        'For residual edge-error marginals q_i, the probability of any error in a group lies between max(q_i) and min(1, sum(q_i)). The prior independent estimate 1 - product(1-q_i) lies between those bounds. A review multiplies its edge marginal by 1-s, where assumed sensitivity s=0.75. Group-budget dynamic programming minimizes the sum of the upper envelopes. For a fixed review count within a group, reviewing its highest-risk edges minimizes the residual sum; enumerating all group counts then yields the exact global allocation for this supplied objective. This establishes optimality of the modeled allocation, not correctness of the supplied risks.', '',
        'The development-only risk features and acquisition charges are unchanged from the previous independent-risk optimizer. False removal of a correct reviewed edge is assumed to be 0.05 and measured in the outcome simulation, not included in the allocation objective. Exact subset enumeration on 64 eight-edge fixtures finds zero objective failures. Enumeration of 64 four-edge joint distributions, including dependent errors, finds zero containment failures. These checks validate arithmetic under supplied marginals. A miscalibration control supplies four marginals of 0.01 although the actual union event has probability one: the computed upper envelope 0.04 is then invalid for truth. Removing an independence assumption cannot repair inaccurate marginal estimates.', '',
        '| Reviews | Independent allocation: expected contaminated / correct | Robust allocation: expected contaminated / correct | Fitted upper envelope (both) |',
        '|---:|---:|---:|---:|']
    for row in r['H3']['budgets']:
        b,p = row['policies']['independent'],row['policies']['robust']
        lines.append(f'| {row["budget"]} | {b["observed"]["expected_contaminated_groups"]:.4f} / {b["observed"]["expected_correct_edges"]:.2f} | {p["observed"]["expected_contaminated_groups"]:.4f} / {p["observed"]["expected_correct_edges"]:.2f} | {p["modeled"]["upper"]:.4f} |')
    lines += ['',
        f'At the primary budget 20, the robust allocation leaves {review["robust"]["observed"]["expected_contaminated_groups"]:.4f} expected contaminated groups, versus {review["independent"]["observed"]["expected_contaminated_groups"]:.4f}, and retains {review["robust"]["observed"]["expected_correct_edges"]:.2f} rather than {review["independent"]["observed"]["expected_correct_edges"]:.2f} expected correct edges. H3 fails. Both allocations tie the fitted upper-envelope objective, so a different optimum can still be worse under the observed-label simulation. The fitted upper envelope near 4.10 is far below either simulation outcome; it is not a calibrated empirical upper confidence bound.', '',
        f'Risk-feature acquisition requires {r["H3"]["risk_feature_input_tokens"]:,} recorded input tokens before reviewer cost. The stored sensitivity analysis crosses s in {{0.5,0.75,1}} with false-removal rates {{0,0.01,0.05}}, keeping selected IDs fixed. These are expectations under assumed independent reviewer detections, not measured human trials or guarantees about correlated reviewer mistakes.', '',
        '![H3. Observed-label reviewer simulations diverge despite equal modeled robust objectives.](figures/03_review_allocation.png)', '',
        '## 6. H4: Bounded exact inference over shared proof lineage', '',
        'A sufficient proof is a conjunction of explicitly supplied primitive Bernoulli events. The accepted assertion is the disjunction of its sufficient proofs. The previous component bounds deduplicate and account conservatively for shared atoms, but can be too loose for admission. The refinement canonicalizes proof clauses, absorbs supersets, and applies Shannon decomposition: P(F) = p_a P(F | a=true) + (1-p_a) P(F | a=false). The most frequent atom is conditioned first, with lexical tie-breaking; canonical residual formulas are memoized. Shared proofs are never treated as independent witnesses.', '',
        'The exactness follows by the law of total probability and independence of the supplied primitive atoms, not independence of clauses. This is an application of established Boolean/probabilistic inference rather than a newly invented theorem. [Darwiche and Marquis, A Knowledge Compilation Map](https://arxiv.org/abs/1106.1819) situates representation/tractability tradeoffs; [Fink, Han and Olteanu, Aggregation in Probabilistic Databases via Knowledge Compilation](https://arxiv.org/abs/1201.6569) provides related probabilistic-database context. Neither reference validates Jev scores as source reliabilities.', '',
        f'All {len(h4["fixtures"])} seeded eight-atom fixtures match full possible-world enumeration within 1e-10. All {h4["invariance_checks"]} duplicate/order checks pass. Eight larger shared-hub fixtures also match the analytic probability 0.99 * (1 - 0.5^(n-1)). Their atoms are the independent hub and leaves; proofs share the hub. The old lower bound stays 0.495 while exact probabilities exceed the 0.95 admission threshold.', '',
        '| Primitive atoms | Old lower bound | Exact / analytic probability | Memoized states |',
        '|---:|---:|---:|---:|']
    for row in h4['large']:
        lines.append(f'| {row["atoms"]} | {row["actual"]["prior_bounds"]["lower"]:.6f} | {row["actual"]["probability"]:.9f} | {row["actual"]["states"]} |')
    lines += ['',
        f'Across the 128 finite fixtures and eight analytic fixtures, exact inference recovers {h4["recovered_admissions"]} oracle-valid admissions that the old lower bound would withhold, with {h4["false_admissions"]} false admissions. H4 meets its controlled target. The endpoint counts fixtures, not newly discovered scientific graph edges. Values rounded to 0.99 in the table retain normal floating-point limitations; no symbolic exact-arithmetic claim is made.', '',
        'The implementation caps supplied atoms at 256, input proofs at 512 and memoized residual states at 4,096. On input/state exhaustion it returns the prior valid bounds with nonexact status and no point probability. The one-state control returns [0.25,0.50], containing the exact probability 0.375. This finite cap is a safety boundary, not a polynomial-time guarantee for arbitrary Boolean formulas. A corrupted-lineage control declares two aliases of the same 0.9 event independent and obtains 0.99 instead of 0.9. Incorrect primitive identity or uncalibrated reliability can therefore invalidate apparently precise answers. Raw Jev confidence is not promoted to primitive reliability.', '',
        '![H4. Eight controlled shared-hub families resolve the old lower-bound abstention.](figures/04_exact_lineage.png)', '',
        '## 7. H5: Feedback-cutset conditioning for cyclic conflicts', '',
        'The prior solver handled forest components by exact dynamic programming, cyclic components of at most 16 vertices by enumeration, and staged larger cycles. The refinement finds a bounded feedback set by repeatedly removing a deterministic maximum-degree vertex from the current cycle-containing 2-core. If at most four removals leave a forest, every independent assignment of the cutset is enumerated. For each assignment, selected cutset vertices exclude their neighbors and the residual forest is solved exactly. Maximizing across these assignments is exact for the supplied weighted independent-set problem because every feasible solution has one enumerated cutset assignment.', '',
        'Cutset discovery is a heuristic: failing its four-removal cap does not prove that the graph lacks a smaller feedback vertex set. Such failures retain the prior solver behavior, including exact small-component fallback and explicit staging. Components over 256 vertices remain staged. No asymptotic improvement is claimed for conflict construction, and the generic graph backend does not establish that these cyclic topologies arise in a particular scientific corpus.', '',
        f'All {len(h5["fixtures"])} seeded ten-vertex graphs agree with exhaustive subset enumeration, have consistent selected sets, and never regress below prior utility. All {h5["permutation_checks"]} input-order checks pass. Sixteen large uniform/weighted cycles agree with an independently implemented two-path recurrence; the prior solver stages every one of them.', '',
        '| Cycle vertices | Uniform: new / oracle | Weighted: new / oracle | Prior utility (both) |',
        '|---:|---:|---:|---:|']
    for i in range(8):
        u,w = h5['large'][i],h5['large'][i+8]
        lines.append(f'| {u["n"]} | {u["actual"]["utility"]} / {u["oracle"]} | {w["actual"]["utility"]} / {w["oracle"]} | 0 |')
    lines += ['',
        'H5 meets its controlled target. The 17-clique cap control stages all 17 vertices, and the 257-cycle control stages all 257. A semantic control offers two conflicting assertions with priorities nine and eight and marks the higher-priority assertion false. The exact solver still chooses the false assertion. Optimal priority retention and consistency are not factual validation. This extension changes research-only solvers, not the default graph compiler.', '',
        '![H5. Weighted cycle utility equals the independent oracle beyond the prior cyclic cap.](figures/05_cutset_capacity.png)', '',
        '## 8. Uncertainty, limitations and next discriminating evidence', '',
        'H1-H2 use 4,000 paired source-group bootstrap draws, seed 20260921. Fitted rankings and accepted IDs are fixed in each resample. Reported 95% and 99% percentile intervals are descriptive, not simultaneous; they omit fitting uncertainty and cannot undo prior test exposure. No result is an independent confirmatory p-value. Repeated model responses are not new independent labels, and source groups do not remove every possible dependency or public-corpus training overlap.', '',
        'The strongest semantic lead is a small equal-volume ranking improvement, not a validated deployment policy. The strongest controlled improvements exploit structure already supplied to the algorithm. They require independently credible primitive reliabilities, correct provenance and well-specified conflict priorities. Larger candidate sets, diverse real graph topologies, externally adjudicated edge truth and fresh source-disjoint evaluations remain necessary before translating those gains into claims about Jev-assisted graph synthesis. A matched-evidence comparison with [KARMA](https://arxiv.org/abs/2502.06472) has not been run here.', '',
        'A discriminating next semantic experiment should freeze the ranking before obtaining new independently adjudicated source groups, compare it with raw-confidence ranking at matched accepted volume and acquisition cost, and report source coverage alongside correct and wrong edges. A next systems experiment should preserve a real extracted provenance/conflict graph, blind its truth labels during policy selection, and measure cap/staging frequency and wall-clock cost. Those are future evidence requirements, not unexecuted results represented as complete.', '',
        '## 9. Reproduction and claim audit', '',
        'Run `python -B -m graph_synthesis.structural.run --check` to reconstruct inputs and reproduce all five outcomes without service access. Run `python -B -m unittest discover -s graph_synthesis/structural/tests -v` for implementation regressions. Run `python -B -m graph_synthesis.structural.report --figures --update-paper` to regenerate this report, five PNG/SVG figures and the additive current-paper section. The shared renderer then builds the full HTML/PDF, and its build record binds manuscript, renderer and PDF SHA-256 hashes.', '',
        '`results.json` retains fitted parameters, selected IDs, all finite fixtures, oracle outputs, control failures, descriptive intervals and reviewer sensitivities. `summary.csv` records all equal-volume policy comparisons. `artifact-manifest.json` binds extension files without rewriting archived evidence. [CLAIM_EVIDENCE.md](CLAIM_EVIDENCE.md) maps each conclusion to its evidence and forbidden extrapolation. Environment files distinguish local execution from CI. The original 161-file study and earlier extension outputs remain intact. The full manuscript remains an author-review draft.', '']
    return '\n'.join(lines)


def insert(text, section):
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError('Unbalanced or duplicate structural manuscript markers')
    text = re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*', '', text, flags=re.S)
    if text.count(ANCHOR) != 1:
        raise ValueError('Expected one risk-control anchor')
    before, after = text.split(ANCHOR, 1)
    return before+ANCHOR+'\n\n'+START+'\n\n'+section.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def update_paper(text):
    def rebase(match):
        url = match.group(1)
        if '://' in url or url.startswith('#'): return ']('+url+')'
        path = (HERE/url).resolve()
        if not path.is_relative_to(ROOT): raise ValueError('Report link escapes repository')
        return '](../'+path.relative_to(ROOT).as_posix()+')'
    section = re.sub(r'\]\(([^)]+)\)', rebase, text)
    paper = ROOT/'manuscript/paper-current.md'
    paper.write_text(insert(paper.read_text(encoding='utf-8'), section), encoding='utf-8', newline='\n')
    current = ROOT/'CURRENT_RESULTS.md'
    note = ('## Five structural refinements after PR #16\n\n'
            '[Executed report](graph_synthesis/structural/RESULTS.md), [frozen protocol](graph_synthesis/structural/PROTOCOL.md), '
            '[five figures](graph_synthesis/structural/figures/) and [updated full paper](manuscript/paper-current.pdf). '
            'No fresh Jev calls. Reliability ranking reduces matched-volume wrong edges from 17 to 15 but misses its 20% target. '
            'Source diversification and dependence-robust review worsen primary quality outcomes. Exact shared-lineage inference '
            'recovers 16 controlled admissions; feedback-cutset optimization solves all 16 tested large cycles through 256 assertions. '
            'Controlled probability/priority gains are not semantic-accuracy gains. Negative results retained; no production-policy change.')
    current.write_text(insert(current.read_text(encoding='utf-8'), note), encoding='utf-8', newline='\n')


def manifest():
    paths = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts and p.name != 'artifact-manifest.json'}
    write(HERE/'artifact-manifest.json', {'note':'Structural extension only; excludes this self-reference and changing full-paper builds.', 'sha256':paths})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--figures', action='store_true'); parser.add_argument('--update-paper', action='store_true')
    args = parser.parse_args()
    r = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    text = render(r)
    (HERE/'RESULTS.md').write_text(text, encoding='utf-8', newline='\n')
    with (HERE/'summary.csv').open('w', encoding='utf-8', newline='') as stream:
        fields = ['accepted_budget','policy','correct_edges','wrong_edges','represented_groups','contaminated_groups','precision','recall','input_tokens']
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for budget in r['acceptance']['budgets']:
            for name, row in budget['policies'].items():
                writer.writerow({'accepted_budget':budget['k'], 'policy':name, **{k:row[k] for k in fields[2:]}})
    if args.figures: figures(r)
    if args.update_paper: update_paper(text)
    manifest()
    print('Generated structural report, tables, requested figures and additive paper section')

if __name__ == '__main__': main()
