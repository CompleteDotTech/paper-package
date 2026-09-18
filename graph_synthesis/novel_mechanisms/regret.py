"""Distinct replacement experiment after a concurrent bipartite-method overlap."""
from __future__ import annotations
import argparse
from itertools import combinations, product
import json
from pathlib import Path
import random
import re
import socket
from unittest.mock import patch

from ..reliability.methods import graph_input, solve_graph
from .run import HERE, ROOT, sha, write

SEED = 20260923
PROTOCOL_COMMIT = '7a624f79c3f79b4c23a0879006bbe34412f126d9'
INTEGRATION_BASE = '7e2ce2fce28f29ebc6a2b462d063ea558b656cc1'
START = '<!-- INTERVAL_REGRET_RESEARCH_START -->'
END = '<!-- INTERVAL_REGRET_RESEARCH_END -->'
NOTICE = ('**Concurrent novelty reconciliation.** A main-branch study added the same broad bipartite '
          'flow mechanism while this branch was running. Original H4 is retained as concurrent replication, '
          'not counted as a fifth distinct addition. The five distinct mechanisms are H1, H2, H3, H5 and '
          '[H6: interval-priority minimax regret](REGRET_RESULTS.md). Both pre-execution protocols and all '
          'six outcomes are preserved; no worldwide novelty claim is made.')


def validate(nominal, intervals, edges):
    adj = graph_input(nominal, edges)
    if set(intervals) != set(nominal):
        raise ValueError('Exactly one interval per assertion required')
    for k, pair in intervals.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(type(v) is not int for v in pair):
            raise ValueError('Two integer interval endpoints required')
        if not 0 <= pair[0] <= nominal[k] <= pair[1]:
            raise ValueError('Nominal priority must lie inside its nonnegative interval')
    return adj


def subset_sums(values):
    sums = [0] * (1 << len(values))
    for mask in range(1, len(sums)):
        bit = mask & -mask
        sums[mask] = sums[mask ^ bit] + values[bit.bit_length()-1]
    return sums


def robust_select(nominal, intervals, edges, *, vertex_cap=12, pair_cap=1000000):
    """Minimize exact interval-box regret; cap failure never exposes a partial optimum."""
    if type(vertex_cap) is not int or not 0 <= vertex_cap <= 12:
        raise ValueError('Vertex cap must be an integer in [0,12]')
    if type(pair_cap) is not int or not 1 <= pair_cap <= 1000000:
        raise ValueError('Pair cap must be an integer in [1,1000000]')
    adj = validate(nominal, intervals, edges)
    staged = {'status':'staged', 'selected':[], 'regret':None, 'nominal_utility':None,
              'rival':[], 'witness':{}, 'pair_checks':0}
    keys = sorted(nominal)
    if len(keys) > vertex_cap:
        return {**staged, 'reason':'vertex_cap'}
    index = {k:i for i,k in enumerate(keys)}
    conflicts = [(1 << index[a]) | (1 << index[b]) for a in keys for b in sorted(adj[a]) if a < b]
    feasible = [mask for mask in range(1 << len(keys)) if all(mask & edge != edge for edge in conflicts)]
    if len(feasible)**2 > pair_cap:
        return {**staged, 'reason':'pair_cap'}
    low = subset_sums([intervals[k][0] for k in keys])
    high = subset_sums([intervals[k][1] for k in keys])
    point = subset_sums([nominal[k] for k in keys])
    names = {mask:tuple(k for i,k in enumerate(keys) if mask & (1 << i)) for mask in feasible}
    best = None
    for selected in feasible:
        rival = min(feasible, key=lambda other:(-(high[other & ~selected]-low[selected & ~other]), names[other]))
        regret = high[rival & ~selected]-low[selected & ~rival]
        score = (regret, -point[selected], names[selected])
        if best is None or score < best[0]:
            best = (score, selected, rival)
    score, selected, rival = best
    witness = {k:intervals[k][0 if k in names[selected] else 1] for k in keys}
    return {'status':'optimal', 'selected':list(names[selected]), 'regret':score[0],
            'nominal_utility':point[selected], 'rival':list(names[rival]), 'witness':witness,
            'pair_checks':len(feasible)**2, 'feasible_sets':len(feasible)}


def endpoint_oracle(nominal, intervals, edges):
    """Independent endpoint-scenario utility oracle; no proposed regret formula/helpers."""
    keys = sorted(nominal)
    possible = []
    for size in range(len(keys)+1):
        for selected in combinations(keys, size):
            if all(not(a in selected and b in selected) for a,b in edges):
                possible.append(selected)
    worst = {selected:0 for selected in possible}
    for endpoints in product((0,1), repeat=len(keys)):
        scenario = {k:intervals[k][endpoints[i]] for i,k in enumerate(keys)}
        utilities = {s:sum(scenario[k] for k in s) for s in possible}
        optimal = max(utilities.values())
        for selected, value in utilities.items():
            worst[selected] = max(worst[selected], optimal-value)
    best = min(possible, key=lambda s:(worst[s], -sum(nominal[k] for k in s), s))
    return {'selected':list(best), 'regret':worst[best],
            'nominal_utility':sum(nominal[k] for k in best)}, worst


