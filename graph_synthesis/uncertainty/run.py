"""Execute five frozen controlled benchmarks; retain negative outcomes and controls."""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
from itertools import combinations, product
import json
from pathlib import Path
import random
from statistics import mean
from .methods import (credal_bounds, frechet_bounds, grounded, holds, independent_probability,
                      query_loss, retraction_plan, review_plan, skeptical_repair, support_prune,
                      world_table)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 20260922
BASELINE = 'a62a3257645d8e35cd4e45be53bfa9511d27724b'
PROTOCOL_COMMIT = '383bab6f559c7f14525ddcef2275f3a816c9caa3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write(path, value):
    Path(path).write_text(json.dumps(clean(value), sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def random_proofs(rng, atoms, maximum=4):
    return [sorted(rng.sample(atoms, rng.randint(1, min(3, len(atoms)))))
            for _ in range(rng.randint(1, maximum))]


def solve_rational(matrix, rhs):
    """Independent exact Gaussian elimination for tiny vertex-oracle systems."""
    n = len(rhs)
    rows = [[Fraction(x) for x in row]+[Fraction(y)] for row, y in zip(matrix, rhs)]
    for col in range(n):
        pivot = next((i for i in range(col, n) if rows[i][col]), None)
        if pivot is None:
            return None
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]; rows[col] = [x/scale for x in rows[col]]
        for i in range(n):
            if i != col:
                factor = rows[i][col]
                rows[i] = [x-factor*y for x, y in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


def rational_lineage_oracle(proofs, p):
    atoms = sorted(p); size = 1 << len(atoms)
    matrix = [[1]*size]+[[int(mask & (1 << i) != 0) for mask in range(size)] for i in range(len(atoms))]
    rhs = [Fraction(1)]+[Fraction(p[a]) for a in atoms]
    value = [int(any(all(mask & (1 << atoms.index(a)) for a in term) for term in proofs)) for mask in range(size)]
    extrema = []
    for columns in combinations(range(size), len(rhs)):
        solution = solve_rational([[row[c] for c in columns] for row in matrix], rhs)
        if solution is not None and all(x >= 0 for x in solution):
            extrema.append(sum(x*value[c] for c, x in zip(columns, solution)))
    if not extrema:
        raise AssertionError('No feasible rational vertex')
    return float(min(extrema)), float(max(extrema))


def h1():
    rng = random.Random(SEED+1); cases = []; failures = false_admissions = invariance = 0
    for i in range(128):
        n = rng.randint(2, 6); atoms = [f'a{j}' for j in range(n)]
        weights = [rng.randrange(0, 7) if rng.random() < 0.55 else 0 for _ in range(1 << n)]
        weights[0] += 1; weights[-1] += 10 if i % 3 else 150
        total = sum(weights)
        p = {a: sum(w for mask, w in enumerate(weights) if mask & (1 << j))/total for j, a in enumerate(atoms)}
        proofs = random_proofs(rng, atoms)
        actual = sum(w for mask, w in enumerate(weights) if any(all(mask & (1 << atoms.index(a)) for a in term) for term in proofs))/total
        result = credal_bounds(proofs, p); coarse = frechet_bounds(proofs, p)
        independent = independent_probability(proofs, p)
        failures += not result['lower']-1e-8 <= actual <= result['upper']+1e-8
        false_admissions += result['lower'] >= 0.95 and actual < 0.95-1e-8
        duplicate = credal_bounds(list(reversed(proofs))*5, dict(reversed(list(p.items()))))
        invariance += abs(duplicate['lower']-result['lower']) > 1e-10 or abs(duplicate['upper']-result['upper']) > 1e-10
        cases.append({'id': i, 'probabilities': p, 'joint_integer_masses': weights, 'proofs': proofs,
                      'actual': actual, 'independent': independent, 'proposed': result, 'analytic': coarse})
    oracle_cases = []; oracle_failures = 0
    for i in range(16):
        atoms = [f'a{j}' for j in range(2+i % 2)]
        p = {a: Fraction(rng.randint(1, 9), 10) for a in atoms}
        proofs = random_proofs(rng, atoms)
        lower, upper = rational_lineage_oracle(proofs, p)
        result = credal_bounds(proofs, {a: float(x) for a, x in p.items()})
        oracle_failures += (abs(result.get('raw_lower', result['lower'])-lower) > 1e-8 or
                            abs(result.get('raw_upper', result['upper'])-upper) > 1e-8)
        oracle_cases.append({'proofs': proofs, 'probabilities': {a: str(x) for a, x in p.items()},
                             'oracle': [lower, upper], 'proposed': result})
    shared = credal_bounds([['a'], ['b']], {'a': 0.8, 'b': 0.8})
    singleton = credal_bounds([['a']], {'a': 0.99})
    overcap = credal_bounds([[f'a{i}'] for i in range(9)], {f'a{i}': 0.8 for i in range(9)})
    bad_marginal = credal_bounds([['a']], {'a': 0.99})
    return {'cases': cases, 'oracle_cases': oracle_cases, 'containment_failures': failures,
            'oracle_failures': oracle_failures, 'invariance_failures': invariance, 'false_admissions': false_admissions,
            'independent_false_admissions': sum(c['independent'] >= 0.95 and c['actual'] < 0.95 for c in cases),
            'mean_analytic_width': mean(c['analytic']['upper']-c['analytic']['lower'] for c in cases),
            'mean_credal_width': mean(c['proposed']['upper']-c['proposed']['lower'] for c in cases),
            'controls': {'shared_source': {'independent': 0.96, 'actual': 0.8, 'proposed': shared},
                         'singleton': singleton, 'over_cap': overcap,
                         'bad_marginal': {'supplied': 0.99, 'actual': 0.5, 'proposed': bad_marginal}},
            'primary_target_met': not (failures or oracle_failures or invariance or false_admissions)
                                  and shared['lower'] < 0.95 and singleton['lower'] >= 0.95}


def independent_sets_oracle(weights, edges):
    nodes = sorted(weights); best = -1; optima = []
    for mask in range(1 << len(nodes)):
        chosen = {node for i, node in enumerate(nodes) if mask & (1 << i)}
        if any(a in chosen and b in chosen for a, b in edges):
            continue
        value = sum(weights[a] for a in chosen)
        if value > best:
            best = value; optima = [chosen]
        elif value == best:
            optima.append(chosen)
    return best, optima


def h2():
    rng = random.Random(SEED+2); cases = []; failures = invariance = 0
    for i in range(128):
        nodes = [f'v{j:02}' for j in range(rng.randint(2, 12))]
        weights = {a: 1 if i % 4 == 0 else rng.randint(0, 9) for a in nodes}
        density = rng.choice([0.1, 0.3, 0.6, 0.9])
        edges = [list(pair) for pair in combinations(nodes, 2) if rng.random() < density]
        result = skeptical_repair(weights, edges)
        utility, optima = independent_sets_oracle(weights, edges)
        necessary = sorted(set.intersection(*optima)); possible = sorted(set.union(*optima))
        invalid = result['utility'] != utility or result['necessary'] != necessary or result['possible'] != possible
        for node, witness in result['witnesses'].items():
            invalid |= (set(witness['include']) not in optima or node not in witness['include'] or
                        set(witness['exclude']) not in optima or node in witness['exclude'])
        failures += bool(invalid)
        for _ in range(4):
            order = nodes[:]; rng.shuffle(order); permuted = edges[:]; rng.shuffle(permuted)
            invariance += skeptical_repair({a: weights[a] for a in order}, permuted) != result
        cases.append({'id': i, 'weights': weights, 'edges': edges, 'proposed': result,
                      'oracle_utility': utility, 'oracle_necessary': necessary, 'oracle_possible': possible,
                      'optimal_repairs': len(optima), 'backbone_utility': sum(weights[a] for a in necessary)})
    tie = skeptical_repair({'a': 5, 'b': 5, 'certain': 2}, [('a', 'b')])
    misleading = skeptical_repair({'false': 9, 'true': 8}, [('false', 'true')])
    overcap = skeptical_repair({f'v{i}': 1 for i in range(32)}, [(f'v{i}', f'v{(i+1)%32}') for i in range(32)])
    unique_loss = sum(c['optimal_repairs'] == 1 and c['backbone_utility'] != c['oracle_utility'] for c in cases)
    return {'cases': cases, 'oracle_failures': failures, 'invariance_failures': invariance,
            'unique_optimum_losses': unique_loss, 'ambiguous_cases': sum(c['optimal_repairs'] > 1 for c in cases),
            'selected_assertions': sum(len(c['proposed']['selected']) for c in cases),
            'necessary_assertions': sum(len(c['proposed']['necessary']) for c in cases),
            'controls': {'tie': tie, 'false_priority': misleading, 'over_cap': overcap},
            'primary_target_met': not (failures or invariance or unique_loss) and tie['necessary'] == ['certain']}


def direct_brier(queries, assumed, reviewed, actual=None, noise=0.0):
    """Independent oracle via explicit squared errors, not conditional variance."""
    atoms, worlds, mass = world_table(assumed)
    reviewed = sorted(reviewed)
    _, _, actual_mass = world_table(actual if actual is not None else assumed)
    posterior = {}
    for obs in product((False, True), repeat=len(reviewed)):
        matching = [i for i, w in enumerate(worlds) if all((a in w) == b for a, b in zip(reviewed, obs))]
        denominator = sum(mass[i] for i in matching)
        posterior[obs] = [sum(mass[i]*any(all(a in worlds[i] for a in t) for t in q) for i in matching)/denominator
                          if denominator else 0.5 for q in queries]
    total = 0.0
    for world, m in zip(worlds, actual_mass):
        truth = [any(all(a in world for a in term) for term in q) for q in queries]
        for obs, predictions in posterior.items():
            likelihood = 1.0
            for a, b in zip(reviewed, obs):
                likelihood *= (1-noise) if ((a in world) == b) else noise
            total += m*likelihood*sum((float(y)-p)**2 for y, p in zip(truth, predictions))
    return total


def bootstrap_difference(values):
    rng = random.Random(SEED+30)
    draws = sorted(mean(rng.choices(values, k=len(values))) for _ in range(2000))
    return [draws[49], draws[1949]]


def h3():
    rng = random.Random(SEED+3); cases = []; failures = 0
    for i in range(64):
        atoms = [f'a{j}' for j in range(rng.randint(6, 8))]
        p = {a: rng.choice([0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95]) for a in atoms}
        queries = [random_proofs(rng, atoms, 3) for _ in range(3)]
        budgets = []
        for budget in (1, 2):
            proposed = review_plan(queries, p, budget)
            risk = sorted(p, key=lambda a: (p[a], a))[:budget]
            entropy = sorted(p, key=lambda a: (-p[a]*(1-p[a]), a))[:budget]
            oracle_scores = [direct_brier(queries, p, subset) for subset in combinations(atoms, budget)]
            proposed_direct = direct_brier(queries, p, proposed['reviewed'])
            failures += abs(proposed_direct-proposed['loss']) > 1e-10 or proposed_direct-min(oracle_scores) > 1e-10
            budgets.append({'budget': budget, 'proposed': proposed, 'oracle_minimum': min(oracle_scores),
                            'risk': {'reviewed': risk, 'loss': direct_brier(queries, p, risk)},
                            'entropy': {'reviewed': entropy, 'loss': direct_brier(queries, p, entropy)},
                            'noisy_proposed_loss': direct_brier(queries, p, proposed['reviewed'], noise=0.1),
                            'noisy_risk_loss': direct_brier(queries, p, risk, noise=0.1)})
        cases.append({'id': i, 'probabilities': p, 'queries': queries,
                      'no_review_loss': direct_brier(queries, p, []), 'budgets': budgets})
    proposed_sum = sum(c['budgets'][1]['proposed']['loss'] for c in cases)
    risk_sum = sum(c['budgets'][1]['risk']['loss'] for c in cases)
    improvement = 1-proposed_sum/risk_sum if risk_sum else 0.0
    assumed = {'a': 0.9, 'b': 0.05}; actual = {'a': 0.9, 'b': 0.5}
    queries = [[['a']], [['a']], [['b']]]
    chosen = review_plan(queries, assumed, 1)
    control = {'assumed': assumed, 'actual': actual, 'queries': queries, 'proposed': chosen,
               'actual_proposed_loss': direct_brier(queries, assumed, chosen['reviewed'], actual),
               'risk_reviewed': ['b'], 'actual_risk_loss': direct_brier(queries, assumed, ['b'], actual)}
    return {'cases': cases, 'oracle_failures': failures, 'budget2_proposed_total_loss': proposed_sum,
            'budget2_risk_total_loss': risk_sum, 'relative_loss_reduction': improvement,
            'paired_fixture_difference_95': bootstrap_difference([c['budgets'][1]['proposed']['loss']-c['budgets'][1]['risk']['loss'] for c in cases]),
            'controls': {'misspecified_prior': control, 'noise_rate': 0.1, 'noise_model': 'unmodeled independent reviewer bit flips'},
            'primary_target_met': failures == 0 and improvement >= 0.20}


def retraction_oracle(facts, target, protected, costs):
    atoms = sorted(costs); best = None; best_removed = None
    for mask in range(1 << len(atoms)):
        removed = {a for j, a in enumerate(atoms) if mask & (1 << j)}
        truth = {f: any(not any(a in removed for a in term) for term in proofs) for f, proofs in facts.items()}
        if truth[target] or any(not truth[f] for f in protected):
            continue
        collateral = sum(not value for f, value in truth.items() if f != target and f not in protected)
        objective = (collateral, sum(costs[a] for a in removed), len(removed), tuple(sorted(removed)))
        if best is None or objective < best:
            best, best_removed = objective, sorted(removed)
    return best, best_removed


def evaluate_removal(facts, target, protected, costs, removed):
    if removed is None:
        return {'feasible': False}
    active = set(costs)-set(removed)
    feasible = not holds(facts[target], active) and all(holds(facts[f], active) for f in protected)
    return {'feasible': feasible, 'removed': sorted(removed),
            'collateral': sum(not holds(proofs, active) for f, proofs in facts.items() if f != target and f not in protected),
            'cost': sum(costs[a] for a in removed)}


def h4():
    rng = random.Random(SEED+4); cases = []; failures = protected_losses = invariance = 0
    for i in range(128):
        atoms = [f'a{j}' for j in range(rng.randint(4, 10))]
        facts = {f'q{j}': random_proofs(rng, atoms, 3) for j in range(6)}
        costs = {a: rng.randint(1, 5) for a in atoms}; protected = ['q1']; target = 'q0'
        result = retraction_plan(facts, target, protected, costs)
        objective, oracle_removed = retraction_oracle(facts, target, protected, costs)
        failures += result['removed'] != oracle_removed
        proposed = evaluate_removal(facts, target, protected, costs, result['removed'])
        protected_losses += result['removed'] is not None and not proposed['feasible']
        union = {a for term in facts[target] for a in term}
        greedy = set()
        while any(not set(term) & greedy for term in facts[target]):
            candidates = {a for term in facts[target] if not set(term) & greedy for a in term}
            greedy.add(min(candidates, key=lambda a: (costs[a], a)))
        shuffled = list(facts); rng.shuffle(shuffled)
        invariance += retraction_plan({f: list(reversed(facts[f])) for f in shuffled}, target, protected,
                                     dict(reversed(list(costs.items())))) != result
        cases.append({'id': i, 'facts': facts, 'costs': costs, 'target': target, 'protected': protected,
                      'proposed': result, 'oracle_objective': objective, 'oracle_removed': oracle_removed,
                      'union': evaluate_removal(facts, target, protected, costs, union),
                      'greedy': evaluate_removal(facts, target, protected, costs, greedy)})
    matched = [c for c in cases if c['proposed']['removed'] is not None and c['union']['feasible']]
    union_sum = sum(c['union']['collateral'] for c in matched)
    proposed_sum = sum(c['proposed']['collateral'] for c in matched)
    improvement = 1-proposed_sum/union_sum if union_sum else 0.0
    incomplete = retraction_plan({'target': [['a']], 'other': [['b']]}, 'target', [], {'a': 1, 'b': 1})
    incomplete_still_true = holds([['a'], ['b']], {'a', 'b'}-set(incomplete['removed']))
    return {'cases': cases, 'oracle_failures': failures, 'protected_losses': protected_losses,
            'invariance_failures': invariance, 'matched_feasible_cases': len(matched),
            'union_collateral': union_sum, 'proposed_collateral': proposed_sum, 'relative_collateral_reduction': improvement,
            'proposed_feasible_cases': sum(c['proposed']['removed'] is not None for c in cases),
            'union_feasible_cases': sum(c['union']['feasible'] for c in cases),
            'greedy_feasible_cases': sum(c['greedy']['feasible'] for c in cases),
            'controls': {'impossible': retraction_plan({'t': [['a']], 'p': [['a']]}, 't', ['p'], {'a': 1}),
                         'omitted_proof': {'plan': incomplete, 'target_still_true_under_complete_lineage': incomplete_still_true},
                         'wrong_target': {'plan': incomplete, 'all_supplied_atoms_actually_true': True},
                         'over_cap': retraction_plan({'t': [['a0']]}, 't', [], {f'a{i}': 1 for i in range(15)})},
            'primary_target_met': not (failures or protected_losses or invariance) and improvement >= 0.25}


def finite_model_oracle(bases, rules):
    atoms = sorted(set(bases) | {head for head, _ in rules} | {a for _, body in rules for a in body})
    intersection = set(atoms)
    for bits in product((False, True), repeat=len(atoms)):
        interpretation = dict(zip(atoms, bits))
        if not all(interpretation[a] for a in bases):
            continue
        if all(interpretation[head] or not all(interpretation[a] for a in body) for head, body in rules):
            intersection &= {a for a in atoms if interpretation[a]}
    return sorted(intersection)


def h5():
    rng = random.Random(SEED+5); cases = []; failures = invariance = 0; phantom = 0
    for i in range(96):
        atoms = [f'a{j}' for j in range(rng.randint(4, 8))]
        rules = [(rng.choice(atoms), sorted(rng.sample(atoms, rng.randint(1, min(3, len(atoms)))))) for _ in range(2*len(atoms))]
        if i % 2 == 0:
            rules.extend((atoms[(j+1)%3], [atoms[j]]) for j in range(3))
        previous = []; snapshots = []
        for step in range(12):
            bases = [a for a in atoms if rng.random() < 0.3]
            result = grounded(bases, rules); oracle = finite_model_oracle(bases, rules)
            failures += result['active'] != oracle
            expanded = grounded(set(previous) | set(bases), rules)['active']
            naive = support_prune(expanded, bases, rules)
            extra = sorted(set(naive)-set(oracle)); phantom += len(extra)
            invariance += grounded(list(reversed(bases)), list(reversed(rules))*2) != result
            snapshots.append({'step': step, 'bases': bases, 'proposed': result, 'oracle': oracle, 'naive': naive, 'phantom': extra})
            previous = result['active']
        cases.append({'id': i, 'rules': rules, 'snapshots': snapshots})
    cycles = []
    for n in (2, 4, 8, 16, 32, 64):
        rules = [(f'v{(i+1)%n}', [f'v{i}']) for i in range(n)]+[('v0', ['seed'])]
        previous = grounded(['seed'], rules)['active']
        after = grounded([], rules)
        naive = support_prune(previous, [], rules)
        alternative = grounded(['backup'], rules+[('v0', ['backup'])])
        cycles.append({'n': n, 'proposed_after_withdrawal': after, 'naive_after_withdrawal': naive,
                       'alternative_support': alternative})
    controls_pass = all(not c['proposed_after_withdrawal']['active'] and len(c['alternative_support']['active']) == c['n']+1 for c in cycles)
    return {'cases': cases, 'snapshot_evaluations': 1152, 'oracle_failures': failures,
            'invariance_failures': invariance, 'naive_phantom_occurrences': phantom,
            'controls': {'cycles': cycles, 'unseeded_self_support': grounded([], [('a', ['a'])]),
                         'false_base': {'actual_false': ['a', 'b'], 'proposed': grounded(['a'], [('b', ['a'])])}},
            'primary_target_met': not (failures or invariance) and controls_pass and phantom > 0}


def execute():
    result = {'study': 'Five uncertainty and grounding improvements', 'date': '2026-09-18', 'seed': SEED,
              'baseline_commit': BASELINE, 'protocol_commit': PROTOCOL_COMMIT, 'fresh_service_calls': 0,
              'new_scientific_documents': 0, 'evidence_class': 'controlled fixtures only; no semantic validation',
              'protocol_sha256': sha(HERE/'PROTOCOL.md') if (HERE/'PROTOCOL.md').exists() else None,
              'source_sha256': {p.name: sha(p) for p in sorted(HERE.glob('*.py'))}}
    for i, function in enumerate((h1, h2, h3, h4, h5), 1):
        result[f'H{i}'] = function()
        print(f"H{i}: primary target {'met' if result[f'H{i}']['primary_target_met'] else 'NOT met'}", flush=True)
    return clean(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true')
    args = parser.parse_args(); result = execute(); path = HERE/'results.json'
    if args.check:
        if json.loads(path.read_text(encoding='utf-8')) != result:
            raise SystemExit('Deterministic replay differs from committed results')
        print('Exact machine-readable replay verified')
    else:
        write(path, result)
        print(f'Wrote {path}')


if __name__ == '__main__':
    main()
