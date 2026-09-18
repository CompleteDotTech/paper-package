"""Pinned, unchanged NLI checkpoint experiments on document-disjoint SciFact splits.

Selection, temperature fitting and train priors are fixed without evaluation labels.
Gold rationale IDs are accessed only by the post-selection retention measurement.
Run: .venv\\Scripts\\python.exe -B -m pgc.experiments.run_nli_research
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import re
import subprocess
import time

from pgc.decision.local_model import LocalPairModel, softmax
from pgc.evaluation import EvaluationResult, RELATION_LABELS, summarize_results
from pgc.experiments.research_data import ROOT, digest, scifact


MODEL_ID = "cross-encoder/nli-deberta-v3-small"
MODEL_REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"
SEED = 20260917
STOPWORDS = set("a an the of to in on and or is are was were be been by for with that this these those as at from it its has have had can may do does did".split())


def words(text):
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOPWORDS}


def fit_idf(training_rows):
    """Fit lexical weights on training documents; annotations are not features."""
    documents = {row["document_id"]: "\n".join(row["evidence"]) for row in training_rows}
    frequency = Counter(word for document in documents.values() for word in words(document))
    return {word: math.log((len(documents) + 1) / (count + 1)) + 1 for word, count in frequency.items()}


def choose_sentences(row, idf, token_length, budget=384):
    """Whole-sentence query overlap selection, preserving original sentence order.

    Sentence rank is IDF-weighted overlap divided by sqrt(sentence word count).
    Ties prefer earlier text. Gold labels and rationale annotations are unused.
    """
    query = words(row["claim"])
    ranked = []
    for index, sentence in enumerate(row["evidence"]):
        terms = words(sentence)
        score = sum(idf.get(word, 1.0) for word in query & terms) / math.sqrt(max(1, len(terms)))
        ranked.append((-score, index))
    selected = []
    for _, index in sorted(ranked):
        candidate = sorted(selected + [index])
        if token_length("\n".join(row["evidence"][i] for i in candidate)) <= budget:
            selected = candidate
    if not selected and ranked:
        # One exceptionally long sentence still supplies evidence; token truncation
        # and rationale loss remain measured explicitly downstream.
        selected = [min(ranked)[1]]
    return selected


def prepare_input(row, variant, tokenizer, idf, max_length=512):
    claim = row["claim"]
    available = max(1, max_length - len(tokenizer(claim, add_special_tokens=False)["input_ids"])
                    - tokenizer.num_special_tokens_to_add(pair=True) - 8)
    if variant == "selected":
        selected = choose_sentences(row, idf,
                                    lambda text: len(tokenizer(text, add_special_tokens=False)["input_ids"]),
                                    budget=min(384, available))
    else:
        selected = list(range(len(row["evidence"])))
    pieces = [row["evidence"][index] for index in selected]
    premise = "\n".join(pieces)
    spans, offset = {}, 0
    for index, sentence in zip(selected, pieces):
        spans[index] = (offset, offset + len(sentence))
        offset += len(sentence) + 1
    if variant == "prefix80":
        premise = premise[:80]
    hypothesis = "Does the evidence support this claim?" if variant == "wrong_hypothesis" else claim
    encoded = tokenizer(premise, hypothesis, truncation=True, max_length=max_length,
                        return_offsets_mapping=True)
    positions = [span for span, sequence in zip(encoded["offset_mapping"], encoded.sequence_ids()) if sequence == 0]
    retained_end = max((span[1] for span in positions), default=0)
    complete = [index for index, (start, end) in spans.items()
                if end <= len(premise) and end <= retained_end and end > start]
    # This is intentionally after input construction. Never rank using gold IDs.
    rationale = set(row.get("rationale_sentence_ids", []))
    retained = rationale & set(complete)
    retention = {
        "gold_rationale_sentences": len(rationale), "retained_gold_rationale_sentences": len(retained),
        "all_gold_rationale_retained": len(retained) == len(rationale) if rationale else None,
        "selected_sentence_ids": selected, "complete_sentence_ids_after_tokenization": complete,
        "input_premise_characters": len(premise), "original_premise_characters": len("\n".join(row["evidence"])),
        "tokenized_premise_retained_character_end": retained_end,
    }
    return (premise, hypothesis), retention


def fit_temperature(logits, gold_indices):
    """Minimize calibration NLL over a fixed positive temperature interval."""
    if not logits or len(logits) != len(gold_indices):
        raise ValueError("Temperature fitting needs matched nonempty calibration rows")

    def objective(log_temperature):
        temperature = math.exp(log_temperature)
        losses = []
        for row, gold in zip(logits, gold_indices):
            values = [value / temperature for value in row]
            maximum = max(values)
            losses.append(maximum + math.log(sum(math.exp(value - maximum) for value in values)) - values[gold])
        return sum(losses) / len(losses)

    lower, upper = math.log(0.05), math.log(20.0)
    grid = [lower + (upper - lower) * i / 100 for i in range(101)]
    best = min(range(len(grid)), key=lambda i: objective(grid[i]))
    left, right = grid[max(0, best - 1)], grid[min(100, best + 1)]
    ratio = (math.sqrt(5) - 1) / 2
    for _ in range(60):
        a, b = right - ratio * (right - left), left + ratio * (right - left)
        if objective(a) <= objective(b):
            right = b
        else:
            left = a
    chosen = min((lower, upper, (left + right) / 2), key=objective)
    return {"temperature": math.exp(chosen), "calibration_rows": len(logits),
            "nll_before": objective(0.0), "nll_after": objective(chosen),
            "bounds": [0.05, 20.0], "at_boundary": abs(chosen - lower) < 1e-6 or abs(chosen - upper) < 1e-6,
            "fit_source": "calibration split only", "objective": "multiclass negative log likelihood"}


def summarize_arm(name, rows, probabilities, timings, retention, execution_mode="real"):
    records = []
    for row, distribution, timing in zip(rows, probabilities, timings):
        prediction = max(distribution, key=distribution.get)
        records.append(EvaluationResult(
            row["id"], name, MODEL_REVISION, "choice", distribution, distribution[prediction],
            row["gold_label"], prediction, prediction == row["gold_label"], distribution[prediction],
            timing.get("latency_ms"), {"input": timing.get("input_tokens", 0), "output": 0},
            labels=list(RELATION_LABELS), service_success=True, execution_mode=execution_mode,
            wall_latency_ms=timing.get("latency_ms"), metadata={"group": row["group"], **timing},
        ))
    summary = summarize_results(records, RELATION_LABELS)
    summary["latency_source"] = "measured synchronized batch wall time divided by batch rows; excludes one-time model load"
    if execution_mode == "constant":
        summary["latency_source"] = "constant baseline; no model inference timing"
        summary["mean_latency_ms"] = None
        summary["latency_denominator"] = 0
    summary["input_tokens_total"] = sum(item.get("input_tokens", 0) for item in timings)
    summary["truncated_input_rows"] = sum(item.get("truncated", False) for item in timings)
    annotated = [item for item in retention if item["gold_rationale_sentences"]]
    rationale_total = sum(item["gold_rationale_sentences"] for item in retention)
    retained_total = sum(item["retained_gold_rationale_sentences"] for item in retention)
    summary["rationale_retention"] = {
        "annotated_rows": len(annotated), "gold_sentence_count": rationale_total,
        "retained_gold_sentence_count": retained_total,
        "sentence_recall": retained_total / rationale_total if rationale_total else None,
        "all_rationales_retained_fraction": sum(item["all_gold_rationale_retained"] for item in annotated) / len(annotated) if annotated else None,
        "measurement": "complete original gold sentence remains after selector and model tokenization; annotation used only for measurement",
    }
    return summary, records


def bootstrap_comparisons(rows, arms, comparisons, seed, iterations=2000):
    """Paired component bootstrap using sufficient statistics, retaining unequal sizes."""
    import numpy as np
    groups = sorted({row["group"] for row in rows})
    group_index = {group: i for i, group in enumerate(groups)}
    labels = {label: i for i, label in enumerate(RELATION_LABELS)}
    indices = np.random.default_rng(seed).integers(0, len(groups), size=(iterations, len(groups)))
    draws, points = {}, {}
    for name, records in arms.items():
        # n, correct, Brier, NLL, then flattened 3x3 confusion matrix.
        statistics = np.zeros((len(groups), 13), dtype=float)
        for row, record in zip(rows, records):
            slot = statistics[group_index[row["group"]]]
            slot[:4] += [1, record.correct, record.brier_score(), record.log_loss()]
            slot[4 + 3 * labels[row["gold_label"]] + labels[record.predicted_label]] += 1

        def metrics(total):
            confusion = total[..., 4:].reshape((*total.shape[:-1], 3, 3))
            tp = np.diagonal(confusion, axis1=-2, axis2=-1)
            denominator = confusion.sum(axis=-1) + confusion.sum(axis=-2)
            f1 = np.divide(2 * tp, denominator, out=np.zeros_like(tp), where=denominator != 0).mean(axis=-1)
            return {"accuracy": total[..., 1] / total[..., 0], "brier_score": total[..., 2] / total[..., 0],
                    "log_loss": total[..., 3] / total[..., 0], "macro_f1": f1}

        draws[name] = metrics(statistics[indices].sum(axis=1))
        points[name] = metrics(statistics.sum(axis=0))
    output = []
    for candidate, baseline in comparisons:
        entry = {"candidate": candidate, "baseline": baseline, "difference": "candidate minus baseline",
                 "bootstrap_groups": len(groups), "iterations": iterations, "seed": seed,
                 "method": "paired percentile 95% CI, resampling connected claim/document/duplicate-abstract components",
                 "metrics": {}}
        for metric in draws[candidate]:
            delta = draws[candidate][metric] - draws[baseline][metric]
            low, high = np.quantile(delta, [0.025, 0.975])
            entry["metrics"][metric] = {"difference": float(points[candidate][metric] - points[baseline][metric]),
                                        "ci95": [float(low), float(high)],
                                        "direction": "higher is better" if metric in {"accuracy", "macro_f1"} else "lower is better"}
        output.append(entry)
    return output


def legacy_diagnostics(rows, raw_logits, canonical_logits):
    """Historical incompatible binary adapters, not claimed three-class systems."""
    results = {}
    answerable = [i for i, row in enumerate(rows) if row["gold_label"] != "NOT_ENOUGH_INFO"]
    for name in ("neutral_index_as_support_probability", "legacy_index_2_raw_logit_clipped"):
        predictions = []
        for index, row in enumerate(rows):
            p = softmax(canonical_logits[index])[2] if name.startswith("neutral") else max(0.0, min(1.0, raw_logits[index][2]))
            prediction = "SUPPORTS" if p >= 0.5 else "REFUTES"
            predictions.append({"id": row["id"], "p_support": p, "predicted_label": prediction,
                                "gold_label": row["gold_label"]})
        results[name] = {
            "status": "legacy/incompatible binary diagnostic derived from cached full-evidence logits, not a three-class model",
            "answerable_rows": len(answerable), "unreachable_nei_rows": len(rows) - len(answerable),
            "answerable_accuracy": sum(predictions[i]["predicted_label"] == rows[i]["gold_label"] for i in answerable) / len(answerable),
            "exact_accuracy_all_labels": sum(p["predicted_label"] == p["gold_label"] for p in predictions) / len(rows),
            "answerable_binary_one_coordinate_brier": sum((predictions[i]["p_support"] - float(rows[i]["gold_label"] == "SUPPORTS")) ** 2 for i in answerable) / len(answerable),
            "predictions": predictions,
        }
    return results


def run(output_path, device="cuda", batch_size=8, max_length=512, bootstrap_iterations=2000):
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("Requested CUDA execution is unavailable; refusing implicit fallback")
    splits, data_manifest = scifact()
    if any(not splits[name] for name in ("train", "calibration", "evaluation")):
        raise ValueError("Every predeclared split must be nonempty")
    for name, rows in splits.items():
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError(f"Duplicate claim-document IDs in {name}; refuse repeated evaluation units")
    print("DATA", json.dumps(data_manifest["split_summary"]), flush=True)
    idf = fit_idf(splits["train"])
    start = time.perf_counter()
    model = LocalPairModel(MODEL_ID, revision=MODEL_REVISION, device=device, max_length=max_length)
    load_seconds = time.perf_counter() - start
    aliases = {"entailment": "SUPPORTS", "contradiction": "REFUTES", "neutral": "NOT_ENOUGH_INFO"}
    label_mapping = {i: aliases[label.lower()] for i, label in model.id2label.items()}
    order = [next(i for i, label in label_mapping.items() if label == canonical) for canonical in RELATION_LABELS]
    cache = {}
    for split_name in ("calibration", "evaluation"):
        variants = ("full", "selected") if split_name == "calibration" else ("full", "selected", "prefix80", "wrong_hypothesis")
        for variant in variants:
            started = time.perf_counter()
            prepared = [prepare_input(row, variant, model.tokenizer, idf, max_length) for row in splits[split_name]]
            preparation_seconds = time.perf_counter() - started
            pairs, retention = zip(*prepared)
            started = time.perf_counter()
            raw_logits, timings = model.predict(list(pairs), batch_size=batch_size)
            inference_seconds = time.perf_counter() - started
            canonical = [[values[index] for index in order] for values in raw_logits]
            cache[(split_name, variant)] = {"raw_logits": raw_logits, "logits": canonical, "timings": timings,
                                          "retention": list(retention), "preparation_seconds": preparation_seconds,
                                          "inference_seconds": inference_seconds,
                                          "pair_sha256": [digest(pair) for pair in pairs]}
            print(f"INFERENCE {split_name}/{variant}: {len(pairs)} rows; {inference_seconds:.2f}s", flush=True)
    # GPU work is now complete; all following fitting/bootstrap is CPU-only.
    del model
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    print("GPU_RELEASED", flush=True)

    calibration_indices = [RELATION_LABELS.index(row["gold_label"]) for row in splits["calibration"]]
    calibrators = {variant: fit_temperature(cache[("calibration", variant)]["logits"], calibration_indices)
                   for variant in ("full", "selected")}
    evaluation = splits["evaluation"]
    train_counts = Counter(row["gold_label"] for row in splits["train"])
    prior = {label: train_counts[label] / len(splits["train"]) for label in RELATION_LABELS}
    summaries, arms = {}, {}
    predictions = {}
    for name in ("full", "full_calibrated", "selected", "selected_calibrated", "prefix80", "wrong_hypothesis"):
        base = name.removesuffix("_calibrated")
        data = cache[("evaluation", base)]
        temperature = calibrators[base]["temperature"] if name.endswith("_calibrated") else 1.0
        probabilities = [dict(zip(RELATION_LABELS, softmax(row, temperature))) for row in data["logits"]]
        summaries[name], arms[name] = summarize_arm(name, evaluation, probabilities, data["timings"], data["retention"])
        summaries[name].update({"temperature": temperature, "preparation_seconds": data["preparation_seconds"],
                                "inference_seconds": data["inference_seconds"], "cached_inference_reused": name.endswith("_calibrated")})
        predictions[name] = [{"id": row["id"], "group": row["group"], "document_id": row["document_id"],
                              "gold_label": row["gold_label"], "distribution": probabilities[index],
                              "predicted_label": arms[name][index].predicted_label,
                              "canonical_logits": data["logits"][index], "raw_logits": data["raw_logits"][index],
                              "pair_sha256": data["pair_sha256"][index], "timing": data["timings"][index],
                              "rationale_retention": data["retention"][index], "execution_mode": "real"}
                             for index, row in enumerate(evaluation)]
    summaries["train_prior"], arms["train_prior"] = summarize_arm(
        "train_prior", evaluation, [prior] * len(evaluation), [{}] * len(evaluation), [], "constant")
    comparisons = bootstrap_comparisons(
        evaluation, arms, [("full", "train_prior"), ("full", "prefix80"), ("full", "wrong_hypothesis"),
                           ("selected", "full"), ("full_calibrated", "full"), ("selected_calibrated", "selected")],
        SEED, iterations=bootstrap_iterations)
    dependencies = {name: importlib.metadata.version(name) for name in ("torch", "transformers", "tokenizers", "numpy", "safetensors")}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    source_files = [Path(__file__), ROOT / "pgc/decision/local_model.py", ROOT / "pgc/evaluation.py", ROOT / "pgc/experiments/research_data.py"]
    result = {
        "schema_version": 1, "timestamp": datetime.now(timezone.utc).isoformat(), "seed": SEED,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "label_mapping": label_mapping,
                  "canonical_order": list(RELATION_LABELS), "weights_updated": False, "device": device,
                  "device_name": torch.cuda.get_device_name() if device.startswith("cuda") else "cpu",
                  "batch_size": batch_size, "max_length": max_length, "torch_threads": 2,
                  "load_seconds": load_seconds, "execution_mode": "real"},
        "dependencies": dependencies, "repository_commit": revision,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
        "data_manifest": data_manifest, "selection": {"method": "training-IDF lexical overlap over whole abstract sentences",
                                                        "maximum_premise_token_budget": 384, "idf_training_documents": len({r['document_id'] for r in splits['train']}),
                                                        "gold_annotations_used_for_selection": False, "idf_sha256": digest(idf)},
        "temperature_calibration": calibrators, "train_prior": prior,
        "metrics": summaries, "paired_group_bootstrap": comparisons,
        "predictions": predictions,
        "calibration_predictions": {variant: [{"id": row["id"], "group": row["group"], "gold_label": row["gold_label"],
                                                 "canonical_logits": cache[("calibration", variant)]["logits"][index]}
                                                for index, row in enumerate(splits["calibration"])] for variant in ("full", "selected")},
        "legacy_binary_diagnostics": legacy_diagnostics(evaluation, cache[("evaluation", "full")]["raw_logits"], cache[("evaluation", "full")]["logits"]),
        "limitations": ["Cited-abstract classification only; not document retrieval or an official SciFact leaderboard result.",
                        "One unchanged public checkpoint and one fixed held-out split; no cross-domain guarantee.",
                        "Rationale retention is complete-sentence recall after tokenization, not verified causal attribution.",
                        "Legacy binary diagnostics are incompatible with the three-class task and excluded from primary comparisons.",
                        "Group-bootstrap intervals condition on fixed model, training split and fitted temperatures; multiplicity is not corrected.",
                        "Local inference uses measured device time; monetary compute cost was not estimated."],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    write_report(result, output_path.with_name("NLI_RESULTS.md"))
    print("SAVED", output_path, flush=True)
    return result


def reanalyze_deduplicated(source_path, output_path, bootstrap_iterations=2000):
    """Reuse verified cached neural outputs after removing duplicate citations.

    This never loads a model or uses the GPU. Source archive bytes, training and
    calibration membership, and every retained inference pair must be unchanged.
    Original inference source hashes remain alongside reanalysis source hashes.
    """
    source_bytes = source_path.read_bytes()
    result = json.loads(source_bytes)
    splits, manifest = scifact()
    if result["data_manifest"]["source"]["sha256"] != manifest["source"]["sha256"]:
        raise ValueError("Cached inference came from different data archive bytes")
    for split in ("train", "calibration"):
        if result["data_manifest"]["split_summary"][split] != manifest["split_summary"][split]:
            raise ValueError(f"{split} changed; calibration/prior cannot be reused")
    if digest(fit_idf(splits["train"])) != result["selection"]["idf_sha256"]:
        raise ValueError("Training-derived lexical selector changed")
    rows = splits["evaluation"]
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Corrected evaluation IDs must be unique")
    for variant, records in result["calibration_predictions"].items():
        expected = {row["id"]: (row["gold_label"], row["group"]) for row in splits["calibration"]}
        if {row["id"]: (row["gold_label"], row["group"]) for row in records} != expected:
            raise ValueError(f"Calibration annotations changed for {variant}")
    arms, summaries = {}, {}
    original_count = len(result["predictions"]["full"])
    for name, records in result["predictions"].items():
        indexed = {}
        for record in records:
            if record["id"] in indexed:
                previous = indexed[record["id"]]
                if (record["gold_label"], record["pair_sha256"]) != (previous["gold_label"], previous["pair_sha256"]):
                    raise ValueError("Repeated ID has conflicting label/input; cannot deduplicate")
            else:
                indexed[record["id"]] = record
        retained = [indexed[row["id"]] for row in rows]
        base = name.removesuffix("_calibrated")
        for row, record in zip(rows, retained):
            if (row["gold_label"], row["group"]) != (record["gold_label"], record["group"]):
                raise ValueError("Retained evaluation annotations changed")
            premise = "\n".join(row["evidence"][i] for i in record["rationale_retention"]["selected_sentence_ids"])
            if base == "prefix80":
                premise = premise[:80]
            hypothesis = "Does the evidence support this claim?" if base == "wrong_hypothesis" else row["claim"]
            if digest((premise, hypothesis)) != record["pair_sha256"]:
                raise ValueError("Cached model pair differs from corrected dataset input")
            if record["execution_mode"] != "real":
                raise ValueError("Cached experiment contains non-real model outputs")
        summaries[name], arms[name] = summarize_arm(
            name, rows, [record["distribution"] for record in retained],
            [record["timing"] for record in retained], [record["rationale_retention"] for record in retained])
        previous = result["metrics"][name]
        summaries[name].update({key: previous[key] for key in ("temperature", "preparation_seconds", "inference_seconds")})
        summaries[name].update({"cached_inference_reused": True, "inference_rows_originally_executed": original_count,
                               "analysis_rows_after_deduplication": len(rows),
                               "timing_note": "Original measured inference/preprocessing includes the discarded duplicate; row timings are retained amortized measurements."})
        result["predictions"][name] = retained
    summaries["train_prior"], arms["train_prior"] = summarize_arm(
        "train_prior", rows, [result["train_prior"]] * len(rows), [{}] * len(rows), [], "constant")
    result["metrics"] = summaries
    comparisons = [(item["candidate"], item["baseline"]) for item in result["paired_group_bootstrap"]]
    result["paired_group_bootstrap"] = bootstrap_comparisons(rows, arms, comparisons, result["seed"], bootstrap_iterations)
    full = result["predictions"]["full"]
    result["legacy_binary_diagnostics"] = legacy_diagnostics(rows, [row["raw_logits"] for row in full], [row["canonical_logits"] for row in full])
    result["data_manifest"] = manifest
    result["inference_source_sha256"] = result["source_sha256"]
    result["source_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (Path(__file__), ROOT / "pgc/decision/local_model.py", ROOT / "pgc/evaluation.py", ROOT / "pgc/experiments/research_data.py")}
    result["reanalysis"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(), "method": "offline reuse of unchanged cached neural logits/probabilities",
        "source_artifact": str(source_path.relative_to(ROOT)), "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "original_evaluation_rows": original_count, "corrected_evaluation_rows": len(rows),
        "discarded_duplicate_rows": original_count - len(rows), "new_model_calls": 0,
        "reason": "SciFact claim 1245 repeats cited document 7662395; retain one claim-document unit",
        "training_calibration_and_input_pair_hashes_verified_unchanged": True,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    write_report(result, output_path.with_name("NLI_RESULTS.md"))
    print("REANALYZED", output_path, flush=True)
    return result


def write_report(result, path):
    lines = ["# NLI research results", "", "Unchanged pinned DeBERTa checkpoint; real CUDA inference. These are supplied-cited-abstract classification experiments, not retrieval or leaderboard scores.", "",
             "| Arm | Accuracy | Macro F1 | Sum Brier | Log loss | Rationale sentence recall |", "|---|---:|---:|---:|---:|---:|"]
    for name, metrics in result["metrics"].items():
        recall = metrics["rationale_retention"]["sentence_recall"]
        lines.append(f"| {name} | {metrics['accuracy']:.4f} | {metrics['macro_f1']:.4f} | {metrics['brier_score']:.4f} | {metrics['log_loss']:.4f} | {recall:.4f} |" if recall is not None else
                     f"| {name} | {metrics['accuracy']:.4f} | {metrics['macro_f1']:.4f} | {metrics['brier_score']:.4f} | {metrics['log_loss']:.4f} | N/A |")
    if "reanalysis" in result:
        lines.extend(["", "One duplicated source citation was removed: the final evaluation contains 339 unique claim-document pairs. Metrics and group intervals were recomputed offline from unchanged cached model outputs; training, calibration and retained input hashes were verified unchanged. The 340-row intermediate artifact is archived and is not the reported evaluation."])
    lines.extend(["", "Temperatures were fitted only on the separate calibration split; the prior only on training labels. Selection uses training-IDF lexical overlap and no rationale annotations. Rationale recall is measured after the model's 512-token truncation.", "",
                  "| Paired comparison | Accuracy delta [95% group CI] | Brier delta [95% group CI] |", "|---|---:|---:|"])
    for comparison in result["paired_group_bootstrap"]:
        accuracy, brier = comparison["metrics"]["accuracy"], comparison["metrics"]["brier_score"]
        lines.append(f"| {comparison['candidate']} minus {comparison['baseline']} | {accuracy['difference']:+.4f} [{accuracy['ci95'][0]:+.4f}, {accuracy['ci95'][1]:+.4f}] | {brier['difference']:+.4f} [{brier['ci95'][0]:+.4f}, {brier['ci95'][1]:+.4f}] |")
    lines.extend(["", "Higher accuracy and lower Brier are better. Intervals resample connected claim/document/duplicate-abstract groups. Intervals containing zero do not establish an improvement in that metric. Calibration is not expected to change argmax accuracy.", "",
                  "Full logits, errors/coverage, per-class confusion, reliability bins, calibration records, source hashes, pinned model/dependency versions, timing and legacy binary diagnostics are in [nli_results.json](nli_results.json).", "",
                  "Data: " + json.dumps(result["data_manifest"]["split_summary"], sort_keys=True), "",
                  "Limitations: " + " ".join(result["limitations"]), ""])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/research/nli_results.json")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--bootstrap-iterations", type=int, default=2000)
    parser.add_argument("--deduplicate-from", type=Path, help="Reanalyze a saved intermediate run without loading a model")
    args = parser.parse_args()
    if args.deduplicate_from:
        reanalyze_deduplicated(args.deduplicate_from.resolve(), args.output, args.bootstrap_iterations)
    else:
        run(args.output, args.device, args.batch_size, args.max_length, args.bootstrap_iterations)
