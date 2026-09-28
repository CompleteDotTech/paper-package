"""Use bounded component normalization for forecasts without altering original policies."""
import argparse
from pathlib import Path
from graph_synthesis.dspy_multicall import run as original
from graph_synthesis.dspy_benchmark.study import sha,read
from graph_synthesis.dspy_jev_optimizer.core import write_json
from .adapter import distribution


def forecasts(calls,choices):
    def p(site):
        values=calls[site]['response']['answers']['decision']['probabilities']
        return distribution([values[label] for label in original.LABELS])
    output={}
    for arm,result in choices.items():
        if arm in ('repeat_vote','blind_vote'):
            sites=('base1','base2','base3') if arm=='repeat_vote' else ('base1','blind1','blind2')
            vector=sum((p(site) for site in sites))/3
        elif arm=='selective':vector=p('adjudicate' if len(result['sites'])==3 else 'base1')
        else:vector=p({'single':'base1','targeted':'adjudicate','structured':'structured','contrastive':'contrastive'}[arm])
        output[arm]=vector.tolist()
    return output


def install():
    original.forecasts=forecasts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--shard',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if read(a.capture/'execution.json').get('status')!='completed' or read(a.capture/'protocol.json').get('revision')!=2:
        raise ValueError('Require a complete amendment-v2 primary capture')
    install();original.run(a.capture,a.shard,a.output)
    write_json(a.output/'amendment.json',{'revision':2,'wrapper_sha256':sha(__file__),
        'scope':'Only normalized forecasts use the bounded mass interpretation; original policy scores, labels and adjudication inputs stay raw.'})
    write_json(a.output/'artifact-manifest.json',{'sha256':{f.name:sha(f) for f in sorted(a.output.iterdir()) if f.is_file() and f.name!='artifact-manifest.json'}})

if __name__=='__main__':main()
