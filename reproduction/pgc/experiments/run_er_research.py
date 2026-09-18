"""Reproducible identity-model training and entity-disjoint E3/E4 ablations.

Run with the pinned research environment. Downloads public weights/data only.
No API credentials are read. Checkpoints are stored in ignored .cache/models.
"""

import argparse
from collections import Counter
from dataclasses import asdict
from difflib import SequenceMatcher
import gc
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
import subprocess
from time import perf_counter

from pgc.decision import DecisionRequest, DecisionResponse
from pgc.decision.local_model import record_text, softmax
from pgc.decision.specialist_er import SpecialistERBackend
from pgc.evaluation import ER_LABELS, evaluate_request, summarize_results
from pgc.experiments.research_data import ROOT, digest, entity_resolution
from pgc.ir import PrimitiveType


MODEL = "cross-encoder/nli-deberta-v3-small"
REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"
SEED = 20260917
MODEL_LABELS = ("different", "same")


def title_similarity(row):
    return SequenceMatcher(None, row["record_1"].get("title", "").lower(),
                           row["record_2"].get("title", "").lower()).ratio()


def inputs(row, title_only=False):
    if title_only:
        return row["record_1"].get("title", ""), row["record_2"].get("title", "")
    return record_text(row["record_1"]), record_text(row["record_2"])


def training_examples(rows, no_hard_negatives=False):
    if not rows:
        raise ValueError("Training data must be nonempty")
    if not no_hard_negatives:
        return list(rows), {"excluded_hard_negative_count": 0, "resampled_easy_negative_count": 0}
    easy_negatives = [r for r in rows if r["gold_label"] == "different" and title_similarity(r) < .65]
    if not easy_negatives:
        raise ValueError("The no-hard-negative ablation requires training-only easy negatives")
    rng = random.Random(SEED)
    count = 0
    selected = []
    for row in rows:
        if row["gold_label"] == "different" and title_similarity(row) >= .65:
            selected.append(rng.choice(easy_negatives))
            count += 1
        else:
            selected.append(row)
    return selected, {"excluded_hard_negative_count": count, "resampled_easy_negative_count": count,
                      "policy": "replace hard negatives with training-only easy negatives; preserve labels and optimizer budget"}


