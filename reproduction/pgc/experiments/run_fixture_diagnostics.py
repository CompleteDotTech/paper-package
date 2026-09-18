"""Run repaired original fixture harnesses with explicit local models and controls.

These hand-curated examples are development/OOD diagnostics. They are neither
official SciFact evaluation data nor held-out biomedical validation. No retraining
or external model API is performed; lexical logistic regression fits DBLP train.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import gc
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from time import perf_counter
import unicodedata

from pgc.decision import DecisionResponse
from pgc.decision.specialist_er import SpecialistERBackend
from pgc.decision.specialist_nli import SpecialistNLIBackend
from pgc.evaluation import ER_LABELS, RELATION_LABELS, json_safe
from pgc.experiments.benchmark_entity_resolution_100 import run_entity_resolution_benchmark
from pgc.experiments.benchmark_relation_support_50 import run_relation_support_benchmark
from pgc.experiments.entity_resolution_100 import load_entity_resolution_100
from pgc.experiments.scifact_50 import load_scifact_50
from pgc.experiments.research_data import ROOT, digest, entity_resolution
from pgc.experiments.run_er_research import title_similarity


MODEL = "cross-encoder/nli-deberta-v3-small"
REVISION = "fa2804872c3b4bd748f38c0185cc85775361e735"
SEED = 20260917
STOPWORDS = set("a an the of to in on and or is are was were be been by for with that this these those as at from it its has have had can may do does did".split())


def point_mass(label, labels):
    return {candidate: float(candidate == label) for candidate in labels}


def normalize_mention(text):
    return "".join(character for character in unicodedata.normalize("NFKC", text).casefold() if character.isalnum())


def relation_lexical_label(payload):
    """Fixed, deliberately shallow rule; its output is not calibrated probability."""
    claim = set(re.findall(r"[a-z0-9]+", payload["claim"].lower()))
    evidence = set(re.findall(r"[a-z0-9]+", "\n".join(payload["evidence"]).lower()))
    content = claim - STOPWORDS
    coverage = len(content & evidence) / max(1, len(content))
    if coverage < 0.6:
        return "NOT_ENOUGH_INFO"
    negation = {"no", "not", "neither", "without"}
    return "REFUTES" if bool(claim & negation) != bool(evidence & negation) else "SUPPORTS"


class FunctionalBackend:
    """An actually executed deterministic/learned baseline, explicitly non-neural."""
    def __init__(self, name, task, labels, predictor, metadata):
        self.backend_name, self.task, self.labels = name, task, tuple(labels)
        self.predictor, self.metadata = predictor, {"neural": False, **metadata}

    def name(self):
        return self.backend_name

    def version(self):
        return "fixture-diagnostic-baseline-v1"

    def decide(self, request):
        started = perf_counter()
        if request.task != self.task or set(request.labels or ()) != set(self.labels):
            return DecisionResponse(request.request_id, {}, error="Baseline task/label mismatch", execution_mode="real")
        distribution = self.predictor(request.payload)
        return DecisionResponse(request.request_id, distribution, confidence=max(distribution.values()),
                                latency_ms=(perf_counter() - started) * 1000,
                                execution_mode="real", metadata=self.metadata,
                                tokens_used={"input": 0, "output": 0})


class RecordingBackend:
    """Preserve actual adapter responses while exercising the unchanged harness."""
    def __init__(self, backend):
        self.backend, self.responses = backend, {}

    def name(self):
        return self.backend.name()

    def version(self):
        return self.backend.version()

    def decide(self, request):
        response = self.backend.decide(request)
        self.responses[request.request_id] = json_safe(response)
        return response


def constant_backend(task, labels, label):
    return FunctionalBackend("constant-" + label, task, labels, lambda payload: point_mass(label, labels),
                             {"constant_label": label, "fit_split": None,
                              "probability_semantics": "Point mass encoding of a predeclared constant prediction, not calibrated confidence."})


def uncertain_diagnostics(results):
    """Describe predictions for unadjudicated examples without correctness credit."""
    rows = [row for row in results if not row.semantic_eligible]
    valid = [row for row in rows if row.service_success]
    confident = [row for row in valid if row.confidence >= 0.9]
    return {"offered_examples": len(rows), "successful_responses": len(valid),
            "errors": len(rows) - len(valid),
            "predictions": dict(Counter(row.predicted_label for row in rows)),
            "high_confidence_threshold": 0.9, "high_confidence_count": len(confident),
            "high_confidence_among_successful": len(confident) / len(valid) if valid else None,
            "high_confidence_offered_fraction": len(confident) / len(rows) if rows else None,
            "truth_metrics": None,
            "interpretation": "Unadjudicated uncertain labels are excluded from semantic accuracy, F1, Brier and log loss. High confidence is descriptive only."}


def capture_artifact(path, backends, report_rows, summaries, task):
    artifact = json.loads(path.read_text(encoding="utf-8"))
    by_backend = {}
    for backend in backends:
        rows = [row for row in report_rows if row.backend_name == backend.name()]
        by_backend[backend.name()] = {"summary": summaries[backend.name()],
                                     "version": backend.version(),
                                     "responses": backend.responses,
                                     "results": [row.to_dict() for row in rows]}
        if task == "entity_resolution":
            by_backend[backend.name()]["uncertain_diagnostics"] = uncertain_diagnostics(rows)
    return {"fixture_manifest": artifact["manifest"], "n_examples": artifact["n_examples"],
            "arms": by_backend}


def render_markdown(result):
    lines = ["# Original fixture diagnostics", "",
             "These hand-curated development examples test the repaired legacy harness. They are not official SciFact data or held-out biomedical validation. The identity model was trained on bibliographic records; names, organizations, proteins, and compounds here are outside that training distribution.", "",
             "## Relation support: 50 examples", "",
             "| Arm | Accuracy | Macro-F1 | Sum Brier | Errors | Execution |",
             "|---|---:|---:|---:|---:|---|"]
    for task in ("relation_support", "entity_resolution"):
        if task == "entity_resolution":
            lines.extend(["", "## Entity resolution: 88 binary-labeled + 12 uncertain examples", "",
                          "Only the 88 same/different labels enter semantic metrics. The 12 uncertain cases receive no correctness credit.", "",
                          "| Arm | Accuracy | Macro-F1 | Sum Brier | Errors | Execution |",
                          "|---|---:|---:|---:|---:|---|"])
        for name, arm in result[task]["arms"].items():
            row = arm["summary"]
            lines.append(f"| {name} | {row['accuracy']:.4f} | {row['macro_f1']:.4f} | {row['brier_score']:.4f} | {row['n_errors']} | {row['execution_modes']} |")
    lines.extend(["", "## Uncertain ER predictions: descriptive only", "",
                  "| Arm | Predict same | Predict different | Confidence ≥ 0.9 / successful responses |", "|---|---:|---:|---:|"])
    for name, arm in result["entity_resolution"]["arms"].items():
        row = arm["uncertain_diagnostics"]
        lines.append(f"| {name} | {row['predictions'].get('same', 0)} | {row['predictions'].get('different', 0)} | {row['high_confidence_count']} / {row['successful_responses']} |")
    lines.extend(["", "Brier is the sum over all classes (range 0–2), including both classes for ER; log loss clips gold probabilities at 1e-15. Constant and deterministic lexical rules use point-mass encodings, so their confidence of 1 is not a calibration claim. Lexical logistic probabilities are fitted only on DBLP training pairs and are not assumed calibrated on these fixtures.", "",
                  "NLI receives the full supplied passages and actual claim. ER receives both mentions plus supplied context through the repaired benchmark. Every response records mode, backend version, errors, input serialization, and neural raw logits where available. Models run locally with zero API calls; observed wall time is recorded, and zero API fees does not imply zero compute cost.", "",
                  "Constant SUPPORTS, NOT_ENOUGH_INFO, and same controls are predeclared descriptive baselines, not chosen by optimizing fixture outcomes. NOT_ENOUGH_INFO and same happen to be the fixture majority labels. The shallow relation lexical rule uses a fixed 0.6 content-word overlap threshold and a four-word negation check.", "",
                  "Do not subtract historical headline accuracies from these results: interfaces, labels, error handling, inputs, and models changed. These examples have been used for development, include unadjudicated labels, and do not establish improved scientific generalization.", "",
                  "Reproduce: `.venv\\Scripts\\python.exe -m pgc.experiments.run_fixture_diagnostics`.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path, default=ROOT / "results/research/fixture_diagnostics.json")
    args = parser.parse_args()
    import torch
    from sklearn.linear_model import LogisticRegression
    torch.set_num_threads(2)
    started = perf_counter()
    fixture_relation, fixture_er = load_scifact_50(), load_entity_resolution_100()
    if len(fixture_relation) != 50 or len(fixture_er) != 100 or sum(row.gold_label == "uncertain" for row in fixture_er) != 12:
        raise ValueError("The original fixture sizes/uncertain-label counts changed; review the protocol")
    result = {"manifest": {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "purpose": "development/OOD fixture diagnostics through repaired original harness entrypoints",
                "seed": SEED, "api_calls": 0, "api_fees_usd": 0,
                "python": platform.python_version(), "packages": {name: importlib.metadata.version(name)
                    for name in ("torch", "transformers", "scikit-learn", "numpy")},
                "device": args.device, "gpu_name": torch.cuda.get_device_name() if args.device.startswith("cuda") else None,
                "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "source_sha256": {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in sorted((ROOT / "pgc").rglob("*.py"))},
                "nli_model": MODEL, "nli_revision": REVISION,
                "er_checkpoint": ".cache/models/er-full-context",
                "evaluation_tuning": "None; no model fitting, threshold selection, or calibration on fixture labels.",
                "limits": ["Curated development fixtures, not official SciFact claims or untouched evaluation data.",
                           "Bibliographic ER model applied outside its training domain; no biomedical transfer claim.",
                           "Uncertain ER gold excluded from all semantic metrics; confidence is descriptive only.",
                           "Historical invalid results are not used as a model-improvement baseline."]}}
    with tempfile.TemporaryDirectory(prefix="pgc-fixture-diagnostics-") as temporary:
        destination = Path(temporary)
        nli = SpecialistNLIBackend(MODEL, revision=REVISION, device=args.device, max_length=512)
        if not nli.available or nli.execution_mode != "real":
            raise RuntimeError(nli.load_error or "Pinned real NLI checkpoint required")
        relation_backends = [RecordingBackend(backend) for backend in (
            nli,
            constant_backend("relation_support", RELATION_LABELS, "SUPPORTS"),
            constant_backend("relation_support", RELATION_LABELS, "NOT_ENOUGH_INFO"),
            FunctionalBackend("lexical-overlap-negation", "relation_support", RELATION_LABELS,
                              lambda payload: point_mass(relation_lexical_label(payload), RELATION_LABELS),
                              {"overlap_threshold": 0.6, "negation_words": ["no", "not", "neither", "without"],
                               "fit_split": None, "probability_semantics": "Point mass encoding of fixed deterministic rule; not calibrated confidence."}),
        )]
        report, summaries = run_relation_support_benchmark(backends=relation_backends, examples=fixture_relation,
            output_path=destination / "relation.json", seed=SEED,
            manifest={"purpose": result["manifest"]["purpose"], "model_revision": REVISION})
        result["relation_support"] = capture_artifact(destination / "relation.json", relation_backends,
                                                     report.results, summaries, "relation_support")
        del relation_backends, nli, report
        gc.collect()
        if args.device.startswith("cuda"):
            torch.cuda.empty_cache()

        splits, data_manifest = entity_resolution()
        lexical = LogisticRegression(C=1.0, random_state=SEED).fit(
            [[title_similarity(row)] for row in splits["train"]],
            [int(row["gold_label"] == "same") for row in splits["train"]])
        positive_index = list(lexical.classes_).index(1)

        def lexical_probability(payload):
            similarity = SequenceMatcher(None, payload["mention_1"].lower(), payload["mention_2"].lower()).ratio()
            probability = float(lexical.predict_proba([[similarity]])[0][positive_index])
            return {"same": probability, "different": 1 - probability}

        er = SpecialistERBackend(str(ROOT / ".cache/models/er-full-context"), device=args.device, max_length=256)
        if not er.available or er.execution_mode != "real":
            raise RuntimeError(er.load_error or "Trained real identity checkpoint required")
        lexical_metadata = {"fit_split": "DBLP-ACM training only", "training_rows": len(splits["train"]),
            "training_data_sha256": digest(splits["train"]), "training_row_ids_sha256": data_manifest["split_summary"]["train"]["row_ids_sha256"],
            "feature": "SequenceMatcher ratio of lowercased training titles / fixture mentions",
            "coefficients": lexical.coef_.tolist(), "intercept": lexical.intercept_.tolist(),
            "classes": lexical.classes_.tolist(), "calibration_claim": "No calibration guarantee under domain shift"}
        result["manifest"]["lexical_training"] = lexical_metadata
        er_backends = [RecordingBackend(backend) for backend in (
            er,
            constant_backend("entity_resolution", ER_LABELS, "same"),
            FunctionalBackend("normalized-exact", "entity_resolution", ER_LABELS,
                lambda payload: point_mass("same" if normalize_mention(payload["mention_1"]) == normalize_mention(payload["mention_2"]) else "different", ER_LABELS),
                {"normalization": "Unicode NFKC, casefold, retain alphanumeric characters", "fit_split": None,
                 "probability_semantics": "Point mass encoding of a deterministic identity heuristic, not calibrated confidence."}),
            FunctionalBackend("dblp-train-lexical-logistic", "entity_resolution", ER_LABELS, lexical_probability, lexical_metadata),
        )]
        report, summaries = run_entity_resolution_benchmark(backends=er_backends, examples=fixture_er,
            output_path=destination / "er.json", seed=SEED,
            manifest={"purpose": result["manifest"]["purpose"], "lexical_training": lexical_metadata})
        result["entity_resolution"] = capture_artifact(destination / "er.json", er_backends,
                                                      report["results"], summaries, "entity_resolution")
        del er_backends, er, report
        gc.collect()
        if args.device.startswith("cuda"):
            torch.cuda.empty_cache()
    result["manifest"]["measured_total_wall_seconds"] = perf_counter() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    markdown = args.output.with_name("FIXTURE_DIAGNOSTICS.md")
    markdown.write_text(render_markdown(result), encoding="utf-8")
    print(f"Saved {args.output} and {markdown}; GPU models released.", flush=True)


if __name__ == "__main__":
    main()
