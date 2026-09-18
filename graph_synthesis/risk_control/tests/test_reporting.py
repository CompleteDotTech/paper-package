"""Integration controls for fixed evidence, gold separation, and additive reporting."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from graph_synthesis.risk_control import report
from graph_synthesis.risk_control.run import HERE, ROOT, SOURCE_HASHES, INPUT, read, sha
from graph_synthesis.risk_control.methods import fit_router, fit_gate, route, threshold_gate, qualifier_veto
from graph_synthesis.adaptive.run import load
from graph_synthesis.adaptive.methods import safe_targeted


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=read(HERE/'results.json')
    def test_input_hashes(self):
        for name,value in SOURCE_HASHES.items():
            with self.subTest(name=name):self.assertEqual(sha(INPUT/name),value)
    def test_frozen_protocol(self):self.assertEqual(sha(HERE/'PROTOCOL.md'),self.r['protocol_sha256'])
    def test_outcomes_not_redefined_as_success(self):
        self.assertEqual([self.r[f'H{i}']['primary_target_met'] for i in range(1,6)],[False,False,False,False,True])
        self.assertTrue(self.r['H4']['algorithm_target_met'])
    def test_report_preserves_boundaries(self):
        text=report.render(self.r)
        for phrase in ('Fresh service calls in this extension: 0','not independent preregistration','not measured human-review trials','false','256','77.27%'):
            with self.subTest(phrase=phrase):self.assertIn(phrase,text)
    def test_render_deterministic(self):self.assertEqual(report.render(self.r),report.render(copy.deepcopy(self.r)))
    def test_report_matches_saved(self):self.assertEqual(report.render(self.r),(HERE/'RESULTS.md').read_text(encoding='utf-8'))
    def test_marker_replacement_idempotent(self):
        old='prior\n'+report.ANCHOR+'\n\nhistorical\n'
        once=report.replace_after_anchor(old,'new evidence')
        self.assertEqual(once,report.replace_after_anchor(once,'new evidence'));self.assertIn('historical\n',once)
        self.assertEqual(once.count(report.START),1)
    def test_missing_or_duplicate_anchor_rejected(self):
        for text in ('missing',report.ANCHOR*2):
            with self.assertRaises(ValueError):report.replace_after_anchor(text,'new')
    def test_all_local_links_exist(self):
        for link in re.findall(r'\]\(([^)]+)\)',report.render(self.r)):
            if '://' not in link and not link.startswith('#'):
                with self.subTest(link=link):self.assertTrue((HERE/link).exists())
    def test_five_figure_pairs(self):
        for ext in ('svg','png'):self.assertEqual(len(list((HERE/'figures').glob('*.'+ext))),5)
    def test_report_update_idempotent(self):
        files=[ROOT/'manuscript/paper-current.md',ROOT/'CURRENT_RESULTS.md'];before=[p.read_bytes() for p in files]
        report.update_paper(self.r);self.assertEqual(before,[p.read_bytes() for p in files])
    def test_prior_generators_preserved(self):
        from graph_synthesis.adaptive.report import update_paper as adaptive_update
        from graph_synthesis.followup.report import update_paper as followup_update
        files=[ROOT/'manuscript/paper-current.md',ROOT/'CURRENT_RESULTS.md'];before=[p.read_bytes() for p in files]
        adaptive_update(read(ROOT/'graph_synthesis/adaptive/results.json'))
        followup_update(read(ROOT/'graph_synthesis/followup/results.json'))
        self.assertEqual(before,[p.read_bytes() for p in files])
    def test_current_source_has_new_section(self):
        text=(ROOT/'manuscript/paper-current.md').read_text(encoding='utf-8')
        self.assertEqual(text.count(report.START),1);self.assertIn('../graph_synthesis/risk_control/figures/05_forest_capacity.png',text)
    def test_paths_portable(self):
        self.assertTrue(all('\\' not in key for key in self.r['source_hashes']))
    def test_classification_and_cost_accounting(self):
        predictions=read(HERE/'predictions.json');rows=[r for r in predictions if r['split']=='test']
        for name,x in self.r['observed'].items():
            with self.subTest(name=name):
                self.assertEqual(x['accepted'],x['correct_edges']+x['wrong_edges'])
                self.assertEqual(x['input_tokens'],sum(r['arms'][name]['input_tokens'] for r in rows))
                self.assertEqual(x['required_calls'],sum(len(r['arms'][name]['sites']) for r in rows))
    def test_fit_ids_and_groups_disjoint(self):
        rows=read(HERE/'predictions.json');test=[r for r in rows if r['split']=='test']
        for key in ('H1','H2'):
            fit=self.r[key]['fit'];self.assertFalse(set(fit['fit_ids'])&{r['id'] for r in test});self.assertFalse(set(fit['fit_groups'])&{r['group'] for r in test})


class IsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows,cls.panels,_=load()
    def test_gold_changes_do_not_change_execution(self):
        fit=read(HERE/'results.json')['H1']['fit']
        for row in self.rows[:8]:
            calls=copy.deepcopy(self.panels[row['id']]);expected=route(calls,fit);checks=qualifier_veto(calls)
            calls['gold']='intentionally wrong gold label'
            self.assertEqual(route(calls,fit),expected);self.assertEqual(qualifier_veto(calls),checks)
    def test_fit_permutation_and_nonmutation(self):
        dev=copy.deepcopy([r for r in self.rows if r['split']=='development'])
        old=copy.deepcopy(dev);a=fit_router(dev,self.panels,split='development');b=fit_router(dev[::-1],self.panels,split='development')
        self.assertEqual(a,b);self.assertEqual(dev,old)
    def test_gate_nonmutation_and_permutation(self):
        dev=copy.deepcopy([r for r in self.rows if r['split']=='development'])
        for r in dev:r['arms']['safe_targeted']=safe_targeted(self.panels[r['id']])
        old=copy.deepcopy(dev);a=fit_gate(dev,split='development');b=fit_gate(dev[::-1],split='development')
        self.assertEqual(a,b);self.assertEqual(dev,old)


if __name__=='__main__':unittest.main()
