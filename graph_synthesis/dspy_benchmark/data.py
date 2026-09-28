"""Deterministic benchmark splits from the original frozen experiment plans."""
from dataclasses import asdict
from pathlib import Path
from collections import Counter
from graph_synthesis.dspy_jev_optimizer.core import Example, JevConfig, digest, read_json, fingerprints, disjoint

ROOT = Path(__file__).resolve().parents[2]
PLAN = 'reproduction/results/jev/run-20260918/plan.json'
MULTICALL = 'experiments/jev-multicall-20260918/plan.json'
CHALLENGE = 'experiments/falsification/challenge.json'
SEEDS = [11, 23, 37, 53, 71]
OBJECTIVES = ['accuracy', 'composite']


def state(task, row):
    if task == 'relation_support':
        return {'claim': row['claim'], 'evidence': row['evidence']}
    result = {k: row[k] for k in ('record_1', 'record_2')}
    if row.get('context'):
        result['context'] = row['context']
    return result


def identities(task, row):
    return {row['group']} if task == 'relation_support' else set(row['identity_groups'])


def example(task, row):
    group = row.get('group') if task == 'relation_support' else digest(sorted(identities(task, row)))
    return Example(row['id'], state(task, row), row['gold_label'], group)


def load_task(task):
    plan = read_json(ROOT / PLAN)
    source = plan['tasks'][task]
    # Stratification uses development labels only; the partition never changes between seeds.
    train, validation = [], []
    for label in sorted({r['gold_label'] for r in source['development']}):
        rows = sorted([r for r in source['development'] if r['gold_label'] == label],
                      key=lambda r: digest(['dspy-development-v1', r['id']]))
        train.extend(rows[:len(rows)//2])
        validation.extend(rows[len(rows)//2:])
    raw = {'train': train, 'validation': validation,
           'calibration': source['calibration'], 'test': source['evaluation'],
           'demonstrations': source['demonstrations']}
    # Pair hashes alone cannot detect a reused entity; check every constituent identity.
    pools = {s: set().union(*(identities(task, r) for r in rows)) for s, rows in raw.items()}
    for i, a in enumerate(pools):
        for b in list(pools)[i+1:]:
            if pools[a] & pools[b]:
                raise ValueError('Source/entity leakage: '+a+' / '+b)
    splits = {s: [example(task, r) for r in rows] for s, rows in raw.items()}
    for i, a in enumerate(splits):
        for b in list(splits)[i+1:]:
            disjoint(fingerprints(splits[a]), fingerprints(splits[b]))
    arm = 'evidence_contract' if task == 'relation_support' else 'identity_contract'
    question = next(iter(plan['question_specs'][task][arm].values()))
    config = JevConfig(task, question['instructions'], question['criteria'])
    return config, splits, plan['question_specs'][task], source


def panels(task):
    """Return panel definitions; they are never supplied to optimizer feedback."""
    config, splits, _, source = load_task(task)
    fixtures = [Example(r['id'], state(task, r), r['gold_label'], r.get('group', r['id']))
                for r in source['fixtures']]
    result = {'test': splits['test'], 'fixtures': fixtures}
    if task == 'relation_support':
        result['semantic_challenge'] = [Example(r['id'], r['state'], r['gold'], r['pair'])
                                       for r in read_json(ROOT / CHALLENGE)]
        mc = read_json(ROOT / MULTICALL)['rows']
        for split in ('development', 'test'):
            result['multicall_'+split] = [example(task, r) for r in mc if r['split'] == split]
    return result


def inventory():
    output = {}
    for task in ('relation_support', 'entity_resolution'):
        config, splits, specs, source = load_task(task)
        output[task] = {'labels': list(config.criteria), 'legacy_arms': list(specs),
                        'splits': {s: {'n':len(rows), 'labels':dict(Counter(r.label for r in rows)),
                        'sha256':digest([asdict(r) for r in rows])} for s, rows in splits.items()},
                        'panels': {s: {'n':len(rows), 'scorable':sum(r.label in config.criteria for r in rows)}
                                   for s, rows in panels(task).items()}}
    return output
