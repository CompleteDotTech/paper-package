"""
Reference implementations of decision backends for testing.

These are mock/reference implementations that demonstrate the interface
without requiring external API calls.
"""

from pgc.decision import DecisionBackend, DecisionRequest, DecisionResponse
from pgc.ir import PrimitiveType
from typing import List, Dict, Any
import random
import time


class MockDecisionBackend(DecisionBackend):
    """
    Mock backend that returns synthetic but realistic decisions.

    Used for prototyping and testing without external API dependencies.
    """

    def __init__(self, name_prefix: str = "mock"):
        self.name_prefix = name_prefix
        self.call_count = 0

    def name(self) -> str:
        return f"{self.name_prefix}-backend"

    def version(self) -> str:
        return "v1"

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Generate a synthetic decision."""
        self.call_count += 1

        if request.primitive == PrimitiveType.CHOICE:
            return self._decide_choice(request)
        elif request.primitive == PrimitiveType.NOUL:
            return self._decide_noul(request)
        elif request.primitive == PrimitiveType.SCORE:
            return self._decide_score(request)
        else:
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error=f"Unknown primitive: {request.primitive}"
            )

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        """Process multiple decisions."""
        return [self.decide(req) for req in requests]

    def _decide_choice(self, request: DecisionRequest) -> DecisionResponse:
        """Synthetic CHOICE decision."""
        if not request.options:
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error="No options provided"
            )

        # Generate a realistic distribution skewed toward first option
        n = len(request.options)
        probs = []

        # Concentration parameter (higher = more concentrated on first option)
        alpha = random.uniform(2.0, 5.0)

        for i in range(n):
            # Decreasing probabilities
            prob = alpha ** (-i)
            probs.append(prob)

        # Normalize
        total = sum(probs)
        distribution = {opt: p / total for opt, p in zip(request.options, probs)}

        # Pick the highest probability option
        max_opt = max(distribution, key=distribution.get)
        confidence = distribution[max_opt]

        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=confidence,
            latency_ms=random.uniform(10, 50)
        )

    def _decide_noul(self, request: DecisionRequest) -> DecisionResponse:
        """Synthetic NOUL decision."""
        # Random probability between 0.5 and 0.99 (positive bias)
        p_true = random.uniform(0.5, 0.99)

        distribution = {
            "true": p_true,
            "false": 1.0 - p_true
        }

        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=max(p_true, 1.0 - p_true),
            latency_ms=random.uniform(10, 50)
        )

    def _decide_score(self, request: DecisionRequest) -> DecisionResponse:
        """Synthetic SCORE decision."""
        if not request.rubric:
            request.rubric = ["low", "medium", "high"]

        n = len(request.rubric)
        # Random distribution over rubric levels
        probs = [random.uniform(0.1, 0.5) for _ in range(n)]
        total = sum(probs)
        distribution = {
            level: p / total for level, p in zip(request.rubric, probs)
        }

        # Compute mean score
        mean_score = sum(
            i * distribution[level] for i, level in enumerate(request.rubric)
        )

        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=max(distribution.values()),
            raw_output={"mean_score": mean_score},
            latency_ms=random.uniform(10, 50)
        )


class CalibrationControlBackend(DecisionBackend):
    """
    Backend that returns decisions with controlled calibration properties.

    Useful for testing different confidence regimes.
    """

    def __init__(self, confidence_level: float = 0.85):
        """
        Args:
            confidence_level: Desired confidence for decisions (0.5-1.0)
        """
        self.confidence_level = max(0.5, min(1.0, confidence_level))

    def name(self) -> str:
        return "calibration-control"

    def version(self) -> str:
        return f"conf_{self.confidence_level:.2f}"

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Decision with controlled confidence."""
        if request.primitive == PrimitiveType.CHOICE:
            return self._choose_with_confidence(request)
        elif request.primitive == PrimitiveType.NOUL:
            return self._noul_with_confidence(request)
        return DecisionResponse(
            request_id=request.request_id,
            distribution={},
            error="Unsupported primitive"
        )

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        return [self.decide(req) for req in requests]

    def _choose_with_confidence(self, request: DecisionRequest) -> DecisionResponse:
        """CHOICE with target confidence."""
        if not request.options:
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error="No options"
            )

        n = len(request.options)
        first_prob = self.confidence_level
        remaining = 1.0 - first_prob

        # Distribute remaining probability among other options
        other_probs = [remaining / (n - 1) if n > 1 else 0] * (n - 1)

        distribution = {
            request.options[0]: first_prob
        }
        for opt, prob in zip(request.options[1:], other_probs):
            distribution[opt] = prob

        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=first_prob
        )

    def _noul_with_confidence(self, request: DecisionRequest) -> DecisionResponse:
        """NOUL with target confidence."""
        # Confidence means: how far from 0.5?
        p_true = 0.5 + (self.confidence_level - 0.5)

        distribution = {
            "true": p_true,
            "false": 1.0 - p_true
        }

        return DecisionResponse(
            request_id=request.request_id,
            distribution=distribution,
            confidence=self.confidence_level
        )


class NoisyDecisionBackend(DecisionBackend):
    """
    Backend that returns decisions with controlled noise/error rate.

    Useful for testing robustness and error handling.
    """

    def __init__(self, error_rate: float = 0.1):
        """
        Args:
            error_rate: Fraction of decisions that should be "wrong" (0.0-1.0)
        """
        self.error_rate = max(0.0, min(1.0, error_rate))

    def name(self) -> str:
        return "noisy-backend"

    def version(self) -> str:
        return f"err_{self.error_rate:.2f}"

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Decision with controlled error injection."""
        if random.random() < self.error_rate:
            # Inject an error: pick a non-optimal option
            if request.primitive == PrimitiveType.CHOICE and request.options:
                # Pick a wrong option
                wrong_choice = random.choice(request.options[1:])
                distribution = {opt: 0.01 for opt in request.options}
                distribution[wrong_choice] = 0.91
                return DecisionResponse(
                    request_id=request.request_id,
                    distribution=distribution,
                    confidence=0.91  # Confidently wrong!
                )
            elif request.primitive == PrimitiveType.NOUL:
                # Pick wrong direction with high confidence
                return DecisionResponse(
                    request_id=request.request_id,
                    distribution={"true": 0.05, "false": 0.95},
                    confidence=0.95
                )

        # Otherwise, return a good decision
        backend = MockDecisionBackend()
        return backend.decide(request)

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        return [self.decide(req) for req in requests]
