"""Traceable public-data preparation; splits are fixed before model evaluation."""

from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
SCIFACT_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
DITTO_REVISION = "52985564a93fb11308439516d3e17a033d43ec8f"
DATA_ROOT = ROOT / ".cache" / "research-data"
EXPECTED_SHA256 = {
    "scifact-data.tar.gz": "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be",
    "dblp-acm-train.txt": "4f757d2d5dae4f7d7d118b796c683a232b4e11bf000e2012b64f8af95a981a4e",
    "dblp-acm-valid.txt": "b13444a2bf1a503ed558e782f42b247cf56e16e67be2e58d92d7435161299e2e",
    "dblp-acm-test.txt": "ded891e469b1d08e21269038c984dc761ae2fd5b142b00c46c30fce45adc6e68",
}


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def download(url, filename):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    path = DATA_ROOT / filename
    if not path.exists():
        with urlopen(Request(url, headers={"User-Agent": "pgc-research-reproduction/1"}), timeout=120) as response:
            content = response.read()
        path.write_bytes(content)
    content = path.read_bytes()
    if filename in EXPECTED_SHA256 and digest(content) != EXPECTED_SHA256[filename]:
        raise ValueError(f"Source bytes changed for {filename}; review the new data before changing the pinned hash")
    return content, {"url": url, "sha256": digest(content), "bytes": len(content), "local_file": str(path.relative_to(ROOT))}


class Components:
    def __init__(self):
        self.parent = {}

    def find(self, item):
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left, right):
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def partition(key, seed=20260917):
    bucket = int(digest([seed, key])[:8], 16) % 10
    return "train" if bucket < 6 else ("calibration" if bucket < 8 else "evaluation")


def scifact():
    archive, source = download(SCIFACT_URL, "scifact-data.tar.gz")
    members = {}
    wanted = {"corpus.jsonl", "claims_train.jsonl", "claims_dev.jsonl"}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile() and Path(member.name).name in wanted and "/cross_validation/" not in member.name:
                stream = tar.extractfile(member)
                members[Path(member.name).name] = [json.loads(line) for line in stream.read().decode("utf-8").splitlines() if line]
    if set(members) != wanted:
        raise ValueError("Unexpected SciFact archive layout")
    corpus = {str(row["doc_id"]): row for row in members["corpus.jsonl"]}

    def rows(claims):
        result = []
        for claim in claims:
            # Citations are metadata; selection never looks at evidence labels.
            for doc_id in sorted(set(map(str, claim["cited_doc_ids"]))):
                document = corpus[doc_id]
                annotations = claim["evidence"].get(doc_id, [])
                labels = {item["label"] for item in annotations}
                if len(labels) > 1:
                    raise ValueError("Conflicting document labels require adjudication")
                label = next(iter(labels)) if labels else "NOT_ENOUGH_INFO"
                label = {"SUPPORT": "SUPPORTS", "CONTRADICT": "REFUTES"}.get(label, label)
                if label not in {"SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"}:
                    raise ValueError(f"Unknown SciFact label {label}")
                rationale = sorted({i for item in annotations for i in item["sentences"]})
                result.append({
                    "id": f"scifact-{claim['id']}-{doc_id}", "claim_id": str(claim["id"]),
                    "document_id": doc_id, "claim": claim["claim"],
                    "evidence": list(document["abstract"]), "title": document["title"],
                    "gold_label": label, "rationale_sentence_ids": rationale,
                })
        return result

    training, evaluation = rows(members["claims_train.jsonl"]), rows(members["claims_dev.jsonl"])
    eval_docs = {row["document_id"] for row in evaluation}
    eval_texts = {digest(row["evidence"]) for row in evaluation}
    # Purge whole claims if any cited document or abstract overlaps evaluation.
    excluded_claims = {row["claim_id"] for row in training
                       if row["document_id"] in eval_docs or digest(row["evidence"]) in eval_texts}
    training = [row for row in training if row["claim_id"] not in excluded_claims]
    groups = Components()
    for row in training + evaluation:
        groups.union("claim:" + row["claim_id"], "doc:" + row["document_id"])
        groups.union("doc:" + row["document_id"], "text:" + digest(row["evidence"]))
    splits = {"train": [], "calibration": [], "evaluation": evaluation}
    for row in training:
        group = groups.find("claim:" + row["claim_id"])
        destination = "calibration" if int(digest(group)[:8], 16) % 4 == 0 else "train"
        splits[destination].append(row)
    for split in splits.values():
        for row in split:
            row["group"] = groups.find("claim:" + row["claim_id"])
        split.sort(key=lambda row: row["id"])
    assert_disjoint(splits, lambda row: [row["document_id"], digest(row["evidence"])])
    return splits, {
        "dataset": "SciFact original release", "source": source,
        "task": "classification of supplied cited abstracts; not open-corpus retrieval or leaderboard evaluation",
        "evaluation": "official development claims; training/calibration purge overlapping documents and duplicate abstracts",
        "purged_training_claims": len(excluded_claims),
        "split_summary": summary(splits), "splits_sha256": digest(splits),
        "group_unit": "connected claim/document/duplicate-abstract component",
    }


