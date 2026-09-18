"""Offline paired source-group analysis of the frozen multicall study."""
from collections import Counter, defaultdict
import argparse
import csv
import hashlib
import json
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

import numpy as np

from .multicall import ARMS, LABELS, ROOT, SITES, Runner, decisions, payloads, prediction, read, rows, write
from .core import digest

POSITIVE = {"SUPPORTS", "REFUTES"}
OUTCOMES = (*LABELS, "ERROR", "ABSTAIN")


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def vector(row, arm, selected=None):
    p=row["arms"][arm]
    accept=p["label"] in POSITIVE and (selected is None or row["id"] in selected)
    true=accept and p["label"]==row["gold"]
    v=np.zeros(23)
    v[:5]=[1,p["label"]==row["gold"],accept,true,row["gold"] in POSITIVE]
    v[5+LABELS.index(row["gold"])*5+OUTCOMES.index(p["label"])]=1
    v[20:]=[len(p["sites"]),p["input_tokens"],p["unknown_usage_calls"]]
    return v


def scores(v):
    n,correct,accepted,true,gold=v[:5]
    matrix=v[5:20].reshape((3,5))
    f1=[]
    for k in range(3):
        tp=matrix[k,k]; fn=matrix[k,:].sum()-tp; fp=matrix[:,k].sum()-tp
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)
    valid=matrix[:,:3].sum()
    return {"n":int(n),"correct":int(correct),"accuracy":correct/n if n else None,
            "conditional_accuracy":correct/valid if valid else None,"macro_f1":float(np.mean(f1)),
            "accepted":int(accepted),"correct_edges":int(true),"wrong_edges":int(accepted-true),
            "gold_edges":int(gold),"precision":true/accepted if accepted else None,"recall":true/gold if gold else None,
            "errors":int(matrix[:,3].sum()),"abstentions":int(matrix[:,4].sum()),
            "required_calls":int(v[20]),"input_tokens":int(v[21]),"unknown_usage_calls":int(v[22]),
            "correct_edges_per_million_input_tokens":1e6*true/v[21] if v[21] else None,
            "confusion":{g:{p:int(matrix[i,j]) for j,p in enumerate(OUTCOMES)} for i,g in enumerate(LABELS)}}


def group_vectors(data,arm,groups,selected=None):
    output=np.zeros((len(groups),23)); indexes={g:i for i,g in enumerate(groups)}
    for row in data:
        output[indexes[row["group"]]]+=vector(row,arm,selected)
    return output


def bootstrap(data, selections=None):
    groups=sorted({r["group"] for r in data})
    weights=np.random.default_rng(20260918).multinomial(len(groups),np.full(len(groups),1/len(groups)),size=2000)
    draws={arm:weights@group_vectors(data,arm,groups,None if selections is None else selections[arm]) for arm in ARMS}
    metrics={arm:[scores(v) for v in values] for arm,values in draws.items()}
    output={}
    for arm in ARMS[1:]:
        output[arm]={}
        for metric in ("precision","recall","macro_f1","accuracy"):
            delta=[b[metric]-a[metric] for a,b in zip(metrics['single'],metrics[arm]) if a[metric] is not None and b[metric] is not None]
            output[arm][metric]={"lower":float(np.quantile(delta,.025)) if delta else None,
                                 "upper":float(np.quantile(delta,.975)) if delta else None,"valid_draws":len(delta)}
    return {"groups":len(groups),"draws":2000,"direction":"arm_minus_single","intervals":output,
            "note":"Exploratory pointwise unadjusted group-bootstrap intervals; matched ID sets fixed before resampling."}


