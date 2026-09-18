"""Render the frozen structural-frontier results without changing earlier studies."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
START = '<!-- FRONTIER_RESEARCH_START -->'
END = '<!-- FRONTIER_RESEARCH_END -->'
ANCHOR = '<!-- RELIABILITY_RESEARCH_END -->'
NAMES = {'H1':'Latent-source-conditioned lineage', 'H2':'Cost/noise-aware group review',
         'H3':'Reusable state-bounded lineage diagrams', 'H4':'Certified bipartite conflict optimization',
         'H5':'Connected-path incremental optimization'}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))


def status(value):
    return 'Met' if value else 'Not met'


def summary_rows(r):
    return [dict(hypothesis=k, method=NAMES[k], target_met=r[k]['primary_target_met'],
                 evidence='saved-response / reviewer-model scenario' if k=='H2' else 'controlled supplied-input algorithm') for k in NAMES]


def report(r):
    a,b,c,d,e = (r[k] for k in NAMES)
    p=b['primary']['policies']; large=e['large']; reuse=c['reuse']
    summary='\n'.join(f"| {k} | {NAMES[k]} | {status(r[k]['primary_target_met'])} | {'Replay + reviewer assumptions' if k=='H2' else 'Controlled algorithm'} |" for k in NAMES)
    reviews='\n'.join(f"| {name.replace('_',' ')} | {v['cost']} | {len(v['selected'])} | {v['outcome']['expected_contaminated_groups']:.6f} | {v['outcome']['expected_correct_removed']:.4f} |" for name,v in p.items())
    lineage='\n'.join(f"| {x['kind']} | {x['n']} | {x['nodes']} | {x['prior']['lower']:.3f} | {x['proposed']['lower']:.9f} |" for x in c['large'])
    graphs='\n'.join(f"| {x['kind'].replace('_',' ')} | {x['n']} | {x['prior']['utility']} | {x['greedy']['utility']} | {x['proposed']['utility']} | {x['oracle']} |" for x in d['large'])
    return f'''# Structural frontiers for evidence-preserving Jev graph synthesis

Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026

## Abstract

Five frozen extensions test whether explicit source dependence, heterogeneous review assumptions and structural recognition address limitations exposed by PR #17. Latent-source marginalization matches an independent joint-world oracle on 96 supplied-model fixtures and prevents {a['prior_false_admissions_random']} false threshold admissions made by the independent-marginal comparator. Cost- and noise-aware review allocation fails its frozen downstream target: at 40 proxy effort units it leaves {p['optimal']['outcome']['expected_contaminated_groups']:.6f} expected contaminated source groups, identical to both comparison policies. Compile-once decision diagrams exactly evaluate ten connected lineage formulas with 17–256 primitives beyond the previous blanket component cap. Certified bipartite optimization attains nine analytic large-graph optima previously staged. A fixed-path segment tree reduces counted summary-maintenance transitions by {100*large['saving']:.2f}% across a 1,024-vertex, 256-update workload, excluding separately reported linear witness decoding. These are bounded engineering results, not new Jev semantic-accuracy evidence or proof of worldwide algorithmic novelty.

## 1. Motivation, novelty scope and frozen design

The [preceding reliability study](../reliability/RESULTS.md) found that better average calibration bias need not improve Brier score; source identity errors invalidate independent-event probabilities; capped exact solvers leave some structured cases unresolved; review effectiveness depends on assumptions; and whole-component caching provides no solver saving on a connected graph. The five present mechanisms address these particular limitations rather than adding more correlated Jev calls. TypeSafe's typed outputs and probabilities do not themselves establish graph truth ([TypeSafe documentation](https://docs.typesafe.ai/introduction)).

The [protocol](PROTOCOL.md) was committed as `{r['protocol_commit']}` before implementation and benchmark execution, against `{r['baseline_commit']}`. Prior results were inspected and informed hypothesis selection. This is exploratory follow-up, not independent preregistration. H2 reuses 73 development candidates in 40 groups and 263 evaluation candidates in 149 groups. These are already published observations, not a new holdout. **Fresh service calls: {r['fresh_service_calls']}.** Raw requests, response parsing, group separation and input hashes are checked before scoring. The other four hypotheses evaluate supplied models or graph structures, not newly extracted scientific facts.

| Hypothesis | Proposed extension | Frozen target | Evidence class |
|---|---|---|---|
{summary}

“Met” refers only to the predeclared conjunction on its specified fixture population. These rows must not be pooled into a semantic-success percentage. The [novelty audit](NOVELTY.md) distinguishes repository-new implementations from established source modeling, knowledge compilation, flow optimization and dynamic programming. It does not assert that no person has ever tried an equivalent idea.

## 2. H1: Source-conditioned evidence probability

Distinct evidence atoms can still depend on a common unreliable source. Instead of treating their marginal probabilities as independent, the proposed model supplies a binary quality state for each source, a prior for that state, and two conditional probabilities for each assigned atom. Source states are assumed mutually independent; primitive events are independent only conditional on those states. For a monotone proof formula F, compute P(F) = sum_z P(z) P(F given z). Each conditional formula uses the existing bounded exact lineage evaluator. This is exact marginalization within the supplied model, not discovery of the correct dependence structure.

The 96 seeded fixtures contain 2–8 primitives and 1–3 sources. The independent oracle enumerates joint source-plus-primitive assignments, rather than calling the proposed marginalization/evaluation routine. There are **{a['oracle_failures']} oracle discrepancies above 1e-12**, **{a['invariance_failures']} failures in {a['invariance_checks']} order/duplicate checks**, and **{a['false_admissions']} proposed false admissions at 0.95**. Independent marginals make {a['prior_false_admissions_random']} false admissions on these random fixtures. Mean absolute probability error is {a['mean_absolute_error_prior']:.6f} for independent marginals and {a['mean_absolute_error_proposed']:.3g} for the supplied dependence model.

| Shared-source query | Independent marginals | Conditioned model | Joint-world truth |
|---|---:|---:|---:|
| At least one of two copies (OR) | 0.96 | 0.80 | 0.80 |
| Both copies (AND) | 0.64 | 0.80 | 0.80 |

The OR control prevents an unjustified 0.95 admission; the AND control shows that dependence errors do not always inflate probability. The target is **{status(a['primary_target_met']).lower()}**. Inputs over eight sources or sixteen primitives are explicitly staged with [0,1], not assigned an exact probability. Conditional evaluator exhaustion retains conservative bounds.

![H1. Declared common-source dependence corrects both OR inflation and AND deflation on the supplied two-copy control. These are model probabilities, not observed Jev accuracies.](figures/01_source_dependence.png)

**Assumption-breaking control:** two declared independent latent sources that actually share one cause still yield 0.96 when the actual probability is 0.80. The extension therefore moves the necessary independence assumption to the source layer; it does not remove it. Primitive reliabilities and source assignments are fixture inputs, not calibrated model scores or independently adjudicated provenance. Bayesian source-quality modeling already has substantial prior art, including [Zhao et al. (2012)](https://arxiv.org/abs/1203.0058); this experiment does not reproduce or outperform their truth-discovery system.

## 3. H2: Review allocation under effort and reviewer errors

The proposed allocator uses the prior study's development-only single-view risk estimator. Evaluation gold, compact-view predictions and observed review outcomes are unavailable to selection. The supplied per-edge effort is min(8, 1 + floor(recorded single-call input tokens / 1000)). This is a bounded proxy, not measured annotation time, cognitive difficulty, monetary cost or new service expenditure. At base detection s0, detection for cost c is s0 / (1 + 0.05(c−1)); a supplied false-removal probability applies to correct reviewed edges.

For selected review IDs A, the modeled source-group contamination is 1 − product_i[1 − p_i(1 − s_i I(i in A))]. The objective is total modeled group cleaning minus expected correct-edge removals with unit penalty. Enumerate subsets within each group of at most twelve candidates, then allocate across groups using integer-budget multiple-choice knapsack. Larger groups receive no optimized review; **{len(p['optimal']['staged_groups'])} primary groups exceed the cap**. No-review remains an available option. The baselines are the actual previous group-aware order packed into the same budget, and marginal-model-benefit-per-cost greedy. Equal budgets do not require identical spending.

The fixed acceptance population contains 150 single-view positive judgments: 132 correct and 18 wrong, spread across 15 contaminated groups before review. This is not the earlier study's separate matched-volume top-145 comparison. Primary scoring uses all 149 evaluation source groups, including groups with no accepted edges. The reviewer simulation removes an actually wrong edge with its supplied detection probability and removes a correct one with its supplied false-removal probability. No human reviewed these edges in this experiment.

The frozen primary scenario is budget 40, s0 = 0.75 and false-removal probability 0.01. The target requires at least 5% fewer expected contaminated groups than **both** comparators, while allowing at most 0.25 additional expected correct-edge removals versus either.

| Policy | Effort spent | Edges reviewed | Expected contaminated groups | Expected correct removed |
|---|---:|---:|---:|---:|
{reviews}

The target is **{status(b['primary_target_met']).lower()}**. All three review policies have the same primary expected contamination and correct-edge loss. The optimizer's modeled gain ({p['optimal']['modeled_gain']:.6f}) exceeds packed prior ({p['packed_prior']['modeled_gain']:.6f}) but ties ratio greedy ({p['ratio_greedy']['modeled_gain']:.6f}). Improved optimization of an imperfect model is not a demonstrated graph-quality gain. There are {b['oracle_failures']} objective discrepancies on 64 independent finite-enumeration checks; solver correctness does not rescue the empirical target.

![H2. Frozen budget-40 reviewer scenario. All three selectors tie on expected source contamination despite different selected IDs and effort spending. Values are scenario expectations, not observed human outcomes.](figures/02_noisy_review.png)

All 36 combinations of budgets 20/40/80/160 and detection/false-removal scenarios are retained in results.json; selection is recalculated from features and supplied assumptions only. The 4,000 paired group-bootstrap draws at fixed primary selections give a 95% and 99% proposed-minus-comparator contamination-rate interval of [0,0] for both comparisons because their per-group expected outcomes are identical. **This degeneracy is not evidence of known population equivalence.** These descriptive intervals omit model-fitting and reviewer-model uncertainty, and published-data reuse prevents independent confirmation. A deliberately incorrect-risk control spends its only review on an actually correct edge and misses the wrong one. Prior research already demonstrates the relevance of real annotation costs ([Settles et al., 2008](https://burrsettles.com/pub/settles.nips08ws.pdf)); our token-based proxy is not a measurement of those costs.

## 4. H3: Compile once, bound by decision-diagram state count

The previous evaluator rejects connected lineage components above sixteen atoms even when their Boolean structure is simple. The proposed compiler canonicalizes a monotone disjunction of conjunctions, chooses frequency-descending/lexical atom order, memoizes residual formulas and merges identical decision nodes. A compiled reduced ordered binary decision diagram can then be evaluated with changing supplied probabilities without recompiling its structure. Children precede parents, so evaluation is a bottom-up weighted sum. Conditional expansion preserves the represented Boolean function; merging identical subfunctions preserves every probability assignment under independent primitive events.

The safety boundaries are 512 atoms, 4,096 input proofs and 32,768 visited residual states. Input-cap violations stage. State-budget exhaustion returns conservative previous lineage bounds with an explicit nonexact status, never a partially evaluated point estimate. Compilation remains potentially exponential; these caps are operational safeguards, not a polynomial-time theorem.

There are {c['oracle_failures']} probability discrepancies across 128 random formulas with five assignments each, ten analytic large fixtures, 64 updates on one reused 128-atom chain, and the state-cap control. All ten connected large fixtures are exact under the new compiler and nonexact under the actual previous evaluator. Duplicate/input-order checks have {c['invariance_failures']} failures.

| Formula | Primitives | Decision nodes | Prior lower bound | Exact probability |
|---|---:|---:|---:|---:|
{lineage}

The shared-fan oracle is 0.99(1−0.5^(n−1)). The adjacent-pair chain oracle uses an independent two-state recurrence for the probability of no adjacent successes. The 128-atom reuse workload performs {reuse['compilations']} compilation with {reuse['nodes']} decision nodes, then 64 changed-probability evaluations totaling {reuse['evaluation_node_visits']:,} decision-node visits. The target is **{status(c['primary_target_met']).lower()}**. Diagram size, compile-state visits and evaluation-node visits are separate quantities; none is a measured service-latency saving.

![H3. Decision nodes required for exact connected formulas beyond the previous sixteen-primitive component cap. Lineage probability updates reuse these compiled structures.](figures/03_lineage_capacity.png)

Knowledge compilation for probabilistic data is established ([Fink et al., 2012](https://arxiv.org/abs/1201.6569)); provenance maintenance and hybrid compilation approaches for uncertain knowledge graphs are also established ([Gaur et al., 2021](https://arxiv.org/abs/2108.07758)). The contribution here is the bounded reusable implementation and its tests against this repository's earlier cap, not invention of decision diagrams or superiority over those systems. H3 still assumes independent primitive inputs; it does not automatically incorporate H1's source model.

## 5. H4: Certified bipartite conflict optimization

The cycle-cutset solver in PR #17 can stage a bipartite graph with many cycles even though its supplied-priority maximum independent set has a tractable reduction. The extension first recognizes bipartite components with at most 512 vertices. For bipartition L/R, create source-to-L and R-to-sink capacities equal to nonnegative integer priorities and L-to-R conflict arcs of capacity total priority plus one. A minimum cut cannot profitably cross a conflict arc, since cutting every priority arc is cheaper. Its vertex-side choices therefore give a minimum-weight vertex cover; the complement is a maximum-weight independent set.

The returned certificate contains a capacity-feasible flow, flow conservation at every internal node, a source/sink separating cut of equal value, and the complementary selected witness. A separate verifier checks these conditions without invoking an optimizer. A feasible flow lower-bounds any cut; equality certifies cut optimality, and the cover reduction certifies the selected supplied-priority objective. Nonbipartite components retain the unmodified prior solver and its staging behavior. No additional budget constraint is imposed; adding such constraints changes the complexity ([Doron-Arad and Shachnai, 2023](https://arxiv.org/abs/2307.08592)).

There are {d['oracle_failures']} optimum discrepancies, {d['certificate_errors']} certificate errors and {d['prior_regressions']} prior-utility regressions across 128 random bipartite and 64 general small graphs plus nine analytic large fixtures. The large comparator values below come from the actual imported previous solver, not a renamed reimplementation. Zero previous utility means the unsupported component was staged, not that no positive-utility solution exists.

| Structure | Vertices | Prior utility | Greedy utility | Certified utility | Oracle |
|---|---:|---:|---:|---:|---:|
{graphs}

The target is **{status(d['primary_target_met']).lower()}**. Complete bipartite fixtures have side weights one and two, giving optimum total weight on the heavier side. Rectangular unit grids have an independent checkerboard half; a perfect matching gives the corresponding upper bound. Certificate-tampering tests, zero weights, invalid endpoints, odd cycles and a dense 17-clique are retained. The odd clique still stages. Priority greedy also attains all nine large analytic optima; the extension adds an optimality certificate and recovery versus prior staging, not an observed large-fixture utility advantage over greedy.

![H4. Fraction of analytically optimal supplied-priority utility on nine structured conflict fixtures. Prior staging is zero recovered utility, not extraction failure.](figures/04_bipartite_capacity.png)

The semantic negative control remains decisive: a false assertion with supplied priority 9 defeats a conflicting true assertion with priority 8. An exact optimizer can be exactly wrong about factual truth when its priorities are wrong. No graph-extraction, clinical-validity or KARMA-superiority claim follows.

## 6. H5: Connected-path summary maintenance

Whole-component invalidation cannot exploit a local weight update inside one connected graph. For the deliberately narrower case of a fixed connected path, the proposed data structure stores the skip/take dynamic-programming transition for each vertex in a max-plus segment tree. Two-state transitions compose associatively; a leaf update requires recomputing only its ancestors. The root gives optimal utility without emitting the entire selected graph. Topology is validated at construction. Invalid or unknown-vertex weight updates are rejected before mutation; changing topology requires rebuilding. Stars and cycles are rejected rather than silently treated as paths.

Across 64 random paths with sixteen updates each and the 1,024-vertex path with 256 updates, there are **{e['mismatches']} utility or independent-witness discrepancies** against independent full linear dynamic programming. The primary workload includes cold construction and every update.

| Work quantity | Count | Interpretation |
|---|---:|---|
| Full recomputation transition candidates | {large['full_transition_candidates']:,} | Three scalar candidates per vertex per build/update |
| Segment-tree transition candidates | {large['segment_transition_candidates']:,} | Eight per internal 2-by-2 composition, including cold build |
| Segment summary-work reduction | {100*large['saving']:.2f}% | Only the two transition-candidate counts above |
| Cold topology validation visits | {large['validation_visits_cold']:,} | Vertex plus adjacency visits, separately recorded |
| Full witness-decoding node visits | {large['witness_visits_all_outputs']:,} | Every output decoded for validation; remains linear |

The frozen 90% counted summary-work reduction target is **{status(e['primary_target_met']).lower()}**. The 27,864 versus 789,504 transition comparison is not a total runtime or database-I/O measurement. Witness decoding adds 526,079 tree-node visits under a different operation metric and is explicitly not included in that percentage. A consumer needing the complete selected graph after every update still pays linear output/decoding work. Python overhead, memory traffic, initial sorting, dictionary operations and persistence are not captured by scalar transition counts.

![H5. Counted optimal-utility summary maintenance on a fixed connected path, including cold build. Full witness decoding is separately reported and excluded from the percentage.](figures/05_path_work.png)

## 7. Interpretation and next falsification boundary

The results favor identifying the tractable structure of a supplied problem over imposing blanket size restrictions: declared dependence changes which probabilities are valid; compact formula structure permits reusable exact evaluation; bipartiteness permits certified optimization despite many cycles; and a fixed path permits local summary updates despite being one connected component. These conclusions are conditional on correct metadata and supported topology. They do not establish that those structures dominate real Jev-generated graphs.

The review result is a useful negative finding. A more exact allocator can improve a modeled objective yet fail to improve the frozen downstream source-contamination measure. This counsels against promoting the allocator on optimization quality alone. Prospective human-cost/detection measurements, source-disjoint independently adjudicated documents, policies frozen before those labels are seen, and matched evidence/resource budgets against external graph-synthesis systems remain necessary for semantic or deployment claims. H1 and H3 reliability inputs must be estimated and audited separately; raw model confidence cannot simply be substituted.

The methods remain opt-in research utilities. No default compiler policy or production graph is changed. Failure controls and all prior studies remain in the complete manuscript. Each target is falsifiable on its specified population, but a passed finite benchmark is not a proof of correctness for all inputs or real-world superiority.

## 8. Reproducibility and audit

```bash
python -B -m graph_synthesis.frontier.run
python -B -m unittest discover -s graph_synthesis/frontier/tests -v
python -B -m graph_synthesis.frontier.run --check
python -B -m graph_synthesis.frontier.report --figures --update-paper
python -B -m graph_synthesis.render_current_paper --output manuscript/paper-current.pdf
python -B -m graph_synthesis.frontier.verify
```

The machine-readable results retain source and code hashes, source-group counts, all random fixtures or complete generating specifications, review IDs and scenarios, independent-oracle outputs, flow/cut witnesses, update sequences and decoded-witness hashes. The five figures are generated directly from those results as SVG and PNG pairs; summary.csv preserves target classifications without pooling them. The [implementation log](IMPLEMENTATION.md) records validation corrections without changing the protocol or endpoints. Original evidence integrity is checked against the immutable inventory. Source, result and figure hashes are bound in the extension manifest; the complete current PDF has a separate source/renderer/PDF hash record.
'''


def figures(r):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams['svg.hashsalt']='frontier-20260922'
    folder=HERE/'figures'; folder.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(folder/(name+'.svg'),metadata={'Date':None})
        fig.savefig(folder/(name+'.png'),dpi=220,metadata={'Software':'Matplotlib'})
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.0,4.8))
    x=np.arange(2); width=.25
    controls=r['H1']['paired_controls']
    for off,label,values in [(-1,'Independent marginals',[q['independent_marginals']['lower'] for q in controls]),
                             (0,'Source-conditioned',[q['proposed']['lower'] for q in controls]),
                             (1,'Joint-world oracle',[q['oracle'] for q in controls])]:
        bars=ax.bar(x+off*width,values,width,label=label)
        ax.bar_label(bars,fmt='%.2f',padding=3)
    ax.set(xticks=x,xticklabels=['At least one copy (OR)','Both copies (AND)'],ylabel='Supplied-model probability',ylim=(0,1.15),title='H1 | Distinct atoms, one common source')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.1),ncol=3,fontsize=9)
    save(fig,'01_source_dependence')
    fig,ax=plt.subplots(figsize=(8.0,4.8))
    names=['no_review','packed_prior','ratio_greedy','optimal']
    values=[r['H2']['primary']['policies'][n]['outcome']['expected_contaminated_groups'] for n in names]
    bars=ax.bar(range(4),values); ax.bar_label(bars,fmt='%.3f',padding=4)
    ax.set(xticks=range(4),xticklabels=['No review','Prior order\npacked','Benefit/cost\ngreedy','Group\nknapsack'],ylabel='Expected contaminated source groups',ylim=(0,17),title='H2 | Budget 40: no primary improvement')
    ax.text(.5,-.2,'Supplied detection/false-removal model; not observed human review.',transform=ax.transAxes,ha='center',fontsize=9)
    save(fig,'02_noisy_review')
    fig,ax=plt.subplots(figsize=(8.0,4.8))
    for kind,marker in [('fan','o'),('chain','s')]:
        rows=[x for x in r['H3']['large'] if x['kind']==kind]
        ax.plot([x['n'] for x in rows],[x['nodes'] for x in rows],marker=marker,label=kind.capitalize())
    ax.axvline(16,linestyle='--',label='Previous connected-component atom cap')
    ax.set(xlabel='Primitive events in connected formula',ylabel='Compiled decision nodes',title='H3 | Exact large lineage from compact structure',xlim=(0,265))
    ax.legend(fontsize=9); save(fig,'03_lineage_capacity')
    fig,ax=plt.subplots(figsize=(9.0,4.8))
    rows=r['H4']['large']; x=np.arange(len(rows)); width=.25
    for off,key,label in [(-1,'prior','Previous capped solver'),(0,'greedy','Priority greedy'),(1,'proposed','Certified bipartite')]:
        ax.bar(x+off*width,[q[key]['utility']/q['oracle'] for q in rows],width,label=label)
    labels=[f"K{q['n']//2},{q['n']//2}" if q['kind']=='complete_bipartite' else f"{q['rows']}x{q['cols']} grid" for q in rows]
    ax.set(xticks=x,xticklabels=labels,ylabel='Supplied utility / analytic optimum',ylim=(0,1.15),title='H4 | Nine previously staged structures solved exactly')
    ax.tick_params(axis='x',rotation=30); ax.legend(loc='upper center',bbox_to_anchor=(.5,-.23),ncol=3,fontsize=8)
    save(fig,'04_bipartite_capacity')
    fig,ax=plt.subplots(figsize=(8.0,4.8)); large=r['H5']['large']
    bars=ax.bar(['Full path DP','Segment-tree summary'],[large['full_transition_candidates'],large['segment_transition_candidates']])
    ax.bar_label(bars,labels=[f"{b.get_height():,.0f}" for b in bars],padding=4)
    ax.set(ylabel='Counted scalar transition candidates',ylim=(0,900000),title=f"H5 | {100*large['saving']:.2f}% fewer summary transitions")
    ax.ticklabel_format(style='plain',axis='y')
    ax.text(.5,-.15,'Cold build + 256 updates. Full witness decoding excluded; see separate counts.',transform=ax.transAxes,ha='center',fontsize=9)
    save(fig,'05_path_work')


def replace_block(text, body):
    text=re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\n*','',text,flags=re.S)
    if text.count(ANCHOR)!=1:
        raise ValueError('Exactly one preceding reliability-study anchor required')
    return text.replace(ANCHOR,ANCHOR+'\n\n'+START+'\n\n'+body.strip()+'\n\n'+END,1)


def update_paper(r, body):
    def link(match):
        label,url=match.groups()
        if re.match(r'[A-Za-z][A-Za-z0-9+.-]*:',url) or url.startswith('#'):
            return match.group(0)
        import os
        path=HERE/url
        return f'[{label}]({Path(os.path.relpath(path,ROOT/"manuscript")).as_posix()})'
    body=re.sub(r'\[([^\]]*)\]\(([^)]+)\)',link,body)
    path=ROOT/'manuscript/paper-current.md'
    write(path,replace_block(path.read_text(encoding='utf-8'),body))
    text='''## Five structural-frontier extensions after PR #17

[Executed report](graph_synthesis/frontier/RESULTS.md), [pre-execution protocol](graph_synthesis/frontier/PROTOCOL.md), [novelty audit](graph_synthesis/frontier/NOVELTY.md), [five figure pairs](graph_synthesis/frontier/figures/) and [complete updated paper](manuscript/paper-current.pdf). H1/H3/H4/H5 meet controlled supplied-input targets; H2 fails its frozen review-quality target. Source-conditioned probabilities prevent nine independent-marginal false admissions on 96 controlled fixtures; all three review selectors tie at 13.043478 expected contaminated groups. Ten large lineage formulas and nine bipartite conflict fixtures are exact. Connected-path summary transitions fall by 96.47%, excluding linear witness decoding. No new Jev calls, independent semantic-accuracy finding, worldwide novelty claim or production-policy change. All earlier studies and negative results remain intact.'''
    path=ROOT/'CURRENT_RESULTS.md'; write(path,replace_block(path.read_text(encoding='utf-8'),text))


def manifest():
    files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.rglob('*'))
           if p.is_file() and p.name!='artifact-manifest.json' and '__pycache__' not in p.parts}
    value={'schema_version':1,'scope':'Extension files only; complete manuscript has its own build hash record.','sha256':files}
    write(HERE/'artifact-manifest.json',json.dumps(value,indent=2,sort_keys=True)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--figures',action='store_true');parser.add_argument('--update-paper',action='store_true');args=parser.parse_args()
    r=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    body=report(r);write(HERE/'RESULTS.md',body)
    with (HERE/'summary.csv').open('w',encoding='utf-8',newline='') as f:
        rows=summary_rows(r); writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    if args.figures:figures(r)
    if args.update_paper:update_paper(r,body)
    manifest()


if __name__=='__main__':main()
