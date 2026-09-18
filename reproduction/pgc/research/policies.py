"""Small, auditable policies for controlled E5/E7/E8 experiments.

Only the synthetic generator supplies exact likelihoods/conditional probabilities.
Applying these functions to model confidence does not confer calibration or safety.
"""

from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from math import exp, isfinite, log, prod
from random import Random
from typing import Iterable, Mapping, Sequence


def _probability(value: float) -> float:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Probabilities must be finite and between zero and one")
    return value


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + exp(-value))
    e = exp(value)
    return e / (1 + e)


@dataclass(frozen=True)
class EvidenceScore:
    source_id: str
    group_id: str
    content: str
    log_likelihood_ratio: float


def aggregate_evidence(
    evidence: Sequence[EvidenceScore], prior: float = 0.5, mode: str = "grouped"
) -> dict:
    """Aggregate log scores, retaining contradictions and counting exact copies once.

    ``grouped`` averages distinct passages within a provenance group then adds
    groups. Groups sharing identical content are conservatively joined, so copy
    relabeling cannot manufacture an independent source. The mean is a heuristic
    outside the controlled same-origin experiment, not a general Bayes rule.
    """
    _probability(prior)
    if prior in (0, 1):
        raise ValueError("The prior must be strictly between zero and one")
    if mode not in {"naive", "exact_dedup", "grouped"}:
        raise ValueError("Unknown evidence aggregation mode")
    groups = {item.group_id: item.group_id for item in evidence}

    def root(group):
        while groups[group] != group:
            group = groups[group]
        return group

    unique = {}
    for item in evidence:
        if not item.source_id or not item.group_id or not item.content:
            raise ValueError("Evidence requires a source, group, and content")
        if not isfinite(item.log_likelihood_ratio):
            raise ValueError("Evidence scores must be finite")
        digest = sha256(item.content.encode("utf-8")).hexdigest()
        if digest in unique:
            previous = unique[digest]
            if previous.log_likelihood_ratio != item.log_likelihood_ratio:
                raise ValueError("Identical evidence has conflicting scores")
            left, right = sorted((root(previous.group_id), root(item.group_id)))
            groups[right] = left
        else:
            unique[digest] = item
    by_group = {}
    for item in unique.values():
        by_group.setdefault(root(item.group_id), []).append(item.log_likelihood_ratio)
    if mode == "naive":
        scores = [item.log_likelihood_ratio for item in evidence]
    elif mode == "exact_dedup":
        scores = [item.log_likelihood_ratio for item in unique.values()]
    else:
        scores = [sum(values) / len(values) for values in by_group.values()]
    log_odds = log(prior / (1 - prior)) + sum(scores)
    return {"probability": sigmoid(log_odds), "log_odds": log_odds,
            "unique_items": len(unique), "source_groups": len(by_group)}


def all_partitions(items: Sequence[str]):
    """Enumerate canonical set partitions (Bell-number complexity)."""
    if not items:
        yield ()
        return
    first, *rest = items
    for partition in all_partitions(rest):
        yield ((first,),) + partition
        for index in range(len(partition)):
            yield partition[:index] + ((first,) + partition[index],) + partition[index + 1:]


def identity_pairs(partition: Sequence[Sequence[str]]) -> set[tuple[str, str]]:
    return {tuple(sorted(pair)) for cluster in partition for pair in combinations(cluster, 2)}


def _identity_inputs(nodes, probabilities, cannot_link=(), must_link=()):
    if len(nodes) != len(set(nodes)):
        raise ValueError("Entity IDs must be unique")
    pairs = {tuple(sorted(pair)) for pair in combinations(nodes, 2)}
    supplied = {tuple(sorted(pair)): _probability(p) for pair, p in probabilities.items()}
    if len(supplied) != len(probabilities) or set(supplied) != pairs:
        raise ValueError("Exactly one probability is required for every unordered pair")
    forbidden = {tuple(sorted(pair)) for pair in cannot_link}
    required = {tuple(sorted(pair)) for pair in must_link}
    if not (forbidden | required) <= pairs:
        raise ValueError("Constraints must reference distinct known entities")
    return supplied, forbidden, required


