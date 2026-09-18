"""Three-way NLI with checkpoint-declared labels; no random fallback."""
from pgc.decision.pair_backend import PairBackend


class SpecialistNLIBackend(PairBackend):
    task = "relation_support"
    backend_name = "specialist-nli"
    checkpoint_labels = {"entailment": "SUPPORTS", "contradiction": "REFUTES", "neutral": "NOT_ENOUGH_INFO"}

    def __init__(self, model_name="cross-encoder/nli-deberta-v3-small", **kwargs):
        super().__init__(model_name, **kwargs)

    def input_pair(self, request):
        claim = request.payload.get("claim")
        evidence = request.payload.get("evidence")
        if isinstance(evidence, list) and all(isinstance(item, str) for item in evidence):
            evidence = "\n".join(evidence)
        return evidence, claim
