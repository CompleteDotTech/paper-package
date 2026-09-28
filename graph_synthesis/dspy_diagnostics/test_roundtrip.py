"""Synthetic journal replay regression, not live model accuracy evidence."""
import gzip
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from graph_synthesis.dspy_benchmark import study
from .run import run
from .report import audit


class JournalBackend:
    def __init__(self,out,max_calls=2000):
        self.out=out;self.calls=0;self.tokens=0;self.lock=threading.Lock()
    def send(self,payload,site):
        answers={}
        for key,question in payload['questions'].items():
            if question['type']=='noul':answers[key]={'type':'noul','noul':.8}
            else:
                keys=list(question['criteria']);vector={label:1/len(keys) for label in keys}
                answers[key]={'type':'choice','choice':keys[0],'probabilities':vector}
        response={'model':study.MODEL,'answers':answers,'usage':{'input_tokens':10}}
        record={'site':site,'attempt':0,'payload':payload,'request_sha256':study.digest(payload),
                'response':response,'error':None,'http_status':200,'latency_seconds':.1}
        with self.lock:
            self.calls+=1;self.tokens+=10
            with gzip.open(self.out/'calls.jsonl.gz','at',encoding='utf-8') as f:f.write(study.canonical(record)+'\n')
        return response


class ReplayTests(unittest.TestCase):
    def test_entire_640_call_task_replays_exactly(self):
        task='entity_resolution';original,_,_=study.prepare(task)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);primary=root/'primary';primary.mkdir()
            for arm in study.ARMS[task]:
                out=primary/arm;out.mkdir();questions=original['question_specs'][task][arm]
                protocol={'revision':2,'task':task,'arm':arm,'baseline':questions}
                searches=[]
                for seed in study.SEEDS:
                    ledger=[{'iteration':0,'status':'baseline'}]
                    study.write_json(out/f'search-{seed}.json',ledger)
                    searches.append({'seed':seed,'accuracy_questions':questions,'ledger_sha256':study.digest(ledger)})
                frozen={'protocol_sha256':study.digest(protocol),'searches':searches}
                fit={'temperature':1.,'temperature_bias':{'temperature':1.,'bias':[0.,0.]}}
                for name,value in [('protocol',protocol),('freeze',{'payload':frozen,'sha256':study.digest(frozen)}),
                    ('execution',{'status':'completed'}),('calibration',{'fits':[fit]*11})]:study.write_json(out/(name+'.json'),value)
            output=root/'diagnostic'
            with patch.object(study,'Live',JournalBackend):run(task,primary,output)
            results,drift,packing,costs,execution=audit(output,primary)
            self.assertEqual(execution['http_attempts'],640)
            self.assertEqual(len(results),4*6*3*3)
            self.assertEqual(len(drift),24);self.assertEqual(len(packing),2);self.assertEqual(len(costs),4)
            self.assertTrue(all(r['repeat_rows_with_label_disagreement']==0 for r in drift))
            with (output/'predictions.json').open('a') as f:f.write(' ')
            with self.assertRaises(ValueError):audit(output,primary)


if __name__=='__main__':unittest.main()