def evaluate_case(nominal, intervals, edges):
    got = robust_select(nominal, intervals, edges)
    old = solve_graph(nominal, edges)
    oracle, all_regrets = endpoint_oracle(nominal, intervals, edges)
    baseline = {'selected':old['selected'], 'nominal_utility':old['utility'],
                'regret':all_regrets[tuple(sorted(old['selected']))]}
    witness = got['witness']
    witness_best = max(sum(witness[k] for k in selected) for selected in all_regrets)
    witness_regret = witness_best-sum(witness[k] for k in got['selected'])
    valid_witness = (all(intervals[k][0] <= witness[k] <= intervals[k][1] for k in nominal)
                     and sum(witness[k] for k in got['rival']) == witness_best
                     and witness_regret == got['regret'])
    return {'nominal':nominal, 'intervals':intervals, 'edges':edges, 'proposed':got,
            'baseline':baseline, 'oracle':oracle, 'valid_witness':valid_witness}


def execute():
    rng = random.Random(SEED)
    fixtures = []
    for case in range(128):
        keys = [f'a{i}' for i in range(8)]
        probability = (.15,.35,.55,.75)[case % 4]
        edges = [list(pair) for pair in combinations(keys,2) if rng.random() < probability]
        nominal = {k:rng.randint(1,9) for k in keys}
        intervals = {k:[rng.randint(0,nominal[k]),rng.randint(nominal[k],nominal[k]+9)] for k in keys}
        fixtures.append({'case':case, 'edge_probability':probability, **evaluate_case(nominal,intervals,edges)})
    failures = sum(any(row['proposed'][k] != row['oracle'][k] for k in ('selected','regret','nominal_utility')) for row in fixtures)
    consistency = sum(any(a in row['proposed']['selected'] and b in row['proposed']['selected'] for a,b in row['edges']) for row in fixtures)
    witness_failures = sum(not row['valid_witness'] for row in fixtures)
    regressions = sum(row['proposed']['regret'] > row['baseline']['regret'] for row in fixtures)
    improved = sum(row['proposed']['regret'] < row['baseline']['regret'] for row in fixtures)
    control = evaluate_case({'a':9,'b':8}, {'a':[0,10],'b':[8,8]}, [['a','b']])
    point = evaluate_case({'a':9,'b':8}, {'a':[9,9],'b':[8,8]}, [['a','b']])
    return {'protocol_commit':PROTOCOL_COMMIT, 'integration_baseline':INTEGRATION_BASE,
            'seed':SEED, 'fresh_service_calls':0, 'evidence':'Controlled interval-priority optimization, not semantic validation.',
            'source_hashes':{'graph_synthesis/novel_mechanisms/regret.py':sha(Path(__file__)),
                             'graph_synthesis/novel_mechanisms/REGRET_PROTOCOL.md':sha(HERE/'REGRET_PROTOCOL.md')},
            'primary_target_met':not(failures or consistency or witness_failures or regressions) and improved >= .1*len(fixtures),
            'fixtures':fixtures, 'oracle_failures':failures, 'consistency_failures':consistency,
            'witness_failures':witness_failures, 'regret_regressions':regressions, 'improved_cases':improved,
            'nominal_utility_losses':sum(row['proposed']['nominal_utility'] < row['baseline']['nominal_utility'] for row in fixtures),
            'fixed_control':control, 'zero_width_control':point,
            'outside_interval_control':{'actual_priorities':{'a':10,'b':0},'robust_selected':['b'],
                                        'actual_regret':10,'covered_by_supplied_intervals':False}}


