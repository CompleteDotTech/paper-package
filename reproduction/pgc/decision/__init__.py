"""
Decision backends: pluggable semantic judgment implementations.

Abstract interface for models that produce typed decisions (NOUL, CHOICE, SCORE).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json
from pgc.ir import Decision, PrimitiveType, DecisionLedger


@dataclass
class DecisionRequest:
    """Standardized question to a decision backend."""
    request_id: str
    primitive: PrimitiveType
    question: str
    state: str  # Context (evidence text, JSON, etc.)
    options: Optional[List[str]] = None  # For CHOICE
    rubric: Optional[List[str]] = None  # For SCORE
    task: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    labels: Optional[List[str]] = None


@dataclass
class DecisionResponse:
    """Standardized output from a decision backend."""
    request_id: str
    distribution: Dict[str, float]  # Probabilities
    confidence: Optional[float] = None  # Model's self-assessed confidence
    raw_output: Optional[Dict[str, Any]] = None  # Full model response
    latency_ms: Optional[float] = None
    tokens_used: Optional[Dict[str, int]] = None  # {"input": N, "output": M}
    error: Optional[str] = None
    execution_mode: str = "unknown"  # real, mock, unavailable, or legacy unknown
    metadata: Dict[str, Any] = field(default_factory=dict)


class DecisionBackend(ABC):
    """Abstract decision-making interface."""

    @abstractmethod
    def name(self) -> str:
        """Model/backend name."""
        pass

    @abstractmethod
    def version(self) -> str:
        """Model version string."""
        pass

    @abstractmethod
    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Invoke the decision model."""
        pass

    @abstractmethod
    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        """Invoke multiple decisions (may be batched by backend)."""
        pass

    def estimate_cost(self, requests: List[DecisionRequest]) -> Dict[str, Any]:
        """Estimate tokens and cost for a batch."""
        return {"tokens": None, "estimated_cost_usd": None}


# ============================================================================
# Reference implementation: Frontier LLM backend
# ============================================================================

class FrontierLLMBackend(DecisionBackend):
    """
    Baseline: GPT-4o or similar frontier LLM as decision model.
    Receives the same typed questions as Jev, but via conventional prompting.
    """

    def __init__(self, model_id: str = "gpt-4o"):
        self.model_id = model_id
        self.request_count = 0

    def name(self) -> str:
        return "frontier-llm"

    def version(self) -> str:
        return self.model_id

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Stub: format as LLM prompt, call API, parse structured response."""
        # This is a placeholder. In a real implementation:
        # 1. Convert request to a detailed prompt
        # 2. Call OpenAI / Anthropic API
        # 3. Parse response
        # 4. Extract probability distribution

        prompt = self._format_prompt(request)
        # response = client.messages.create(...)  # Actual API call
        # parsed = self._parse_response(response, request.primitive)

        # For now, return a stub:
        return DecisionResponse(
            request_id=request.request_id,
            distribution={},  # Would be filled from parsed response
            confidence=None,
            error="Stub: implement actual API calls"
        )

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        """Process multiple decisions sequentially (no batching for LLM)."""
        return [self.decide(req) for req in requests]

    def _format_prompt(self, request: DecisionRequest) -> str:
        """Convert decision request to LLM prompt."""
        if request.primitive == PrimitiveType.CHOICE:
            options_str = "\n".join(f"  {i}: {opt}" for i, opt in enumerate(request.options or []))
            return f"""{request.question}

Options:
{options_str}

Answer with just the option number (0-indexed)."""

        elif request.primitive == PrimitiveType.NOUL:
            return f"""{request.question}

State your confidence from 0 (definitely not) to 1 (definitely yes)."""

        elif request.primitive == PrimitiveType.SCORE:
            rubric_str = "\n".join(f"  {i}: {r}" for i, r in enumerate(request.rubric or []))
            return f"""{request.question}

Rubric:
{rubric_str}

Select the most appropriate level."""

        return request.question

    def _parse_response(self, response: str, primitive: PrimitiveType) -> Dict[str, float]:
        """Extract probability distribution from LLM output."""
        # Placeholder
        return {}


# ============================================================================
# Reference implementation: Specialist classifier backend
# ============================================================================

class SpecialistClassifierBackend(DecisionBackend):
    """
    Domain-specific classifier (e.g., cross-encoder for entity matching).
    Pre-trained on task-specific data.
    """

    def __init__(self, model_path: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        self.model_path = model_path
        self.model = None  # Load on demand

    def name(self) -> str:
        return "specialist-classifier"

    def version(self) -> str:
        return self.model_path.split("/")[-1]

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Use specialist model to make a decision."""
        # For entity matching: compute similarity scores
        # For relation support: compute entailment scores
        # etc.

        if request.primitive == PrimitiveType.CHOICE:
            # Score each option
            scores = {}
            for option in request.options or []:
                # score = self.model.predict([request.state, option])
                scores[option] = 0.5  # Placeholder

            # Normalize to probabilities
            total = sum(scores.values())
            distribution = {k: v / total for k, v in scores.items()}

            return DecisionResponse(
                request_id=request.request_id,
                distribution=distribution,
                confidence=max(distribution.values())
            )

        return DecisionResponse(
            request_id=request.request_id,
            distribution={},
            error="Stub"
        )

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        """Batch similar requests for efficiency."""
        return [self.decide(req) for req in requests]


