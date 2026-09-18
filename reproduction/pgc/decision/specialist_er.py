"""Identity classifier adapter: relevance ranking scores are not identity probabilities."""
from pgc.decision.local_model import record_text
from pgc.decision.pair_backend import PairBackend


class SpecialistERBackend(PairBackend):
    task = "entity_resolution"
    backend_name = "specialist-er"
    checkpoint_labels = {"same": "same", "different": "different"}

    def __init__(self, model_name=None, **kwargs):
        kwargs.setdefault("max_length", 256)
        super().__init__(model_name, **kwargs)

    def input_pair(self, request):
        left = record_text(request.payload.get("record_1", request.payload.get("mention_1")))
        right = record_text(request.payload.get("record_2", request.payload.get("mention_2")))
        context = request.payload.get("context")
        if context:
            left += f"\nContext: {context}"
            right += f"\nContext: {context}"
        return left, right
