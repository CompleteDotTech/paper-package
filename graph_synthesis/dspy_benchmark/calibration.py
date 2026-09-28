"""Post-hoc calibration. Fit on calibration labels, never on test labels."""
import math
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from graph_synthesis.dspy_jev_optimizer.core import metrics, digest


def matrix(predictions, labels):
    return np.asarray([[r['probabilities'][k] for k in labels] for r in predictions], dtype=float)


def softmax(values):
    values = values - values.max(axis=1, keepdims=True)
    out = np.exp(values)
    return out / out.sum(axis=1, keepdims=True)


def fit(predictions, labels, method='temperature'):
    if not predictions or method not in ('raw','temperature','bias_temperature'):
        raise ValueError('Invalid calibration request')
    p = matrix(predictions, labels)
    if not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(1), 1, atol=1e-6):
        raise ValueError('Invalid calibration probabilities')
    y = np.asarray([list(labels).index(r['gold']) for r in predictions])
    logp = np.log(np.clip(p, 1e-15, 1))
    def loss(log_t, bias):
        q = softmax(logp / np.exp(log_t) + bias)
        return float(-np.log(np.clip(q[np.arange(len(y)), y], 1e-15, 1)).mean())
    log_t, bias = 0., np.zeros(len(labels))
    if method == 'temperature':
        fitted = minimize_scalar(lambda t: loss(t, bias), bounds=(-2.3, 2.3), method='bounded')
        if not fitted.success:
            raise RuntimeError('Temperature fit failed')
        log_t = float(fitted.x)
    elif method == 'bias_temperature':
        # Fixed shrinkage; never choose its strength using test outcomes.
        def objective(x):
            b = x[1:] - np.mean(x[1:])
            return loss(x[0], b) + .01 * float(np.mean(b*b))
        fitted = minimize(objective, np.zeros(len(labels)+1), method='L-BFGS-B',
                          bounds=[(-2.3,2.3)]+[(-3.,3.)]*len(labels))
        if not fitted.success:
            raise RuntimeError('Bias/temperature fit failed')
        log_t, bias = float(fitted.x[0]), fitted.x[1:]-np.mean(fitted.x[1:])
    return {'method':method, 'temperature':math.exp(log_t), 'bias':bias.tolist(),
            'labels':list(labels), 'n_calibration':len(predictions),
            'calibration_ids_sha256':digest([r['id'] for r in predictions])}


def apply(predictions, fitted):
    labels = fitted['labels']
    if fitted['method'] == 'raw':
        return [dict(r) for r in predictions]
    p = matrix(predictions, labels)
    q = softmax(np.log(np.clip(p,1e-15,1))/fitted['temperature']+np.asarray(fitted['bias']))
    # Temperature preserves selected labels, including provider tie-breaking.
    return [{**r, 'choice':r['choice'] if fitted['method']=='temperature' else labels[int(np.argmax(q[i]))],
             'probabilities':dict(zip(labels, map(float,q[i])))} for i,r in enumerate(predictions)]


def evaluation(predictions, labels):
    valid = [r for r in predictions if r['gold'] in labels]
    result = metrics(valid, labels)
    result['unscorable_count'] = len(predictions)-len(valid)
    result['selective'] = []
    for threshold in (.5,.7,.9,.95,.99):
        selected = [r for r in valid if r['probabilities'][r['choice']] >= threshold]
        result['selective'].append({'threshold':threshold, 'accepted':len(selected),
            'coverage':len(selected)/len(valid), 'errors':sum(r['choice']!=r['gold'] for r in selected),
            'risk':sum(r['choice']!=r['gold'] for r in selected)/len(selected) if selected else None})
    if 'same' in labels:
        result['false_merges'] = sum(r['choice']=='same' and r['gold']!='same' for r in valid)
        result['missed_merges'] = sum(r['choice']!='same' and r['gold']=='same' for r in valid)
    else:
        edge_labels = {'SUPPORTS','REFUTES'}
        tp = sum(r['choice'] in edge_labels and r['gold']==r['choice'] for r in valid)
        fp = sum(r['choice'] in edge_labels and r['gold']!=r['choice'] for r in valid)
        fn = sum(r['gold'] in edge_labels and r['gold']!=r['choice'] for r in valid)
        result.update(correct_edges=tp, wrong_edges=fp, missed_edges=fn,
                      edge_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)
    return result


def paired_interval(baseline, candidate, labels, metric, seed=812, repeats=1000):
    if [r['id'] for r in baseline] != [r['id'] for r in candidate]:
        raise ValueError('Unpaired examples')
    groups = {}
    for i,r in enumerate(baseline):
        groups.setdefault(r.get('group_id',r['id']), []).append(i)
    keys = list(groups)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repeats):
        indices = [i for g in rng.choice(len(keys),len(keys)) for i in groups[keys[g]]]
        a, b = ([rows[i] for i in indices] for rows in (baseline,candidate))
        values.append(metrics(b,labels)[metric]-metrics(a,labels)[metric])
    return {'delta':metrics(candidate,labels)[metric]-metrics(baseline,labels)[metric],
            'low':float(np.quantile(values,.025)), 'high':float(np.quantile(values,.975)),
            'resampling_unit':'provided group_id', 'replicates':repeats, 'multiplicity_adjusted':False}