# ============================================================================
# TypeSafe Jev backend (when available)
# ============================================================================

class JevBackend(DecisionBackend):
    """
    TypeSafe AI's Jev System One model.
    Note: Requires TypeSafe API key and current SDK.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "not-set"
        self.jev_version = "jev-1.13.0"  # Current as of 2026-09-17
        self.available = False

        # Attempt to import and configure
        try:
            import typesafe_sdk
            self.client = typesafe_sdk.Client(api_key=self.api_key)
            self.available = True
        except ImportError:
            pass

    def name(self) -> str:
        return "jev-typesafe"

    def version(self) -> str:
        return self.jev_version

    def decide(self, request: DecisionRequest) -> DecisionResponse:
        """Call Jev System One API."""
        if not self.available:
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error="TypeSafe SDK not available"
            )

        # Format request for Jev
        jev_request = self._format_for_jev(request)

        # Call API (stub for now)
        try:
            # response = self.client.decide(jev_request)
            # parsed = self._parse_jev_response(response)
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error="Stub: implement Jev API calls"
            )
        except Exception as e:
            return DecisionResponse(
                request_id=request.request_id,
                distribution={},
                error=str(e)
            )

    def batch_decide(self, requests: List[DecisionRequest]) -> List[DecisionResponse]:
        """Jev supports batching multiple questions in one request."""
        if not self.available:
            return [
                DecisionResponse(
                    request_id=r.request_id,
                    distribution={},
                    error="TypeSafe SDK not available"
                )
                for r in requests
            ]

        # Batch all requests into one call
        jev_batch = self._format_batch_for_jev(requests)

        try:
            # response = self.client.batch_decide(jev_batch)
            # parsed = self._parse_batch_response(response)
            return [
                DecisionResponse(
                    request_id=r.request_id,
                    distribution={},
                    error="Stub: implement Jev batch API calls"
                )
                for r in requests
            ]
        except Exception as e:
            return [
                DecisionResponse(
                    request_id=r.request_id,
                    distribution={},
                    error=str(e)
                )
                for r in requests
            ]

    def _format_for_jev(self, request: DecisionRequest) -> Dict[str, Any]:
        """Convert DecisionRequest to Jev API format."""
        # Jev expects: state (shared context) + list of questions
        jev_question = {}

        if request.primitive == PrimitiveType.CHOICE:
            jev_question["type"] = "choice"
            jev_question["options"] = request.options or []

        elif request.primitive == PrimitiveType.NOUL:
            jev_question["type"] = "noul"

        elif request.primitive == PrimitiveType.SCORE:
            jev_question["type"] = "score"
            jev_question["levels"] = request.rubric or []

        jev_question["question"] = request.question

        return {
            "state": request.state,
            "questions": [jev_question]
        }

    def _format_batch_for_jev(self, requests: List[DecisionRequest]) -> Dict[str, Any]:
        """Format multiple requests as one Jev batch."""
        # Assume all requests share the same state for now (simplification)
        if requests:
            shared_state = requests[0].state
            questions = [self._format_for_jev(r)["questions"][0] for r in requests]
            return {"state": shared_state, "questions": questions}
        return {}

    def _parse_jev_response(self, response: Dict[str, Any]) -> Dict[str, float]:
        """Extract probabilities from Jev response."""
        # Jev returns full distributions for each decision
        if "choices" in response:
            return {choice["option"]: choice["probability"] for choice in response["choices"]}
        return {}

    def estimate_cost(self, requests: List[DecisionRequest]) -> Dict[str, Any]:
        """Estimate Jev costs."""
        # Current pricing: $0.042 per million input tokens
        # Estimate ~500-1000 tokens per request depending on state size
        mean_tokens_per_request = 750
        total_tokens = len(requests) * mean_tokens_per_request
        cost_usd = (total_tokens / 1_000_000) * 0.042

        return {
            "tokens": total_tokens,
            "estimated_cost_usd": cost_usd,
            "rate": "$0.042 per million input tokens"
        }
