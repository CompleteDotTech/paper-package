"""Reconstruct the scoped novelty audit from the immutable Git baseline."""
import hashlib
import json
import re
import subprocess
from .report import HERE, ROOT, write


def main():
    baseline='a62a3257645d8e35cd4e45be53bfa9511d27724b'
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',baseline],cwd=ROOT,text=True).splitlines()
    paths=[n for n in names if n.startswith('graph_synthesis/') and n.endswith(('.py','.md'))]
    terms=['latent','bipartite','decision diagram','segment tree','knapsack','review cost','false.removal']
    hits={term:[] for term in terms}; hashes={}
    for path in paths:
        content=subprocess.check_output(['git','show',baseline+':'+path],cwd=ROOT)
        hashes[path]=hashlib.sha256(content).hexdigest()
        for term in terms:
            if re.search(term,content.decode('utf-8'),re.I):hits[term].append(path)
    record={'baseline_commit':baseline,'snapshot_commit':'02de0cb34a90117805ba13bd0bcb313898ee1197',
            'scope':'All baseline graph_synthesis Python and Markdown files. The snapshot adds only a source-packaging workflow to baseline. Symbol search is an aid, not proof of global novelty.',
            'terms':terms,'matches':hits,'files':hashes}
    write(HERE/'novelty-audit.json',json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'novelty_scope':'pinned baseline only','files_audited':len(paths),'baseline':baseline}))


if __name__=='__main__':main()