def analyze(directory):
    plan=read(directory/'plan.json'); values=read(directory/'predictions.json'); calls=rows(directory/'calls.jsonl')
    if len(values)!=len(plan['rows']) or len(calls)!=9*len(plan['rows']):
        raise ValueError('Incomplete run cannot produce a complete-study report')
    result={"schema_version":1,"evidence":"authentic additional Jev calls, fixed previously unused SciFact source groups",
            "execution":read(directory/'execution.json'),"splits":{},"source_hashes":{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ('plan.json','predictions.json','calls.jsonl')}}
    for split in ('development','test'):
        data=[r for r in values if r['split']==split]
        groups=sorted({r['group'] for r in data})
        arms={arm:scores(group_vectors(data,arm,groups).sum(axis=0)) for arm in ARMS}
        for arm in ARMS:
            positive_groups=clean_complete=contaminated=0
            for group in groups:
                members=[r for r in data if r['group']==group]
                gold_members=[r for r in members if r['gold'] in POSITIVE]
                wrong=any(r['arms'][arm]['label'] in POSITIVE and r['arms'][arm]['label']!=r['gold'] for r in members)
                contaminated+=wrong
                if gold_members:
                    positive_groups+=1
                    clean_complete+=not wrong and all(r['arms'][arm]['label']==r['gold'] for r in gold_members)
            arms[arm]['positive_source_groups']=positive_groups
            arms[arm]['complete_clean_positive_groups']=clean_complete
            arms[arm]['contaminated_source_groups']=contaminated
        k=min(s['accepted'] for s in arms.values())
        selections={arm:{r['id'] for r in sorted((r for r in data if r['arms'][arm]['label'] in POSITIVE),key=lambda r:(-r['arms'][arm]['score'],r['id']))[:k]} for arm in ARMS}
        matched={arm:scores(group_vectors(data,arm,groups,selections[arm]).sum(axis=0)) for arm in ARMS}
        result['splits'][split]={"n":len(data),"groups":len(groups),"arms":arms,"matched_k":k,"matched":matched,
                                 "selected_ids":{a:sorted(s) for a,s in selections.items()}}
        if split=='test':
            result['splits'][split]['bootstrap']=bootstrap(data)
            result['splits'][split]['matched_bootstrap']=bootstrap(data,selections)
    bycall={(r['id'],r['site']):r for r in calls}
    test=[r for r in values if r['split']=='test']
    overlaps=[]
    for left in ('base1','base2','base3','blind1','blind2'):
        for right in ('base1','base2','base3','blind1','blind2'):
            pairs=[(prediction(bycall[(r['id'],left)]),prediction(bycall[(r['id'],right)]),r['gold']) for r in test]
            valid=[(a,b,g) for a,b,g in pairs if a['status']==b['status']=='ok']
            n=len(valid); wrong_a=sum(a['label']!=g for a,b,g in valid); wrong_b=sum(b['label']!=g for a,b,g in valid)
            overlaps.append({"left":left,"right":right,"common_valid":n,
               "shared_errors":sum(a['label']!=g and b['label']!=g for a,b,g in valid),
               "wrong_agreement":sum(a['label']==b['label'] and a['label']!=g for a,b,g in valid),
               "label_disagreements":sum(a['label']!=b['label'] for a,b,g in valid),
               "independent_error_product_expected_count":wrong_a*wrong_b/n if n else None})
    result['error_overlap']=overlaps
    common=[r for r in test if all(r['arms'][a]['status']=='ok' for a in ARMS)]
    common_groups=sorted({r['group'] for r in common})
    result['posthoc_common_valid']={'status':'secondary diagnostic added after observing operational failures; does not replace full-denominator endpoints',
        'n':len(common),'groups':len(common_groups),
        'arms':{arm:scores(group_vectors(common,arm,common_groups).sum(axis=0)) for arm in ARMS}}
    result['latency_ms']={key:float(np.quantile([c['latency_ms'] for c in calls],p)) for key,p in [('p50',.5),('p95',.95),('p99',.99)]}
    result['call_statuses']=dict(Counter(c['error'] or 'ok' for c in calls))
    result['failed_calls_by_site']=dict(Counter(c['site'] for c in calls if c['error']))
    write(directory/'results.json',result)
    with (directory/'edge-outcomes.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['split','arm','n','accepted','correct_edges','wrong_edges','precision','recall','accuracy','macro_f1','errors','abstentions','required_calls','input_tokens']
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for split,data in result['splits'].items():
            for arm,s in data['arms'].items(): writer.writerow({'split':split,'arm':arm,**{k:s[k] for k in fields[2:]}})
    return result


def verify(directory):
    plan=read(directory/'plan.json'); values=read(directory/'predictions.json'); calls=rows(directory/'calls.jsonl')
    receipt=read(directory/'plan-receipt.json')
    assert hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest()==receipt['plan_sha256']
    assert hashlib.sha256((directory/'PROTOCOL.md').read_bytes()).hexdigest()==plan['protocol_sha256']
    assert len(calls)==9*len(plan['rows'])==len({(c['id'],c['site']) for c in calls})
    assert len(values)==len(plan['rows'])==len({r['id'] for r in values})
    previous=set(plan['excluded_prior_groups'])
    dev={r['group'] for r in plan['rows'] if r['split']=='development'}
    test={r['group'] for r in plan['rows'] if r['split']=='test'}
    assert not dev&test and not (dev|test)&previous
    for key in ('claim_id','document_id'):
        assert not {r[key] for r in plan['rows'] if r['split']=='development'}&{r[key] for r in plan['rows'] if r['split']=='test'}
    assert not {digest(r['evidence']) for r in plan['rows'] if r['split']=='development'}&{digest(r['evidence']) for r in plan['rows'] if r['split']=='test'}
    bycall={(c['id'],c['site']):c for c in calls}
    byvalue={r['id']:r for r in values}
    from pgc.decision.jev_real import JevRealBackend
    validator=JevRealBackend(transport=lambda _:None)
    for row in plan['rows']:
        panel={site:bycall[(row['id'],site)] for site in SITES}
        expected=payloads(row,plan,panel)
        for site,c in panel.items():
            assert c['request']==expected[site]
            assert c['request_hash']==digest(c['request']) and c['response_hash']==digest(c['response'])
            assert c['execution_mode']=='real' and c['metadata']['requested_model']==plan['model']
            assert c['metadata']['attempts']==1
            if not c['error']:
                validator._validate_response(c['response'],c['request']['questions'])
                assert c['metadata']['returned_model']==plan['model']
            if c['tokens_used'] is not None:
                assert validator._usage(c['response'])==c['tokens_used']
                assert c['budget_charge']==c['tokens_used']['input']
        assert byvalue[row['id']]=={'id':row['id'],'group':row['group'],'split':row['split'],'gold':row['gold_label'],'arms':decisions(panel)}
        assert panel['base1']['request']==panel['base2']['request']==panel['base3']['request']
        assert len({panel[k]['created_at'] for k in ('base1','base2','base3')})==3
    # Fresh temporary output; prohibit networking while reconstructing all decisions.
    with tempfile.TemporaryDirectory(prefix='multicall-replay-') as temp:
        work=Path(temp)
        for name in ('plan.json','plan-receipt.json','calls.jsonl'):
            shutil_copy(directory/name,work/name)
        with patch.object(socket.socket,'connect',side_effect=RuntimeError('No network during replay')), patch.object(socket,'create_connection',side_effect=RuntimeError('No network during replay')):
            Runner(work,live=False).execute()
        assert (work/'predictions.json').read_text(encoding='utf-8')==(directory/'predictions.json').read_text(encoding='utf-8')
        assert (work/'execution.json').read_text(encoding='utf-8')==(directory/'execution.json').read_text(encoding='utf-8')
        # Preserve the original byte hash after the explicit newline-equivalent replay check.
        shutil_copy(directory/'predictions.json',work/'predictions.json')
        # Regenerate into the isolated copy so verification cannot replace evidence.
        analyze(work)
        from .verify import compare_json
        compare_json(read(directory/'results.json'),read(work/'results.json'))
    report={'status':'passed','calls':len(calls),'cases':len(values),'gold_free_requests':True,
            'group_disjoint':True,'distinct_repeat_sites':True,'raw_response_validation':True,
            'network_disabled_replay':'identical predictions and execution after CRLF/LF normalization','analysis_reproduced':True,
            'analysis_comparison':'exact counts/labels/structure; float atol 1e-14, rtol 1e-12 for cross-platform roundoff',
            'limitation':'Request/response journals are local provenance, not provider-signed attestations; failed responses remain failures.'}
    write(directory/'verification.json',report)
    return report


def shutil_copy(source,target):
    target.write_bytes(source.read_bytes())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    if args.verify:
        result=verify(args.directory)
        print(json.dumps(result))
    else:
        result=analyze(args.directory)
        print(json.dumps(result['splits']['test']['arms'],indent=2))


if __name__=='__main__':
    main()