def report_text(result):
    f = result['fixed_control']
    return '\n'.join(['# Interval-priority regret: fifth distinct addition after concurrent overlap','',
        'Timothy Wayne Gregg | AI-assisted author-review research extension | September 18, 2026','',
        '## Novelty reconciliation','',
        'Concurrent main-branch work independently added bipartite flow optimization. Original H4 is therefore retained as replication rather than counted as a distinct new mechanism. The five distinct additions in this PR are H1 label-shift correction, H2 dependence-robust bounds, H3 protected-fact repair, H5 indexed conflicts, and H6 interval-priority regret. Both original and replacement protocols remain in ancestry. This is repository-scoped novelty, not a new mathematical invention.','',
        f"The [replacement protocol](REGRET_PROTOCOL.md) was frozen in `{PROTOCOL_COMMIT}` before execution against the expanded main baseline `{INTEGRATION_BASE}`. The original experiments and unfavorable outcomes were not retuned. Fresh Jev service calls: {result['fresh_service_calls']}.",'',
        '## Hypothesis and falsification','',
        'Point-priority optimization can choose a fragile conflict-free set when priorities are uncertain. Test whether minimizing worst-case regret over supplied integer intervals reduces the maximum gap from an interval-consistent optimal selection. Regret is R(S)=max_w[max_T w(T)-w(S)]. For interval boxes this equals max_T[upper(T minus S)-lower(S minus T)]; the comparator is the actual previous nominal-priority solver. A separate oracle enumerates every endpoint scenario and computes utilities directly, rather than using this identity.','',
        'Enumeration is capped at 12 vertices and 1,000,000 candidate/rival comparisons. Exhaustion stages with no partial optimum. Exact ties maximize nominal utility and then use lexicographic assertion IDs. A rival set and endpoint priority assignment witness the returned worst-case gap. No graph writes are performed.','',
        'The frozen primary target requires zero oracle, consistency and witness failures, no regret regression, and strictly lower worst-case regret in at least 10% of 128 seeded eight-vertex fixtures. Edge densities alternate 0.15/0.35/0.55/0.75; priorities and intervals are generated under the protocol, seed 20260923.','',
        '## Executed results','',
        '| Measure | Observed |','|---|---:|',
        f"| Primary target | {'Met' if result['primary_target_met'] else 'Not met'} |",
        f"| Strictly lower worst-case regret | {result['improved_cases']}/128 ({result['improved_cases']/128:.2%}) |",
        f"| Oracle / consistency / witness failures | {result['oracle_failures']} / {result['consistency_failures']} / {result['witness_failures']} |",
        f"| Regret regressions | {result['regret_regressions']} |",
        f"| Cases sacrificing nominal utility | {result['nominal_utility_losses']}/128 |",'',
        f"In the fixed conflicting-pair control, nominal optimization chooses a (priority 9, interval [0,10]) over b (priority 8, interval [8,8]). Its worst-case regret is {f['baseline']['regret']}. The robust policy chooses b with regret {f['proposed']['regret']}, sacrificing one nominal utility unit. Zero-width intervals restore a zero-regret nominal optimum. The supplied intervals, not Jev probabilities, define the robustness claim.",'',
        '![H6. Worst-case regret compared with nominal priority optimization.](figures/06_interval_regret.png)','',
        '## Limits and negative controls','',
        'A smaller worst-case supplied-priority gap is not higher semantic accuracy. The random results explicitly report nominal utility sacrifices. Incorrect or overly narrow uncertainty intervals void the guarantee: actual priorities a=10,b=0 are outside the fixed control intervals and give the robust choice regret 10. Complete interval boxes may also be too pessimistic when priorities are dependent. No useful interval-estimation method, large-graph scalability, service latency or superiority to KARMA is established. Malformed inputs, cap exhaustion, nonmutation, edge-order invariance, equal/zero-width intervals and empty/disconnected graphs are regression-tested.','',
        '## Reproduction and attribution','',
        '```bash','python -B -m graph_synthesis.novel_mechanisms.regret',
        'python -B -m graph_synthesis.novel_mechanisms.regret --check',
        'python -B -m graph_synthesis.novel_mechanisms.regret --report',
        '```','',
        'The first command executes the experiment and writes per-case intervals, baseline/proposed selections, regret, independent oracle results, witnesses and input hashes. The second disables network access and checks exact replay. The third publishes the extra figure, standalone report and additive combined manuscript section. This is a deterministic bounded application of established minimax-regret ideas, not a reproduction of randomized or double-oracle algorithms: [Mastin, Jaillet and Chin](https://arxiv.org/abs/1401.7043); [Gilbert and Spanjaard](https://arxiv.org/abs/1602.01764).',''])


def insert_section(text, body):
    text = re.sub(re.escape(START)+r'.*?'+re.escape(END)+r'\s*','',text,flags=re.S)
    anchor = '<!-- NOVEL_MECHANISMS_RESEARCH_END -->'
    if text.count(anchor) != 1:
        raise ValueError('Require exactly one original new-mechanism block')
    before, after = text.split(anchor,1)
    return before+anchor+'\n\n'+START+'\n\n'+body.strip()+'\n\n'+END+'\n\n'+after.lstrip()