def exact_identity_clustering(
    nodes: Sequence[str], probabilities: Mapping[tuple[str, str], float],
    cannot_link: Iterable[tuple[str, str]] = (),
    must_link: Iterable[tuple[str, str]] = (), max_nodes: int = 8,
) -> dict:
    """Exact constrained correlation clustering, preserving every negative score.

    The objective is a factorized log-likelihood surrogate. No posterior claim
    follows for correlated pair scores. Hard constraints must be justified.
    """
    if len(nodes) > max_nodes or max_nodes > 8:
        raise ValueError("Exact search is limited to eight entities")
    probabilities, forbidden, required = _identity_inputs(
        nodes, probabilities, cannot_link, must_link)
    clipped = {pair: min(1 - 1e-12, max(1e-12, p)) for pair, p in probabilities.items()}
    best, best_score, feasible, searched = None, float("-inf"), 0, 0
    for partition in all_partitions(tuple(sorted(nodes))):
        searched += 1
        positive = identity_pairs(partition)
        if positive & forbidden or not required <= positive:
            continue
        feasible += 1
        score = sum(log(p if pair in positive else 1 - p) for pair, p in clipped.items())
        if score > best_score:
            best, best_score = partition, score
    return {"partition": best, "objective": best_score if best is not None else None,
            "feasible": best is not None, "partitions_searched": searched,
            "feasible_partitions": feasible}


def greedy_identity_clustering(
    nodes: Sequence[str], probabilities: Mapping[tuple[str, str], float],
    reject_conflict: bool = False,
    cannot_link: Iterable[tuple[str, str]] = (), threshold: float = 0.5,
) -> tuple:
    """Union-find control, optionally refusing any negative cross-cluster pair."""
    _probability(threshold)
    probabilities, forbidden, _ = _identity_inputs(nodes, probabilities, cannot_link)
    clusters = [{node} for node in sorted(nodes)]
    for pair, p in sorted(probabilities.items(), key=lambda item: (-item[1], item[0])):
        if p < threshold:
            continue
        left = next(cluster for cluster in clusters if pair[0] in cluster)
        right = next(cluster for cluster in clusters if pair[1] in cluster)
        if left is right:
            continue
        cross = {tuple(sorted((a, b))) for a in left for b in right}
        if reject_conflict and (cross & forbidden or any(probabilities[x] < threshold for x in cross)):
            continue
        clusters.remove(left)
        clusters.remove(right)
        clusters.append(left | right)
    return tuple(sorted(tuple(sorted(cluster)) for cluster in clusters))


def pairwise_metrics(nodes, predicted, truth, cannot_link=()) -> dict:
    """Pairwise clustering scores; F1=1 only if both pair sets are empty."""
    predicted, truth = set(predicted), set(truth)
    universe = {tuple(sorted(pair)) for pair in combinations(nodes, 2)}
    if not predicted <= universe or not truth <= universe:
        raise ValueError("Pairs must reference the declared entities in sorted order")
    tp, fp, fn = len(predicted & truth), len(predicted - truth), len(truth - predicted)
    triangles = sum(
        sum(tuple(sorted(pair)) in predicted for pair in combinations(triple, 2)) == 2
        for triple in combinations(nodes, 3)
    )
    forbidden = {tuple(sorted(pair)) for pair in cannot_link}
    return {"pairwise_f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0,
            "pairwise_precision": tp / len(predicted) if predicted else 1.0,
            "pairwise_recall": tp / len(truth) if truth else 1.0,
            "false_merge_rate": fp / max(1, len(universe - truth)),
            "predicted_identity_pairs": len(predicted),
            "transitivity_violations": triangles,
            "hard_constraint_violations": len(predicted & forbidden)}


