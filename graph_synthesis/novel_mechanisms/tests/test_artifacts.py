"""Audit stored evidence independently of the algorithms that generated it."""
from fractions import Fraction
from itertools import product
import json
import unittest
from graph_synthesis.novel_mechanisms.run import HERE,ROOT,sha
from graph_synthesis.novel_mechanisms.report import START,END,ANCHOR,replace_after_anchor,render


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=HERE/'results.json'
        if not path.exists():raise unittest.SkipTest('Execute the frozen benchmark before artifact auditing')
        cls.r=json.loads(path.read_text(encoding='utf-8'))

    def test_source_and_implementation_hashes(self):
        for group in ('source_hashes','implementation_hashes'):
            for path,want in self.r[group].items():self.assertEqual(sha(ROOT/path),want,path)
        self.assertEqual(self.r['fresh_service_calls'],0)

    def test_fit_ids_disjoint_and_predictions_complete(self):
        h=self.r['H1'];fit=h['fit'];self.assertFalse(set(fit['fit_ids'])&set(fit['target_ids']))
        self.assertEqual(len(fit['fit_ids']),73);self.assertEqual(len(fit['target_ids']),263)
        for predictions in h['predictions'].values():
            self.assertEqual(sorted(p['id'] for p in predictions),fit['target_ids'])
        for name,ids in h['selected_ids'].items():
            self.assertEqual(len(ids),h['matched_k']);self.assertEqual(len(ids),len(set(ids)))
            self.assertEqual(h['matched'][name]['accepted'],len(ids))

    def test_joint_truth_and_every_dual_certificate(self):
        for fixture in self.r['H2']['fixtures']:
            atoms=fixture['atoms'];weights=fixture['joint_integer_weights'];total=sum(weights)
            truth=Fraction(0)
            for mask,weight in enumerate(weights):
                active={a for i,a in enumerate(atoms) if mask&(1<<i)}
                if any(set(proof)<=active for proof in fixture['proofs']):truth+=Fraction(weight,total)
            self.assertEqual(truth,Fraction(fixture['truth']))
            got=fixture['proposed'];self.assertLessEqual(Fraction(got['lower_rational']),truth)
            self.assertGreaterEqual(Fraction(got['upper_rational']),truth)
            for cert in got['certificates']:
                y=list(map(Fraction,cert['dual']));keys=got['atoms']
                for bits in product((0,1),repeat=len(keys)):
                    active={a for a,b in zip(keys,bits) if b};v=int(any(set(proof)<=active for proof in fixture['proofs']))
                    self.assertLessEqual(y[0]+sum(q*b for q,b in zip(y[1:],bits)),cert['sign']*v)
                self.assertEqual(y[0]+sum(q*Fraction(fixture['marginals'][a]) for q,a in zip(y[1:],keys)),Fraction(cert['value']))

    def test_repairs_really_preserve_protected_proofs(self):
        for row in self.r['H3']['fixtures']:
            got=row['proposed'];self.assertEqual(got['status'],row['oracle']['status'])
            if got['status']!='optimal':continue
            removed=set(got['removed']);self.assertEqual(got['cost'],sum(row['costs'][a] for a in removed))
            self.assertTrue(all(removed&set(proof) for proof in row['target']))
            self.assertTrue(all(any(not removed&set(proof) for proof in fact) for fact in row['protected']))
            self.assertEqual(got['cost'],row['oracle']['cost'])

    def test_selected_sets_consistent_and_cover_flow_dual(self):
        for row in self.r['H4']['fixtures']+self.r['H4']['general_controls']:
            got=row['proposed'];chosen=set(got['selected']);weights=row['weights']
            self.assertFalse(any(a in chosen and b in chosen for a,b in row['edges']))
            self.assertEqual(got['utility'],sum(weights[a] for a in chosen))
            self.assertEqual(got['utility'],row['oracle'])
            for part in got['components']:
                if part['method']!='bipartite_flow':continue
                self.assertEqual(sum(weights[a] for a in part['cover']),part['flow'])
                self.assertEqual(part['flow'],part['cut_capacity'])

    def test_conflicts_identical_and_targets_recomputed(self):
        h=self.r['H5']
        for row in h['fixtures']:
            for key in ('edges','staged'):self.assertEqual(row['pairwise'][key],row['indexed'][key])
            self.assertEqual(row['bounded_oracle'],row['bounded_indexed'])
        s=h['sparse'][-1];self.assertAlmostEqual(s['saving'],1-s['indexed_checks']/s['baseline_checks'])
        self.assertGreaterEqual(s['saving'],.95);self.assertEqual(h['dense']['saving'],0)
        a=self.r['H1'];criterion=(a['correct_retention']>=.98 and a['matched']['proposed']['wrong']<=.8*a['matched']['baseline']['wrong'] and a['matched']['proposed']['wrong']<a['matched']['baseline']['wrong'])
        self.assertEqual(a['primary_target_met'],criterion)

    def test_additive_idempotent_section_insertion(self):
        old='old\n'+ANCHOR+'\nprior ending\n';once=replace_after_anchor(old,'new evidence')
        self.assertEqual(replace_after_anchor(once,'new evidence'),once)
        self.assertTrue(once.startswith('old\n'+ANCHOR));self.assertTrue(once.endswith('prior ending\n'))
        self.assertEqual(once.count(START),1);self.assertEqual(once.count(END),1)
        with self.assertRaises(ValueError):replace_after_anchor('no anchor','new')

    def test_generated_report_retains_limits_and_negative_controls(self):
        text=render(self.r)
        for phrase in ('not a fresh holdout','Fresh service calls: 0','incorrect admission','not superiority over every heuristic','No sources are actually deleted','primary error-reduction target is **not met**'):
            self.assertIn(phrase,text)
        self.assertEqual(text.count('![H'),5)


if __name__=='__main__':unittest.main()
