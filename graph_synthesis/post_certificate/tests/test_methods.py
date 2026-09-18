import unittest

from graph_synthesis.post_certificate.methods import (
    max_sum_elimination, brute_force_optimum, DependencyGraph,
    query_resilience, brute_force_resilience,
    dnf_probability_shannon, dnf_probability_worlds,
    select_interval_minimax, oracle_interval_worst,
)


class EliminationTests(unittest.TestCase):
    def test_pairwise_triangle(self):
        w=[5,4,3]
        scopes=[(0,1),(1,2),(0,2)]
        got=max_sum_elimination(w,scopes)
        self.assertEqual(got.objective,5)
        self.assertEqual(got.selected,(0,))
        self.assertEqual(got.induced_width,2)

    def test_pairwise_matches_bruteforce(self):
        w=[7,5,8,4,9]
        scopes=[(0,1),(1,2),(2,3),(3,4),(0,2)]
        got=max_sum_elimination(w,scopes)
        want,_=brute_force_optimum(w,scopes)
        self.assertEqual(got.objective,want)

    def test_width_control_stages(self):
        n=6
        scopes=[(i,j) for i in range(n) for j in range(i+1,n)]
        self.assertEqual(max_sum_elimination([1]*n,scopes).status,'staged')

    def test_hyperedge_keeps_pair(self):
        got=max_sum_elimination([1,1,1],[(0,1,2)])
        self.assertEqual(got.objective,2)
        self.assertEqual(len(got.selected),2)

    def test_hyperedge_matches_bruteforce(self):
        w=[4,8,3,7,6]
        scopes=[(0,1,2),(1,2,3),(2,3,4)]
        got=max_sum_elimination(w,scopes)
        want,_=brute_force_optimum(w,scopes)
        self.assertEqual(got.objective,want)


class DeltaTests(unittest.TestCase):
    def graph(self):
        return DependencyGraph(3,{
            3:('and',(0,1)),
            4:('or',(1,2)),
            5:('xor',(3,4)),
        })

    def test_transaction_matches_full(self):
        g=self.graph(); prim={0:True,1:True,2:False}; v=g.full_recompute(prim)
        nv,nr,ev=g.transact(v,0,{1:False},expected_revision=0)
        self.assertEqual(nr,1)
        self.assertEqual(nv,g.full_recompute({0:True,1:False,2:False}))
        self.assertLessEqual(ev,3)

    def test_stale_rejected(self):
        g=self.graph(); v=g.full_recompute({0:True,1:True,2:False})
        with self.assertRaises(RuntimeError): g.transact(v,1,{1:False},expected_revision=0)

    def test_malformed_rejected(self):
        g=self.graph(); v=g.full_recompute({0:True,1:True,2:False})
        with self.assertRaises(ValueError): g.transact(v,0,{3:False},expected_revision=0)

    def test_injected_failure_leaves_input_unmodified(self):
        g=self.graph(); v=g.full_recompute({0:True,1:True,2:False}); before=dict(v)
        with self.assertRaises(RuntimeError): g.transact(v,0,{1:False},expected_revision=0,fail_node=3)
        self.assertEqual(v,before)


class ResilienceTests(unittest.TestCase):
    def test_resilience_matches_oracle(self):
        clauses=[(0,1),(1,2),(2,3)]
        costs={0:4,1:3,2:2,3:5}
        got=query_resilience(clauses,costs)
        want,_=brute_force_resilience(clauses,costs)
        self.assertEqual(got['cost'],want)

    def test_disconnected_adds_costs(self):
        clauses=[(0,1),(2,3)]
        costs={0:1,1:5,2:3,3:2}
        got=query_resilience(clauses,costs)
        self.assertEqual(got['cost'],3)

    def test_large_connected_stages(self):
        clauses=[(i,i+1) for i in range(19)]
        costs={i:1 for i in range(20)}
        self.assertEqual(query_resilience(clauses,costs)['status'],'staged')


class ProbabilityTests(unittest.TestCase):
    def test_shannon_matches_worlds(self):
        q=[(0,1),(2,)]
        p={0:.2,1:.7,2:.3}
        self.assertAlmostEqual(dnf_probability_shannon(q,p),dnf_probability_worlds(q,p),places=12)

    def test_minimax_not_worse_than_midpoint(self):
        intervals={0:(.39,.41),1:(.41,.43),2:(.05,.5),3:(.1,.5),4:(.01,.05),5:(.94,.98)}
        queries=[[(a,)] for a in range(6)]
        got=select_interval_minimax(queries,intervals,2)
        self.assertLessEqual(got['minimax_worst'],got['midpoint_worst']+1e-12)
        self.assertAlmostEqual(got['minimax_worst'],oracle_interval_worst(queries,intervals,got['minimax']),places=12)

    def test_point_intervals_reduce_to_point_selection(self):
        intervals={i:(p,p) for i,p in enumerate([.1,.2,.3,.4,.5,.6])}
        queries=[[(a,)] for a in range(6)]
        got=select_interval_minimax(queries,intervals,2)
        self.assertEqual(got['minimax'],got['midpoint'])
        self.assertAlmostEqual(got['minimax_worst'],got['midpoint_worst'],places=12)


if __name__=='__main__': unittest.main()
