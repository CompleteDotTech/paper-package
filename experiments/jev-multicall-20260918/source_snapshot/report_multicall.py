"""Data-derived charts and paper addendum for the additional-call study."""
import argparse
import hashlib
import json
from pathlib import Path

from .multicall import ARMS, ROOT, read
from .analyze_multicall import write

NAMES={'single':'Single call','repeat_vote':'Repeated vote','blind_vote':'Blind vote','targeted':'Targeted checks',
       'structured':'Indexed evidence','contrastive':'Contrastive examples','selective':'Selective routing'}
COLORS=['#426480','#258a75','#d79832','#a85156','#68589c','#4194a6','#687b39']


def build(directory):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'svg.hashsalt':'multicall-20260918','font.size':10})
    r=read(directory/'results.json'); test=r['splits']['test']; arms=test['arms']; matched=test['matched']
    output=directory/'figures'; output.mkdir(exist_ok=True)
    def save(fig,name):
        fig.tight_layout()
        for ext in ('png','svg'):
            fig.savefig(output/(name+'.'+ext),dpi=180,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
    labels=[NAMES[a] for a in ARMS]; x=np.arange(len(ARMS))
    fig,ax=plt.subplots(figsize=(10,4.8))
    correct=[arms[a]['correct_edges'] for a in ARMS]; wrong=[arms[a]['wrong_edges'] for a in ARMS]
    ax.barh(x,correct,color='#258a75',label='Correct accepted edge')
    ax.barh(x,wrong,left=correct,color='#a85156',label='Wrong accepted edge')
    for i,(c,w) in enumerate(zip(correct,wrong)): ax.text(c+w+1,i,f'{c} / {w}',va='center')
    ax.set(yticks=x,yticklabels=labels,xlabel='Accepted typed edges (annotation: correct / wrong)',title=f'Fresh test panel: {test["n"]} candidates in {test["groups"]} source groups')
    ax.legend(loc='lower right'); ax.set_xlim(0,max(c+w for c,w in zip(correct,wrong))*1.2)
    save(fig,'01_edge_outcomes')
    fig,ax=plt.subplots(figsize=(9,5))
    for arm,color in zip(ARMS,COLORS):
        ax.scatter(100*arms[arm]['recall'],100*arms[arm]['precision'],s=80,color=color,label=NAMES[arm])
    ax.set(xlabel='Correct-edge recall (%)',ylabel='Accepted-edge precision (%)',title='Unchanged operating points; higher precision can sacrifice recall')
    ax.legend(bbox_to_anchor=(1.02,1),loc='upper left'); ax.grid(alpha=.15)
    save(fig,'02_precision_recall')
    fig,ax=plt.subplots(figsize=(10,4.5))
    ax.barh(labels,[matched[a]['wrong_edges'] for a in ARMS],color=COLORS)
    ax.set(xlabel='Incorrect accepted edges (lower is better)',title=f'Equal output volume: top {test["matched_k"]} edges per arm; score then ID')
    save(fig,'03_matched_errors')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    axes[0].barh(labels,[arms[a]['required_calls'] for a in ARMS],color=COLORS)
    axes[1].barh(labels,[arms[a]['input_tokens']/1e6 for a in ARMS],color=COLORS)
    axes[0].set(xlabel='Required HTTP calls',title='Test-policy resource accounting')
    axes[1].set(xlabel='Reported input tokens (millions)',title='Shared experiment calls reused for comparisons')
    fig.suptitle('Selective routing is retrospective; every branch was actually executed',fontsize=11)
    save(fig,'04_cost')
    sites=['base1','base2','base3','blind1','blind2']
    z=np.array([[next(v['wrong_agreement'] for v in r['error_overlap'] if v['left']==a and v['right']==b) for b in sites] for a in sites])
    fig,ax=plt.subplots(figsize=(6,5)); im=ax.imshow(z,cmap='OrRd'); fig.colorbar(im,ax=ax,label='Common-valid wrong-label agreements')
    for i in range(5):
        for j in range(5): ax.text(j,i,str(z[i,j]),ha='center',va='center',color='black')
    ax.set(xticks=range(5),yticks=range(5),xticklabels=sites,yticklabels=sites,title='Same-model errors can persist across calls')
    save(fig,'05_wrong_agreement')
    fig,ax=plt.subplots(figsize=(9,4.5))
    for i,arm in enumerate(ARMS[1:]):
        effect=100*(matched[arm]['precision']-matched['single']['precision'])
        ci=test['matched_bootstrap']['intervals'][arm]['precision']
        lo,hi=100*ci['lower'],100*ci['upper']
        ax.plot([lo,hi],[i,i],color=COLORS[i+1],linewidth=2)
        ax.scatter(effect,i,color=COLORS[i+1],s=50)
    ax.axvline(0,color='.5',linestyle='--')
    ax.set(yticks=range(6),yticklabels=[NAMES[a] for a in ARMS[1:]],xlabel='Matched precision difference vs single (percentage points)',title='Paired 95% source-group intervals; exploratory and unadjusted')
    save(fig,'06_paired_effects')
    # Lexicographically first multi-candidate test group, chosen without outcome quality.
    values=read(directory/'predictions.json'); plan=read(directory/'plan.json')
    lookup={v['id']:v for v in values}; candidates=[v for v in plan['rows'] if v['split']=='test']
    groups=sorted({v['group'] for v in candidates})
    group=next((g for g in groups if sum(v['group']==g for v in candidates)>1),groups[0])
    examples=[v for v in candidates if v['group']==group]
    docs=sorted({v['document_id'] for v in examples}); claims=sorted({v['claim_id'] for v in examples})
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for ax,arm in zip(axes,('single','targeted')):
        positions={('d',s):(0,1-i/max(1,len(docs)-1)) for i,s in enumerate(docs)}
        positions.update({('c',s):(1,1-i/max(1,len(claims)-1)) for i,s in enumerate(claims)})
        for v in examples:
            d=lookup[v['id']]['arms'][arm]; a=positions[('d',v['document_id'])]; b=positions[('c',v['claim_id'])]
            accepted=d['label'] in ('SUPPORTS','REFUTES')
            color='#258a75' if d['label']==v['gold_label'] else '#a85156'
            ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':color if accepted else '#aaa','linestyle':'-' if accepted else ':'})
            ax.text(.5,(a[1]+b[1])/2,d['label'],fontsize=8,ha='center',backgroundcolor='white')
        for (kind,name),(px,py) in positions.items():
            ax.scatter(px,py,s=160,color='#426480' if kind=='d' else '#d79832',zorder=3)
            ax.text(px,py+.08,f'{"Doc" if kind=="d" else "Claim"} {name}',ha='center',fontsize=8)
        ax.set(xlim=(-.35,1.35),ylim=(-.25,1.25),title=NAMES[arm]); ax.axis('off')
    fig.suptitle('First multi-candidate group by ID: solid = accepted, dotted = no edge\nGreen/red = agrees/disagrees with gold; source-to-claim direction',fontsize=10)
    save(fig,'07_evidence_graph')
    write(directory/'graph-example.json',{'selection':'first multi-candidate test group by sorted group ID; no outcome filtering','group':group,'rows':examples,'predictions':[lookup[v['id']] for v in examples]})
    lines=['# Do additional Jev calls improve graph edges?','',
       'Timothy Wayne Gregg — exploratory research addendum, September 18, 2026','',
       '## Design and evidence boundary','',
       f'This study uses {r["splits"]["development"]["n"]} development candidates in 40 connected source groups and {test["n"]} test candidates in {test["groups"]} other groups. These are previously unused within the archived Jev runs, taken from public SciFact training data. They are not a new domain, private benchmark, or guaranteed absent from vendor training. The frozen protocol, data split, prompt implementation and seed were committed before calls in `2eb44a1`. No development tuning or test-based prompt/threshold selection occurred. All seven policies were retained.', '',
       'The single arm uses the previous six-example relation contract. Repeated voting uses three identical-payload fresh calls. Blind voting combines the first answer with two different evidence-only reviewers that never see another answer. Targeted checks use a first judgment, six dimensional checks in one shared request, then adjudication against original evidence. Indexed evidence preserves every sentence and adds explicit IDs. Contrastive examples replace the six original demonstrations with six fixed synthetic boundary examples. Selective routing applies targeted checks only when the first maximum score is below 0.90 or the first call fails; it is reconstructed retrospectively because all branches were actually executed. Three targeted calls contain eight typed decisions, whereas three voting calls contain three. Neither agreement nor a mean score is treated as independent or calibrated evidence.','',
       '## Test results','',
       '| Policy | Correct / wrong edges | Precision | Recall | Macro-F1 | Errors / abstentions |','|---|---:|---:|---:|---:|---:|']
    for arm in ARMS:
        s=arms[arm]
        lines.append(f'| {NAMES[arm]} | {s["correct_edges"]} / {s["wrong_edges"]} | {s["precision"]:.2%} | {s["recall"]:.2%} | {s["macro_f1"]:.4f} | {s["errors"]} / {s["abstentions"]} |')
    lines += ['', '![Edge outcomes](figures/01_edge_outcomes.png)','', '![Precision and recall](figures/02_precision_recall.png)','',
       f'All {test["n"]} cases remain in classification denominators. Wrong polarity counts as an incorrect accepted edge and a missed gold edge. NOT_ENOUGH_INFO is a legitimate classification that creates no positive edge. Probability failures are not silently normalized or discarded.','',
       '## Equal accepted-edge volume','',f'Each policy is ranked by its declared score, with ID tie-breaking, and restricted to the same {test["matched_k"]} accepted edges. Scores order proposals; they are not comparable calibrated probabilities. This is an evaluation diagnostic, not a deployed threshold.','',
       '| Policy | Correct / wrong | Precision difference vs single | Paired 95% interval |','|---|---:|---:|---:|']
    for arm in ARMS:
        s=matched[arm]; delta=100*(s['precision']-matched['single']['precision'])
        ci=test['matched_bootstrap']['intervals'].get(arm,{}).get('precision')
        interval=f'[{100*ci["lower"]:+.2f}, {100*ci["upper"]:+.2f}] pp' if ci else 'reference'
        lines.append(f'| {NAMES[arm]} | {s["correct_edges"]} / {s["wrong_edges"]} | {delta:+.2f} pp | {interval} |')
    lines += ['', '![Matched errors](figures/03_matched_errors.png)','', '![Paired differences](figures/06_paired_effects.png)','',
        'Intervals use 2,000 paired source-group bootstrap draws. They are pointwise, unadjusted and exploratory across multiple methods/endpoints, conditional on the selected ID sets and observed groups. Selected sets are fixed before resampling; per-draw edge counts can differ. Hidden cross-group dependence is not ruled out. Equal volume does not imply equal token budget.','',
        '## Calls, tokens and efficiency','', '| Policy | Test calls required | Test input tokens | Correct edges / million tokens |','|---|---:|---:|---:|']
    for arm in ARMS:
        s=arms[arm]
        lines.append(f'| {NAMES[arm]} | {s["required_calls"]} | {s["input_tokens"]:,} | {s["correct_edges_per_million_input_tokens"]:.1f} |')
    execution=r['execution']
    lines += ['', f'The entire executed study made {execution["logical_calls"]:,} calls and used {execution["reported_input_tokens"]:,} reported input tokens, including development and every branch. There were {execution["failed_calls"]} failed calls and {execution["unknown_usage_calls"]} calls with unknown usage. The table attributes shared calls to each hypothetical policy; summing its rows would double-count them. Selective costs are retrospective required-call estimates, not separately observed routed-service latency. Single-call latency across actual requests was p50 {r["latency_ms"]["p50"]:.0f} ms, p95 {r["latency_ms"]["p95"]:.0f} ms and p99 {r["latency_ms"]["p99"]:.0f} ms; these are not end-to-end policy latencies.', '',
        '![Cost comparison](figures/04_cost.png)','',
        '## Error dependence and graph consequences','',
        '![Wrong-label agreement](figures/05_wrong_agreement.png)','',
        'This heatmap counts wrong-label agreement on common-valid cases, not independent corroboration. Diagonal entries are individual error counts. Different prompts and repeated calls still share the same model and evidence.','',
        '| Policy | Complete and clean positive groups | Contaminated groups |','|---|---:|---:|']
    for arm in ARMS:
        s=arms[arm]
        lines.append(f'| {NAMES[arm]} | {s["complete_clean_positive_groups"]}/{s["positive_source_groups"]} | {s["contaminated_source_groups"]}/{test["groups"]} |')
    lines += ['', '![Illustrative graph](figures/07_evidence_graph.png)','',
        'The graph is the first multi-candidate test group in sorted group-ID order, without selecting for favorable outcomes. Whole-group correctness is different from average edge precision. A clean but incomplete or empty graph is not full synthesis.','',
        '## Operational failures and secondary diagnostic','',
        f'Across development and test, failures by call site were: {json.dumps(r["failed_calls_by_site"],sort_keys=True)}. Error reasons were: {json.dumps({k:v for k,v in r["call_statuses"].items() if k!="ok"},sort_keys=True)}. The six-question check request exposes multiple probability vectors to the strict validation rule. A single invalid prerequisite invalidates the targeted pipeline under the frozen policy; these failures are not repaired after observing test outcomes.', '',
        f'After observing these failures, we added a secondary **common-valid** diagnostic on the {r["posthoc_common_valid"]["n"]} test cases where every policy returned a valid decision. This outcome-conditioned subset does not replace the operational comparison or demonstrate deployment quality.', '',
        '| Policy | Common-valid accuracy | Correct / wrong edges |', '|---|---:|---:|']
    for arm in ARMS:
        s=r['posthoc_common_valid']['arms'][arm]
        lines.append(f'| {NAMES[arm]} | {s["accuracy"]:.2%} | {s["correct_edges"]} / {s["wrong_edges"]} |')
    repeated=next(x for x in r['error_overlap'] if x['left']=='base1' and x['right']=='base2')
    savings=100*(1-arms['contrastive']['input_tokens']/arms['single']['input_tokens'])
    lines += ['', f'The first two repeated calls shared {repeated["shared_errors"]} wrong answers across {repeated["common_valid"]} common-valid test cases; {repeated["wrong_agreement"]} had the same wrong label. This explains why an additional call need not supply new corrective evidence. The product of marginal error rates predicts {repeated["independent_error_product_expected_count"]:.2f} shared errors as a descriptive independence reference, not a hypothesis test.', '',
        f'The strongest efficiency lead is the shorter contrastive-example prompt: {savings:.2f}% fewer test input tokens than the single-call original-demonstration prompt, with equal wrong-edge count at matched volume. At its natural operating point it also recovers fewer correct edges. This is not a noninferiority or statistical-equivalence finding, and different demonstration content plus length prevents attributing the outcome to contrast alone.', '',
        '## Interpretation','']
    for arm in ARMS[1:]:
        ci=test['matched_bootstrap']['intervals'][arm]['precision']; delta=matched[arm]['correct_edges']-matched['single']['correct_edges']
        conclusion='includes zero; no resolved matched-volume advantage' if ci['lower']<=0<=ci['upper'] else ('is positive; an exploratory matched-volume signal' if ci['lower']>0 else 'is negative; an exploratory matched-volume degradation')
        lines.append(f'- **{NAMES[arm]}:** {delta:+d} correct edges versus single at equal volume; the interval {conclusion}.')
    lines += ['', 'No policy is promoted automatically. A positive pointwise interval would still require independent confirmation and a matched-resource comparison before claiming general superiority. More calls can expose mistakes, reinforce the same error, or reject correct edges. These bounded claim–abstract decisions do not measure open-ended candidate discovery, database-scale synthesis, world-truth validation or safe unattended writes. Public training-data reuse, a single pinned service revision, synthetic contrast demonstrations, unequal prompt lengths, shared-context check dependence, and modest source-group counts limit generalization.','',
       '## Reproduction','',
       'The directory includes the pre-call plan/protocol/source snapshots, raw responses, decoded predictions, costs, source-group intervals, CSV tables, seven SVG/PNG figures and a deterministic graph example. `python -B -m graph_synthesis.analyze_multicall --directory experiments/jev-multicall-20260918 --verify` validates raw inputs/responses, split isolation and distinct repeat call sites, prohibits network access during replay, and reproduces predictions and analyses. `python -B -m graph_synthesis.report_multicall --directory experiments/jev-multicall-20260918` rebuilds this report and charts. Prior results and the original immutable manuscript remain separately archived.','']
    text='\n'.join(lines)
    (directory/'REPORT.md').write_text(text,encoding='utf-8',newline='\n')
    # Preserve the prior current manuscript verbatim as a historical appendix.
    historical=ROOT/'manuscript/paper-before-multicall.md'
    if not historical.exists():
        historical.write_bytes((ROOT/'manuscript/paper-current.md').read_bytes())
    current=text.replace('](figures/','](../experiments/jev-multicall-20260918/figures/')
    current+='\n\n---\n\n# Prior same-data rerun and original study (historical evidence)\n\n'+historical.read_text(encoding='utf-8')
    (ROOT/'manuscript/paper-current.md').write_text(current,encoding='utf-8',newline='\n')
    write(output/'manifest.json',{'source_results_sha256':hashlib.sha256((directory/'results.json').read_bytes()).hexdigest(),
       'figures':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.suffix in ('.svg','.png')}})
    print(json.dumps({'figures':7,'report':str(directory/'REPORT.md')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    build(parser.parse_args().directory)