def train_variant(name, rows, args):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, set_seed

    checkpoint = Path(getattr(args, "checkpoint_dir", ROOT / ".cache" / "models")) / name
    selected, selection = training_examples(rows, name == "er-no-hard-negatives")
    config = {"name": name, "base_model": MODEL, "base_revision": REVISION,
              "seed": SEED, "epochs": args.epochs, "batch_size": args.batch_size,
              "max_length": args.max_length, "learning_rate": 2e-5,
              "training_data_sha256": digest(selected), "unique_training_rows": len({r["id"] for r in selected}),
              "training_rows_per_epoch": len(selected), "selection": selection,
              "title_only": name == "er-title-only", "labels": {"0": "different", "1": "same"}}
    manifest_path = checkpoint / "training_manifest.json"
    if args.reuse_checkpoints and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing["configuration"] != config:
            raise ValueError(f"Cached checkpoint configuration differs for {name}")
        return checkpoint, existing
    if checkpoint.exists():
        raise FileExistsError(f"Checkpoint already exists: {checkpoint}; use --reuse-checkpoints or a new --checkpoint-dir")
    set_seed(SEED)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, token=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, revision=REVISION, token=False, use_safetensors=True,
        num_labels=2, id2label={0: "different", 1: "same"},
        label2id={"different": 0, "same": 1}, ignore_mismatched_sizes=True,
    ).to(args.device)
    model.config.pgc_task = "entity_resolution"
    model.config.pgc_training_data_sha256 = config["training_data_sha256"]
    pairs = [inputs(row, config["title_only"]) for row in selected]
    encoded = tokenizer([p[0] for p in pairs], [p[1] for p in pairs], truncation=True,
                        max_length=args.max_length, padding=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
    generator = random.Random(SEED)
    epoch_metrics = []
    start = perf_counter()
    for epoch in range(args.epochs):
        order = list(range(len(selected)))
        generator.shuffle(order)
        loss_sum, examples = 0.0, 0
        model.train()
        for offset in range(0, len(order), args.batch_size):
            indexes = order[offset:offset + args.batch_size]
            features = [{key: values[index] for key, values in encoded.items()} for index in indexes]
            batch = tokenizer.pad(features, padding=True, return_tensors="pt")
            batch = {key: value.to(args.device) for key, value in batch.items()}
            labels = torch.tensor([int(selected[index]["gold_label"] == "same") for index in indexes], device=args.device)
            optimizer.zero_grad(set_to_none=True)
            result = model(**batch, labels=labels)
            result.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            loss_sum += float(result.loss.detach()) * len(indexes)
            examples += len(indexes)
            if offset % (args.batch_size * 100) == 0:
                print(f"{name} epoch={epoch + 1} rows={examples}/{len(selected)} loss={loss_sum/examples:.4f}", flush=True)
        epoch_metrics.append({"epoch": epoch + 1, "examples": examples, "mean_loss": loss_sum / examples})
    if args.device.startswith("cuda"):
        torch.cuda.synchronize()
    duration = perf_counter() - start
    checkpoint.mkdir(parents=True, exist_ok=False)
    model.save_pretrained(checkpoint, safe_serialization=True)
    tokenizer.save_pretrained(checkpoint)
    training_manifest = {"configuration": config, "epoch_metrics": epoch_metrics,
                         "training_wall_seconds": duration, "device": args.device,
                         "optimizer": "AdamW, fixed 2e-5, gradient norm clip 1.0; no evaluation-driven early stopping",
                         "peak_cuda_memory_scope": "process cumulative high-water mark through this variant; not an isolated per-variant measurement",
                         "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated() if args.device.startswith("cuda") else None}
    manifest_path.write_text(json.dumps(training_manifest, indent=2), encoding="utf-8")
    del optimizer, model
    gc.collect()
    if args.device.startswith("cuda"):
        torch.cuda.empty_cache()
    return checkpoint, training_manifest


def request_for(row, title_only=False):
    left, right = inputs(row, title_only)
    return DecisionRequest(row["id"], PrimitiveType.NOUL, "Do these records describe the same publication?",
                           json.dumps([left, right]), labels=list(ER_LABELS), task="entity_resolution",
                           payload={"record_1": left, "record_2": right})


class CachedResponse:
    def __init__(self, name, response):
        self.backend_name, self.response = name, response
    def name(self):
        return self.backend_name
    def version(self):
        return "research-v2"
    def decide(self, request):
        return self.response


def score_responses(name, rows, responses, title_only=False, temperature=None):
    if not rows or len(rows) != len(responses):
        raise ValueError("Scoring requires nonempty aligned rows and responses")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Scoring IDs must be unique")
    if any(row["id"] != response.request_id for row, response in zip(rows, responses)):
        raise ValueError("Scoring response IDs must match example IDs")
    records = []
    for row, response in zip(rows, responses):
        if temperature is not None and not response.error:
            logits = response.raw_output["logits"]
            mapping = response.raw_output["label_mapping"]
            probability = softmax(logits, temperature)
            distribution = {mapping[i]: value for i, value in enumerate(probability)}
            response = DecisionResponse(**{**asdict(response), "distribution": distribution,
                                           "confidence": max(probability),
                                           "metadata": {**response.metadata, "temperature": temperature}})
        request = request_for(row, title_only)
        result = evaluate_request(row["id"], row["gold_label"], CachedResponse(name, response), request, ER_LABELS)
        # Scoring cached outputs must not misreport cache lookup as inference time.
        result.wall_latency_ms = response.latency_ms
        result.metadata["latency_source"] = "backend measured amortized batch wall time; not cache lookup"
        record = result.to_dict()
        record["identity_groups"] = row["identity_groups"]
        record["raw_output"] = response.raw_output
        record["title_similarity"] = title_similarity(row)
        records.append((result, record))
    summary = summarize_results([pair[0] for pair in records], ER_LABELS)
    summary["latency_source"] = "measured_batch_wall_ms_divided_by_batch_size; warm model; training excluded"
    summary["false_merge_rate"] = sum(result.predicted_label == "same" and result.gold_label == "different" for result, _ in records) / max(1, sum(row["gold_label"] == "different" for row in rows))
    negative_count = sum(row["gold_label"] == "different" for row in rows)
    balanced_ids = {row["id"] for row in rows if row["gold_label"] == "different"}
    balanced_ids.update(row["id"] for row in sorted((row for row in rows if row["gold_label"] == "same"), key=lambda r: digest(r["id"]))[:negative_count])
    summary["balanced_challenge"] = summarize_results([result for result, _ in records if result.example_id in balanced_ids], ER_LABELS)
    hard_ids = {row["id"] for row in rows if row["gold_label"] == "different" and title_similarity(row) >= .65}
    hard_results = [result for result, _ in records if result.example_id in hard_ids]
    summary["hard_negative_slice"] = {"count": len(hard_results),
                                      "false_merge_rate": sum(r.predicted_label == "same" for r in hard_results) / len(hard_results) if hard_results else None}
    return {"summary": summary, "predictions": [pair[1] for pair in records]}


def fit_temperature(rows, responses):
    from scipy.optimize import minimize_scalar
    if not rows or len(rows) != len(responses):
        raise ValueError("Calibration requires nonempty aligned rows and responses")
    if any(row["id"] != response.request_id for row, response in zip(rows, responses)):
        raise ValueError("Calibration response IDs must match example IDs")
    if any(response.error for response in responses):
        raise RuntimeError("Cannot calibrate an unavailable classifier")
    for response in responses:
        mapping = response.raw_output["label_mapping"]
        if set(mapping.values()) != set(MODEL_LABELS) or {int(i) for i in mapping} != {0, 1}:
            raise ValueError("Calibration requires a declared same/different label mapping")
    def objective(log_t):
        temperature = math.exp(log_t)
        return sum(-math.log(max(softmax(response.raw_output["logits"], temperature)[
                       {label: int(index) for index, label in response.raw_output["label_mapping"].items()}[row["gold_label"]]], 1e-15))
                   for row, response in zip(rows, responses)) / len(rows)
    optimum = minimize_scalar(objective, bounds=(math.log(.1), math.log(10)), method="bounded")
    temperature = math.exp(float(optimum.x))
    if objective(0) < objective(float(optimum.x)):
        temperature = 1.0
    return {"temperature": temperature, "fit_rows": len(rows), "fit_ids_sha256": digest([r["id"] for r in rows]),
            "calibration_nll_before": objective(0), "calibration_nll_after": objective(math.log(temperature)),
            "objective": "calibration-only log loss; scalar temperature preserves binary confidence ranking"}


def paired_interval(arm, reference, seed=SEED):
    import numpy as np
    a, b = arm["predictions"], reference["predictions"]
    if [row["example_id"] for row in a] != [row["example_id"] for row in b]:
        raise ValueError("Paired comparison requires the same held-out examples")
    delta = np.array([float(x["correct"]) - float(y["correct"]) for x, y in zip(a, b)])
    rng = np.random.default_rng(seed)
    means = delta[rng.integers(0, len(delta), size=(2000, len(delta)))].mean(axis=1)
    brier_delta = np.array([x["brier_score"]-y["brier_score"] for x, y in zip(a, b)])
    brier_samples = brier_delta[rng.integers(0, len(delta), size=(2000, len(delta)))].mean(axis=1)
    negative_pairs = [(x, y) for x, y in zip(a, b) if x["gold_label"] == "different"]
    false_merge_delta = np.array([float(x["predicted_label"] == "same")-float(y["predicted_label"] == "same") for x,y in negative_pairs])
    false_merge_samples = false_merge_delta[rng.integers(0, len(false_merge_delta), size=(2000, len(false_merge_delta)))].mean(axis=1) if len(false_merge_delta) else None
    return {"accuracy_difference": float(delta.mean()), "paired_95_percentile_interval": np.quantile(means, [.025, .975]).tolist(),
            "brier_difference": float(brier_delta.mean()), "brier_ci95": np.quantile(brier_samples, [.025, .975]).tolist(),
            "false_merge_rate_difference": float(false_merge_delta.mean()) if len(false_merge_delta) else None,
            "false_merge_ci95": np.quantile(false_merge_samples, [.025, .975]).tolist() if false_merge_samples is not None else None,
            "false_merge_denominator": len(negative_pairs),
            "bootstrap_unit": "one evaluation pair with disjoint identity groups", "resamples": 2000,
            "multiplicity": "exploratory unadjusted interval; no confirmatory significance claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--reuse-checkpoints", action="store_true")
    parser.add_argument("--checkpoint-dir", type=Path, default=ROOT / ".cache" / "models")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "research")
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.max_length < 8:
        parser.error("epochs/batch-size must be positive and max-length at least 8")
    output = args.output_dir
    if (output / "er_results.json").exists():
        parser.error("er_results.json already exists; choose a new --output-dir to preserve recorded results")
    import torch
    torch.set_num_threads(2)
    splits, data_manifest = entity_resolution()
    output.mkdir(parents=True, exist_ok=True)
    result = {"schema_version": 2, "experiment": "E3/E4 real supervised bibliographic entity matching",
              "data_manifest": data_manifest, "seed": SEED, "environment": {
                  "python": platform.python_version(), "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers", "numpy", "scipy", "scikit-learn")},
                  "device": torch.cuda.get_device_name() if args.device.startswith("cuda") else "cpu",
                  "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  "source_file_sha256": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted((ROOT / "pgc").rglob("*.py"))}},
              "limits": ["One training seed, two fixed epochs; not a model-family superiority claim.",
                         "Bibliographic task; out-of-domain fixture diagnostics are reported separately and do not establish biomedical generalization.",
                         "Entity-disjoint matching changes label prevalence; full, balanced, and class-conditional metrics are reported.",
                         "Architecture/base checkpoint shared across ablations; all variants use the same optimizer example budget."],
              "training": {}, "calibration": {}, "arms": {}, "comparisons": {}}
    # Baselines are fit on training only, including lexical probability conversion.
    from sklearn.linear_model import LogisticRegression
    lexical = LogisticRegression(C=1.0, random_state=SEED).fit(
        [[title_similarity(row)] for row in splits["train"]], [int(r["gold_label"] == "same") for r in splits["train"]])
    prior = sum(row["gold_label"] == "same" for row in splits["train"]) / len(splits["train"])
    for name in ("train-prior", "lexical-logistic"):
        responses = []
        for row in splits["evaluation"]:
            start = perf_counter()
            p = prior if name == "train-prior" else float(lexical.predict_proba([[title_similarity(row)]])[0][1])
            responses.append(DecisionResponse(row["id"], {"different": 1-p, "same": p}, confidence=max(p, 1-p),
                                              latency_ms=(perf_counter()-start)*1000, execution_mode="real",
                                              metadata={"method": name, "fit_split": "train", "neural": False}))
        result["arms"][name] = score_responses(name, splits["evaluation"], responses)
    for name in ("er-title-only", "er-full-context", "er-no-hard-negatives"):
        checkpoint, training = train_variant(name, splits["train"], args)
        result["training"][name] = training
        backend = SpecialistERBackend(str(checkpoint), device=args.device, max_length=args.max_length, batch_size=args.batch_size)
        if not backend.available or backend.execution_mode != "real":
            raise RuntimeError(backend.load_error or "A real identity checkpoint is required")
        title_only = name == "er-title-only"
        predictions = {}
        for split in ("calibration", "evaluation"):
            predictions[split] = backend.batch_decide([request_for(row, title_only) for row in splits[split]])
            if any(response.error for response in predictions[split]):
                raise RuntimeError(next(r.error for r in predictions[split] if r.error))
        calibration = fit_temperature(splits["calibration"], predictions["calibration"])
        result["calibration"][name] = calibration
        result["arms"][name] = score_responses(name, splits["evaluation"], predictions["evaluation"], title_only)
        result["arms"][name + "-calibrated"] = score_responses(name + "-calibrated", splits["evaluation"], predictions["evaluation"], title_only, calibration["temperature"])
        print(name, json.dumps({k: result["arms"][name]["summary"][k] for k in ("accuracy", "macro_f1", "brier_score", "false_merge_rate")}), flush=True)
        del backend
        gc.collect()
        if args.device.startswith("cuda"):
            torch.cuda.empty_cache()
        (output / "er_results.partial.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for name, reference in (("er-full-context", "er-title-only"), ("er-full-context", "er-no-hard-negatives"),
                            ("er-full-context", "lexical-logistic")):
        result["comparisons"][name + " minus " + reference] = paired_interval(result["arms"][name], result["arms"][reference])
    (output / "er_results.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Real entity-matching experiments", "", "Entity-disjoint DBLP-ACM evaluation. Every neural arm trained locally with the same budget.", "",
             "| Arm | Accuracy | Macro-F1 | Sum Brier | False merge rate |", "|---|---:|---:|---:|---:|"]
    for name, arm in result["arms"].items():
        s = arm["summary"]
        lines.append(f"| {name} | {s['accuracy']:.4f} | {s['macro_f1']:.4f} | {s['brier_score']:.4f} | {s['false_merge_rate']:.4f} |")
    lines += ["", "All probability scores use the sum-over-classes convention. Training, calibration and evaluation identities are disjoint.",
              "Negative rate differs across splits due to pair blocking and disjoint matching. See balanced slices and manifests in er_results.json.",
              "One seed and this bibliographic dataset do not establish biomedical generalization or a general neural advantage.",
              "", "## Paired comparisons", "", "```json", json.dumps(result["comparisons"], indent=2), "```", "",
              "Sources: [Ditto data/code](https://github.com/megagonlabs/ditto), [base NLI checkpoint](https://huggingface.co/cross-encoder/nli-deberta-v3-small)."]
    (output / "ER_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