def parse_attributes(text):
    attributes = {}
    for part in re.split(r"\bCOL\s+", text):
        if " VAL " in part:
            key, value = part.split(" VAL ", 1)
            attributes[key.strip()] = value.strip()
    return attributes or {"title": text.strip()}


def entity_resolution():
    rows, sources, seen = [], [], {}
    ambiguous_records, conflicting_pairs = set(), set()
    original_identity_groups = Components()
    for split in ("train", "valid", "test"):
        url = f"https://raw.githubusercontent.com/megagonlabs/ditto/{DITTO_REVISION}/data/er_magellan/Structured/DBLP-ACM/{split}.txt"
        content, source = download(url, f"dblp-acm-{split}.txt")
        sources.append(source)
        for line_no, line in enumerate(content.decode("utf-8").splitlines(), 1):
            parts = line.split("\t")
            if len(parts) != 3 or parts[2] not in {"0", "1"}:
                raise ValueError(f"Invalid entity pair at {split}:{line_no}")
            left, right = map(parse_attributes, parts[:2])
            pair = (digest(left), digest(right))
            label = "same" if parts[2] == "1" else "different"
            for entity in pair:
                original_identity_groups.find(entity)
            if label == "same":
                original_identity_groups.union(*pair)
            if pair in seen:
                if seen[pair] != label:
                    conflicting_pairs.add(pair)
                    ambiguous_records.update(pair)
                continue
            seen[pair] = label
            rows.append({"id": f"dblp-acm-{split}-{line_no}", "record_1": left, "record_2": right,
                         "entity_1": pair[0], "entity_2": pair[1], "gold_label": label,
                         "source_split": split, "source_line": line_no})
    original_unique_pairs = len(rows)
    ambiguous_components = {original_identity_groups.find(entity) for entity in ambiguous_records}
    ambiguous_records.update(entity for entity in original_identity_groups.parent
                             if original_identity_groups.find(entity) in ambiguous_components)
    rows = [row for row in rows if row["entity_1"] not in ambiguous_records and row["entity_2"] not in ambiguous_records]
    quarantined_ambiguous_pairs = original_unique_pairs - len(rows)
    groups = Components()
    for row in rows:
        for key in ("entity_1", "entity_2"):
            groups.find(row[key])
        if row["gold_label"] == "same":
            groups.union(row["entity_1"], row["entity_2"])
    inconsistent_groups = {groups.find(row["entity_1"]) for row in rows
                           if row["gold_label"] == "different" and groups.find(row["entity_1"]) == groups.find(row["entity_2"])}
    coherent_rows = [row for row in rows if not {groups.find(row["entity_1"]), groups.find(row["entity_2"])} & inconsistent_groups]
    quarantined_inconsistent_pairs = len(rows) - len(coherent_rows)
    rows = coherent_rows
    splits = {key: [] for key in ("train", "calibration", "evaluation")}
    discarded_cross_split = 0
    for row in rows:
        group_a, group_b = groups.find(row["entity_1"]), groups.find(row["entity_2"])
        split_a, split_b = partition(group_a), partition(group_b)
        if split_a != split_b:
            discarded_cross_split += 1
            continue
        row["identity_groups"] = [group_a, group_b]
        splits[split_a].append(row)
    # Calibration/evaluation use a deterministic maximal matching of identity groups.
    # This sacrifices sample count to avoid dependent/repeated entities within metrics.
    discarded_reused_identity = {}
    for split_name in ("calibration", "evaluation"):
        selected, used = [], set()
        ordered = sorted(splits[split_name], key=lambda row: digest(row["id"]))
        for row in ordered:
            identities = set(row["identity_groups"])
            if identities & used:
                continue
            selected.append(row)
            used.update(identities)
        discarded_reused_identity[split_name] = len(ordered) - len(selected)
        splits[split_name] = selected
    for split in splits.values():
        for row in split:
            row["group"] = row["id"]
        split.sort(key=lambda row: row["id"])
    assert_disjoint(splits, lambda row: row["identity_groups"])
    # Quarantine must not hide aliases connected through removed records.
    assert_disjoint(splits, lambda row: [original_identity_groups.find(row[key]) for key in ("entity_1", "entity_2")])
    for name in ("calibration", "evaluation"):
        used = set()
        for row in splits[name]:
            identities = {original_identity_groups.find(row[key]) for key in ("entity_1", "entity_2")}
            if used & identities:
                raise ValueError("Quarantine would conceal a repeated held-out identity; revise grouping")
            used.update(identities)
    return splits, {
        "dataset": "DBLP-ACM structured identity pairs, Ditto serialized ER-Magellan data",
        "sources": sources, "source_revision": DITTO_REVISION,
        "task": "bibliographic identity matching; not a biomedical generalization test",
        "split_policy": "positive identity components hashed 60/20/20; cross-split negatives dropped; held-out identity-disjoint maximal matching",
        "discarded_cross_split_pairs": discarded_cross_split,
        "discarded_reused_identity_pairs": discarded_reused_identity,
        "ambiguous_record_quarantine": {"conflicting_serialized_pairs": len(conflicting_pairs),
                                        "record_hashes": sorted(ambiguous_records),
                                        "excluded_pairs": quarantined_ambiguous_pairs},
        "identity_consistency_quarantine": {"inconsistent_positive_components": len(inconsistent_groups),
                                           "excluded_pairs": quarantined_inconsistent_pairs},
        "grouping_uses_labels": "positive labels define split groups only, never model features",
        "split_summary": summary(splits), "splits_sha256": digest(splits),
        "group_unit": "disjoint underlying identity groups in calibration/evaluation",
    }


def assert_disjoint(splits, keys):
    seen = set()
    for name, rows in splits.items():
        values = {value for row in rows for value in keys(row)}
        if seen & values:
            raise ValueError(f"Entity/document leakage into {name}")
        seen.update(values)


def summary(splits):
    return {name: {"rows": len(rows), "labels": dict(Counter(row["gold_label"] for row in rows)),
                   "groups": len({row["group"] for row in rows}),
                   "row_ids_sha256": digest([row["id"] for row in rows])}
            for name, rows in splits.items()}


if __name__ == "__main__":
    destination = ROOT / "results" / "research"
    destination.mkdir(parents=True, exist_ok=True)
    manifests = {}
    for name, loader in (("scifact", scifact), ("entity_resolution", entity_resolution)):
        splits, manifest = loader()
        (DATA_ROOT / f"{name}-prepared.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
        manifests[name] = manifest
        print(name, json.dumps(manifest["split_summary"]), flush=True)
    (destination / "data_manifest.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