def reconcile(text, notice):
    # Applied only to the original experiment report/block, not other studies.
    text = text.replace('# Five new mechanisms for evidence-preserving Jev graph synthesis',
                        '# Five initial hypotheses: distinct additions and concurrent replication')
    text = text.replace('## 5. H4: Bipartite min-cut conflict optimization',
                        '## 5. H4: Bipartite min-cut conflict optimization (concurrent replication)')
    if notice not in text:
        first, rest = text.split('\n',1)
        text = first+'\n\n'+notice+'\n'+rest
    return text


def publish(result):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from .report import manifest
    matplotlib.rcParams['svg.hashsalt']='jev-interval-regret-20260918'
    fig, ax = plt.subplots(figsize=(8.5,4.8))
    rows = result['fixtures']
    x = [r['baseline']['regret'] for r in rows]; y = [r['proposed']['regret'] for r in rows]
    ax.scatter(x,y,alpha=.6,label='128 controlled fixtures')
    limit = max(x+y)+1
    ax.plot([0,limit],[0,limit],linestyle='--',label='Equal worst-case regret')
    ax.set(xlabel='Nominal selection: worst-case regret',ylabel='Robust selection: worst-case regret',
           title='H6 | Smaller worst-case gaps under supplied priority intervals')
    ax.legend()
    fig.text(.10,.02,f"{result['improved_cases']}/128 strictly improved; zero regret regressions.\n"
             f"{result['nominal_utility_losses']}/128 sacrifice nominal utility. Not semantic accuracy.",fontsize=9)
    fig.tight_layout(rect=(0,.13,1,1))
    folder = HERE/'figures'; folder.mkdir(exist_ok=True)
    fig.savefig(folder/'06_interval_regret.png',dpi=200,metadata={'Software':'paper-package interval-regret'})
    fig.savefig(folder/'06_interval_regret.svg',metadata={'Date':None,'Creator':'paper-package interval-regret'})
    plt.close(fig)
    body = report_text(result)
    (HERE/'REGRET_RESULTS.md').write_text(body,encoding='utf-8',newline='\n')
    original = HERE/'RESULTS.md'
    original.write_text(reconcile(original.read_text(encoding='utf-8'),NOTICE),encoding='utf-8',newline='\n')
    def rebase(match):
        url = match.group(1)
        return ']('+url+')' if '://' in url else '](../graph_synthesis/novel_mechanisms/'+url+')'
    paper = ROOT/'manuscript/paper-current.md'
    text = paper.read_text(encoding='utf-8')
    lo,hi = '<!-- NOVEL_MECHANISMS_RESEARCH_START -->','<!-- NOVEL_MECHANISMS_RESEARCH_END -->'
    begin,tail = text.split(lo,1); block,tail = tail.split(hi,1)
    notice = NOTICE.replace('](REGRET_RESULTS.md)','](../graph_synthesis/novel_mechanisms/REGRET_RESULTS.md)')
    text = begin+lo+'\n'+reconcile(block.lstrip(),notice)+hi+tail
    paper.write_text(insert_section(text,re.sub(r'\]\(([^)]+)\)',rebase,body)),encoding='utf-8',newline='\n')
    index = ROOT/'CURRENT_RESULTS.md'
    short = ('## Distinct replacement after concurrent novelty overlap\n\n'
             'Original H4 is concurrent replication of the separately merged bipartite study, not counted twice. '
             'The five distinct additions are H1, H2, H3, H5 and H6. '
             '[H6 results](graph_synthesis/novel_mechanisms/REGRET_RESULTS.md): '
             f"{result['improved_cases']}/128 lower worst-case priority-regret cases, with {result['regret_regressions']} regressions; "
             f"primary target {'met' if result['primary_target_met'] else 'not met'}. "
             'This is controlled interval-priority optimization, not semantic validation. All six executed outcomes and both frozen protocols remain available.')
    index.write_text(insert_section(index.read_text(encoding='utf-8'),short),encoding='utf-8',newline='\n')
    manifest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true'); parser.add_argument('--report',action='store_true')
    args = parser.parse_args()
    path = HERE/'regret-results.json'
    if args.report:
        publish(json.loads(path.read_text(encoding='utf-8')))
        print('Published distinct H6 replacement and documented H4 concurrent replication')
        return
    with patch.object(socket.socket,'connect',side_effect=RuntimeError('Network forbidden')), patch.object(socket,'create_connection',side_effect=RuntimeError('Network forbidden')):
        result = json.loads(json.dumps(execute(),allow_nan=False))
    if args.check:
        if json.loads(path.read_text(encoding='utf-8')) != result:
            raise AssertionError('Interval-regret results failed exact replay')
    else:
        write(path,result)
    print(json.dumps({'status':'reproduced' if args.check else 'executed', 'H6_target':result['primary_target_met'],
                      'improved':result['improved_cases'],'cases':128,'fresh_service_calls':0}))


if __name__=='__main__':main()
