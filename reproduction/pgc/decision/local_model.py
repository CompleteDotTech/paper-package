"""Explicit, inspectable local sequence-pair inference. No fallback predictions."""

import hashlib
import math
from pathlib import Path
from time import perf_counter


def softmax(logits, temperature=1.0):
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("Temperature must be finite and positive")
    values = [float(value) / temperature for value in logits]
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("Logits must be nonempty and finite")
    maximum = max(values)
    exp = [math.exp(value - maximum) for value in values]
    total = sum(exp)
    return [value / total for value in exp]


class LocalPairModel:
    def __init__(self, model_name, *, revision=None, device="cpu", max_length=512):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch, self.device, self.max_length = torch, device, max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision, token=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, revision=revision, token=False, use_safetensors=True,
        ).to(device).eval()
        self.id2label = {int(k): str(v) for k, v in self.model.config.id2label.items()}
        checkpoint, local_hashes = Path(model_name), {}
        if checkpoint.is_dir():
            for name in ("config.json", "model.safetensors"):
                file = checkpoint / name
                if file.is_file():
                    with file.open("rb") as stream:
                        local_hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
        self.metadata = {
            "model_id": model_name, "requested_revision": revision,
            "model_revision": getattr(self.model.config, "_commit_hash", None),
            "local_checkpoint_sha256": local_hashes, "device": device,
            "label_mapping": self.id2label, "max_length": max_length,
            "score_type": "raw_logits", "input_serialization_version": "pair-v2",
        }

    def predict(self, pairs, batch_size=8):
        logits, measurements = [], []
        for offset in range(0, len(pairs), batch_size):
            batch = pairs[offset:offset + batch_size]
            if self.device.startswith("cuda"):
                self.torch.cuda.synchronize()
            start = perf_counter()
            left, right = zip(*batch)
            original_lengths = [len(self.tokenizer(a, b, truncation=False)["input_ids"]) for a, b in batch]
            encoded = self.tokenizer(list(left), list(right), padding=True,
                                     truncation=True, max_length=self.max_length,
                                     return_tensors="pt")
            lengths = encoded["attention_mask"].sum(dim=1).tolist()
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with self.torch.inference_mode():
                values = self.model(**encoded).logits.detach().float().cpu().tolist()
            if self.device.startswith("cuda"):
                self.torch.cuda.synchronize()
            elapsed = (perf_counter() - start) * 1000
            logits.extend(values)
            measurements.extend({
                "latency_ms": elapsed / len(batch),
                "latency_measurement": "measured_batch_wall_ms_divided_by_batch_size",
                "batch_size": len(batch), "input_tokens": int(length),
                "original_input_tokens": original, "truncated": original > length,
            } for original, length in zip(original_lengths, lengths))
        return logits, measurements


def record_text(record):
    """Deterministic, label-free serialization of an entity's available attributes."""
    if isinstance(record, str):
        return record
    if not isinstance(record, dict):
        raise ValueError("Entity record must be text or an attribute mapping")
    return " ".join(f"{key}: {record[key]}" for key in sorted(record)
                    if key not in {"gold_label", "label", "id", "entity_id"} and record[key] is not None)
