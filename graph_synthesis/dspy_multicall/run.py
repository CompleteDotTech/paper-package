"""Fresh matched multi-call evaluations; no prompt search or label-based policy changes."""
from __future__ import annotations
import argparse
import copy
import gzip
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from graph_synthesis.dspy_benchmark.study import (Live, MODEL, SEEDS, ROOT, EXTRA,
    prepare, read, sha, validate_questions)
from graph_synthesis.dspy_jev_optimizer.core import canonical, digest, write_json
from graph_synthesis.multicall import payloads, decisions, LABELS, ARMS

SHARDS=8


def load_configs(capture):
    """Use every accuracy-selected seed; never rank prompts by their test performance."""
    protocol=read(capture/'protocol.json')
    if protocol['task']!='relation_support' or protocol['arm']!='fewshot_contract' or protocol['seeds']!=SEEDS:
        raise ValueError('Wrong upstream experiment')
    freeze=read(capture/'freeze.json')
    if freeze['sha256']!=digest(freeze['payload']) or freeze['payload']['protocol_sha256']!=digest(protocol):
        raise ValueError('Invalid upstream freeze')
    original,_,_=prepare('relation_support')
    baseline=original['question_specs']['relation_support']['fewshot_contract']
    variants=[('baseline',0,baseline)]
    for search in freeze['payload']['searches']:
        if digest(read(capture/f"search-{search['seed']}.json"))!=search['ledger_sha256']:
            raise ValueError('Upstream search changed')
        cfg=validate_questions(search['accuracy_questions'],baseline)
        variants.append(('dspy',search['seed'],cfg))
    if [x[1] for x in variants[1:]]!=SEEDS:raise ValueError('Missing searches')
    return variants,freeze['sha256']


def call_response(answers,usage=None):
    return {'response':{'model':MODEL,'answers':answers},'tokens_used':{'input':0},'error':None}


def forecasts(calls,choices):
    """Normalized component mixture for votes; not a claim of independent votes."""
    def p(site):return np.array([calls[site]['response']['answers']['decision']['probabilities'][label] for label in LABELS])
    output={}
    for arm,result in choices.items():
        if arm in ('repeat_vote','blind_vote'):
            sites=('base1','base2','base3') if arm=='repeat_vote' else ('base1','blind1','blind2')
            vector=sum((p(site) for site in sites))/3
        elif arm=='selective':vector=p('adjudicate' if len(result['sites'])==3 else 'base1')
        else:vector=p({'single':'base1','targeted':'adjudicate','structured':'structured','contrastive':'contrastive'}[arm])
        if np.any(~np.isfinite(vector)) or np.any(vector<0) or not np.isclose(vector.sum(),1,atol=1e-6):
            raise ValueError('Invalid workflow forecast')
        output[arm]=vector.tolist()
    return output


def evaluate_row(row,plan,variants,live,phase):
    initial=payloads(row,plan)
    calls=[{} for _ in variants]
    # Only the primary few-shot verifier text changes; workflow rules stay fixed.
    for site in ('base1','base2','base3','structured','contrastive'):
        q={f'v{i}__decision':next(iter(cfg.values())) for i,(_,_,cfg) in enumerate(variants)}
        request={**initial[site],'questions':q}
        raw=live.send(request,phase+'/'+row['id']+'/'+site)
        for i in range(len(variants)):
            calls[i][site]=call_response({'decision':raw['answers'][f'v{i}__decision']})
    # Blinded reviewers and dimension checks are common controls, not independently resampled per seed.
    q={f'{site}__{k}':v for site in ('blind1','blind2','checks') for k,v in initial[site]['questions'].items()}
    raw=live.send({**initial['checks'],'questions':q},phase+'/'+row['id']+'/common_reviews')
    for site in ('blind1','blind2','checks'):
        answer={k:raw['answers'][f'{site}__{k}'] for k in initial[site]['questions']}
        for variant_calls in calls:variant_calls[site]=call_response(copy.deepcopy(answer))
    results=[]
    for i,(selection,seed,_) in enumerate(variants):
        request=payloads(row,plan,calls[i])['adjudicate']
        raw=live.send(request,phase+'/'+row['id']+'/adjudicate/'+str(i))
        calls[i]['adjudicate']=call_response(raw['answers'])
        chosen=decisions(calls[i]);vectors=forecasts(calls[i],chosen)
        results.append({'selection':selection,'seed':seed,
                        'workflows':{a:{'status':chosen[a]['status'],'label':chosen[a]['label'],
                            'raw_score':chosen[a]['score'],'sites':chosen[a]['sites'],
                            'forecast':vectors[a]} for a in ARMS}})
    return {'id':row['id'],'gold_label':row['gold_label'],'group':row.get('group',row['id']),
            'phase':phase,'original_split':row.get('split'), 'variants':results}


def run(capture,shard,output):
    if not 0<=shard<SHARDS:raise ValueError('Invalid shard')
    if output.exists():raise ValueError('Do not overwrite captured evidence')
    variants,upstream_hash=load_configs(capture)
    plan=read(ROOT/EXTRA);_,parts,_=prepare('relation_support')
    rows=[('calibration',r) for r in parts['calibration']]+[('additional_corpus',r) for r in plan['rows']]
    assigned=[(phase,row) for i,(phase,row) in enumerate(rows) if i%SHARDS==shard]
    output.mkdir(parents=True)
    write_json(output/'protocol.json',{'model':MODEL,'shard':shard,'shards':SHARDS,'rows':len(assigned),
        'upstream_freeze_sha256':upstream_hash,'variants':[{'selection':s,'seed':seed,'questions_sha256':digest(c)} for s,seed,c in variants],
        'source_sha256':sha(__file__),'original_multicall_source_sha256':sha(ROOT/'graph_synthesis/multicall.py'),
        'original_plan_sha256':sha(ROOT/EXTRA),'scope':'Transfer of five frozen primary-verifier prompts; other reviewers, escalation threshold and workflow rules unchanged.'})
    live=Live(output,max_calls=2000)
    def one(item):
        phase,row=item
        result=evaluate_row(row,plan,variants,live,phase)
        with live.lock:
            with gzip.open(output/'predictions.jsonl.gz','at',encoding='utf-8') as f:f.write(canonical(result)+'\n')
        print(canonical({'shard':shard,'completed_row':row['id'],'phase':phase}),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(one,assigned))
    write_json(output/'execution.json',{'status':'completed','live':True,'rows':len(assigned),'http_attempts':live.calls,
        'reported_input_tokens':live.tokens,'estimated_jev_usd':live.tokens*.042/1_000_000})
    write_json(output/'artifact-manifest.json',{'sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'}})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--shard',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.capture,args.shard,args.output)

if __name__=='__main__':main()
