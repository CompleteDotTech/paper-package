"""Shared local classifier adapter with explicit task/label contracts."""

from pgc.decision import DecisionBackend, DecisionResponse
from pgc.decision.local_model import LocalPairModel, softmax
from pgc.ir import PrimitiveType


class PairBackend(DecisionBackend):
    task = ""
    backend_name = ""
    checkpoint_labels = {}

    def __init__(self, model_name, *, revision=None, device="cpu", max_length=512,
                 temperature=1.0, model=None, load_model=True, batch_size=8):
        self.model_name = model_name or "identity-checkpoint-required"
        self.revision, self.temperature, self.batch_size = revision, temperature, batch_size
        softmax([0.0], temperature)  # Reject invalid policy configuration at construction.
        self.model, self.available, self.load_error = model, False, None
        self.execution_mode = "mock" if model is not None else "unavailable"
        self.call_count = 0
        if model is None and model_name and load_model:
            try:
                self.model = LocalPairModel(model_name, revision=revision, device=device, max_length=max_length)
                self.execution_mode = "real"
            except Exception as exc:
                self.load_error = f"{type(exc).__name__}: {exc}"
        if self.model is not None:
            try:
                self.label_mapping = {int(i): self.checkpoint_labels[str(label).lower()]
                                      for i, label in self.model.id2label.items()}
                if (set(self.label_mapping) != set(range(len(self.checkpoint_labels)))
                        or set(self.label_mapping.values()) != set(self.checkpoint_labels.values())):
                    raise ValueError("Checkpoint has duplicate or missing labels")
                self.available = True
            except (KeyError, TypeError, ValueError) as exc:
                self.load_error = f"Invalid {self.task} checkpoint labels: {exc}"
                self.execution_mode = "unavailable"
        if not self.available and self.load_error is None:
            self.load_error = "A trained checkpoint is required; no fallback prediction is available"

    def name(self):
        return self.backend_name if self.execution_mode == "real" else f"{self.backend_name}-{self.execution_mode}"

    def version(self):
        return f"{self.model_name}@{self.revision or 'local-or-resolved-at-load'}"

    def _metadata(self):
        return {**getattr(self.model, "metadata", {}), "model_id": self.model_name,
                "temperature": self.temperature, "task": self.task}

    def _error(self, request, error):
        return DecisionResponse(request.request_id, {}, error=error,
                                execution_mode=self.execution_mode, metadata=self._metadata())

    def decide(self, request):
        return self.batch_decide([request])[0]

    def batch_decide(self, requests):
        if not self.available:
            return [self._error(request, self.load_error) for request in requests]
        responses, valid, pairs = [None] * len(requests), [], []
        for index, request in enumerate(requests):
            try:
                if request.task != self.task or request.primitive not in (PrimitiveType.CHOICE, PrimitiveType.NOUL):
                    raise ValueError(f"This checkpoint requires explicit task={self.task}")
                labels = set(self.checkpoint_labels.values())
                if request.labels is not None and set(request.labels) != labels:
                    raise ValueError(f"Task requires exactly these labels: {sorted(labels)}")
                left, right = self.input_pair(request)
                if not isinstance(left, str) or not isinstance(right, str) or not left.strip() or not right.strip():
                    raise ValueError("Two separate, nonempty text inputs are required")
                valid.append(index)
                pairs.append((left, right))
            except (TypeError, ValueError) as exc:
                responses[index] = self._error(request, str(exc))
        if pairs:
            try:
                rows, timings = self.model.predict(pairs, batch_size=self.batch_size)
                if len(rows) != len(valid) or len(timings) != len(valid):
                    raise ValueError("Model response count mismatch")
                for index, logits, timing in zip(valid, rows, timings):
                    if len(logits) != len(self.checkpoint_labels):
                        raise ValueError("Wrong number of class logits")
                    probabilities = softmax(logits, self.temperature)
                    distribution = {self.label_mapping[i]: p for i, p in enumerate(probabilities)}
                    responses[index] = DecisionResponse(
                        requests[index].request_id, distribution, confidence=max(probabilities),
                        raw_output={"logits": list(map(float, logits)), "label_mapping": self.label_mapping},
                        latency_ms=timing.get("latency_ms"),
                        tokens_used={"input": timing.get("input_tokens", 0), "output": 0},
                        execution_mode=self.execution_mode, metadata={**self._metadata(), **timing})
                self.call_count += len(pairs)
            except Exception as exc:
                for index in valid:
                    responses[index] = self._error(requests[index], f"Inference failed: {type(exc).__name__}: {exc}")
        return responses

    def input_pair(self, request):
        raise NotImplementedError

    def estimate_cost(self, requests):
        return {"estimated_api_cost_usd": 0.0, "estimated_cost_usd": None,
                "note": "Local device time is measured; zero API fees is not zero total cost."}