def dependency_risk(
    correctness: Mapping[str, float], required: Iterable[str],
    method: str = "union", primary: str | None = None,
) -> float:
    """Risk of ANY prerequisite failure, deduplicating shared dependencies.

    Union is a bound only with valid probabilities under the same conditioning
    information and a complete dependency closure. Product assumes independence.
    Single is the deliberately incomplete baseline requiring an explicit primary.
    """
    required = set(required)
    if not required <= set(correctness):
        raise ValueError("Missing prerequisite probabilities")
    values = [_probability(correctness[item]) for item in sorted(required)]
    if method == "union":
        return min(1.0, sum(1 - p for p in values))
    if method == "product":
        return 1 - prod(values)
    if method == "single":
        if primary not in required:
            raise ValueError("Single gating requires a declared primary prerequisite")
        return 1 - correctness[primary]
    raise ValueError("Unknown dependency risk method")


@dataclass(frozen=True)
class QueryContext:
    """Only runtime-observable inputs; no gold labels or query outcomes."""
    confidence: float
    source_kind: str
    impact: float = 1.0
    query_cost: float = 1.0

    def __post_init__(self):
        _probability(self.confidence)
        if not self.source_kind or not isfinite(self.impact) or self.impact < 0:
            raise ValueError("A query requires a source kind and nonnegative finite impact")
        if not isfinite(self.query_cost) or self.query_cost < 0:
            raise ValueError("Query cost must be finite and nonnegative")


@dataclass(frozen=True)
class DevelopmentOutcome:
    context: QueryContext
    baseline_correct: bool
    queried_correct: bool


class ValueOfInformationRouter:
    """Development-fitted expected improvement, with fixed bins and shrinkage.

    Scores estimate reduction in weighted error minus the disclosed query cost.
    Predictions are empirical and may fail under distribution shift. We always
    spend the requested budget in comparisons, including negative-value queries.
    """
    def __init__(self, shrinkage: float = 20):
        if not isfinite(shrinkage) or shrinkage < 0:
            raise ValueError("Shrinkage must be nonnegative and finite")
        self.shrinkage = shrinkage
        self.rates = {}
        self.pooled_rate = None

    @staticmethod
    def _key(context):
        return context.source_kind, sum(context.confidence >= cut for cut in (0.6, 0.75, 0.9))

    def fit(self, outcomes: Sequence[DevelopmentOutcome]):
        if not outcomes:
            raise ValueError("Routing requires development outcomes")
        groups = {}
        deltas = []
        for outcome in outcomes:
            delta = int(outcome.queried_correct) - int(outcome.baseline_correct)
            deltas.append(delta)
            groups.setdefault(self._key(outcome.context), []).append(delta)
        self.pooled_rate = sum(deltas) / len(deltas)
        self.rates = {key: (sum(values) + self.shrinkage * self.pooled_rate) /
                      (len(values) + self.shrinkage) for key, values in groups.items()}
        return self

    def score(self, context: QueryContext) -> float:
        if self.pooled_rate is None:
            raise ValueError("Fit on development data before routing")
        rate = self.rates.get(self._key(context), self.pooled_rate)
        return context.impact * rate - context.query_cost

    def manifest(self) -> dict:
        return {"shrinkage": self.shrinkage, "confidence_bin_cuts": [0.6, 0.75, 0.9],
                "pooled_improvement": self.pooled_rate,
                "improvement_by_kind_and_bin": {f"{k[0]}:{k[1]}": v for k, v in sorted(self.rates.items())}}


def select_queries(
    contexts: Sequence[QueryContext], budget: int, policy: str,
    seed: int = 0, router: ValueOfInformationRouter | None = None,
) -> set[int]:
    """Fixed query-count budget, suitable when all query costs are identical."""
    if not isinstance(budget, int) or not 0 <= budget <= len(contexts):
        raise ValueError("Query count must be an integer within the episode size")
    if len({context.query_cost for context in contexts}) > 1:
        raise ValueError("Fixed query-count comparisons require equal query costs")
    if policy == "random":
        return set(Random(seed).sample(range(len(contexts)), budget))
    if policy == "confidence":
        scores = [1 - context.confidence for context in contexts]
    elif policy == "impact":
        scores = [context.impact * (1 - context.confidence) for context in contexts]
    elif policy == "voi":
        if router is None:
            raise ValueError("VOI routing requires a fitted router")
        scores = [router.score(context) for context in contexts]
    else:
        raise ValueError("Unknown routing policy")
    return set(sorted(range(len(contexts)), key=lambda i: (-scores[i], i))[:budget])
