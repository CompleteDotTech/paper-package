"""Offline scientific-data controls using synthetic source-format fixtures."""

import io
import json
import tarfile
import unittest
from unittest.mock import patch

from pgc.experiments import research_data as data


def publication(name):
    return f"COL title VAL Publication {name} COL authors VAL Author {name} COL venue VAL Venue COL year VAL 2000"


def serialized_pairs(pairs):
    return "\n".join(f"{publication(left)}\t{publication(right)}\t{label}" for left, right, label in pairs).encode()


def download_fixture(contents):
    def download(url, filename):
        content = contents[filename]
        return content, {"url": url, "sha256": data.digest(content), "bytes": len(content),
                         "local_file": f"fixture/{filename}"}
    return download


def load_entity_fixture(train, valid=(), test=(), fixed_partition=None):
    contents = {f"dblp-acm-{name}.txt": serialized_pairs(pairs)
                for name, pairs in (("train", train), ("valid", valid), ("test", test))}
    with patch.object(data, "download", side_effect=download_fixture(contents)):
        if fixed_partition is not None:
            with patch.object(data, "partition", return_value=fixed_partition):
                return data.entity_resolution()
        return data.entity_resolution()


def scifact_archive(corpus, train, dev):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, rows in (("corpus.jsonl", corpus), ("claims_train.jsonl", train), ("claims_dev.jsonl", dev)):
            content = "\n".join(json.dumps(row) for row in rows).encode()
            info = tarfile.TarInfo("data/" + name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class ResearchDataTests(unittest.TestCase):
    def test_entity_splits_keep_positive_alias_families_together(self):
        pairs = []
        for index in range(180):
            pairs.extend(((f"A{index}", f"B{index}", 1), (f"B{index}", f"C{index}", 1),
                          (f"A{index}", f"B{(index + 1) % 180}", 0)))
        splits, manifest = load_entity_fixture(pairs)
        self.assertTrue(all(splits.values()))
        used = set()
        for name, rows in splits.items():
            identities = {identity for row in rows for identity in row["identity_groups"]}
            self.assertFalse(used & identities)
            used.update(identities)
            if name != "train":
                flattened = [identity for row in rows for identity in set(row["identity_groups"])]
                self.assertEqual(len(flattened), len(set(flattened)))
        self.assertGreater(manifest["discarded_cross_split_pairs"], 0)
        self.assertEqual(manifest["splits_sha256"], data.digest(splits))

    def test_conflicting_pairs_quarantine_all_incident_records(self):
        splits, manifest = load_entity_fixture(
            [("A", "B", 1), ("A", "C", 0), ("D", "E", 1)], [("A", "B", 0)], fixed_partition="train")
        self.assertEqual(len(splits["train"]), 1)
        self.assertEqual(splits["train"][0]["record_1"]["title"], "Publication D")
        self.assertEqual(manifest["ambiguous_record_quarantine"]["conflicting_serialized_pairs"], 1)

    def test_ambiguity_quarantine_does_not_sever_a_positive_alias_family(self):
        # C/E and D/F are aliases reached through ambiguous A/B. Removing only
        # A/B would incorrectly turn one uncertain identity family into two.
        train = [("A", "B", 1), ("A", "C", 1), ("B", "D", 1),
                 ("C", "E", 1), ("D", "F", 1), ("safe1", "safe2", 1)]
        splits, _ = load_entity_fixture(train, [("A", "B", 0)], fixed_partition="train")
        remaining_titles = {row[key]["title"] for row in splits["train"] for key in ("record_1", "record_2")}
        self.assertEqual(remaining_titles, {"Publication safe1", "Publication safe2"})

    def test_negative_inside_positive_component_quarantines_entire_component(self):
        splits, manifest = load_entity_fixture(
            [("A", "B", 1), ("B", "C", 1), ("A", "C", 0), ("C", "D", 0), ("E", "F", 1)],
            fixed_partition="train")
        self.assertEqual(len(splits["train"]), 1)
        self.assertEqual(manifest["identity_consistency_quarantine"]["inconsistent_positive_components"], 1)

    def test_exact_repeated_pair_is_not_a_new_observation(self):
        splits, _ = load_entity_fixture([("A", "B", 1)], [("A", "B", 1)], [("A", "B", 1)], fixed_partition="train")
        self.assertEqual(len(splits["train"]), 1)

    def test_scifact_purges_whole_claim_for_duplicate_evaluation_abstract(self):
        corpus = [{"doc_id": index, "title": f"Document {index}", "abstract": abstract}
                  for index, abstract in ((1, ["Shared intro", "Shared result"]),
                                          (2, ["Other document on purged claim"]),
                                          (3, ["Training-only finding"]),
                                          (4, ["Training-only finding"]),
                                          (99, ["Shared intro", "Shared result"]))]
        train = [{"id": 1, "claim": "Purged claim", "cited_doc_ids": [1, 2], "evidence": {}},
                 {"id": 2, "claim": "Training claim one", "cited_doc_ids": [3], "evidence": {}},
                 {"id": 3, "claim": "Training claim two", "cited_doc_ids": [4], "evidence": {}}]
        dev = [{"id": 90, "claim": "Held-out claim", "cited_doc_ids": [99, 99],
                "evidence": {"99": [{"label": "SUPPORT", "sentences": [1]}]}}]
        content = scifact_archive(corpus, train, dev)
        with patch.object(data, "download", side_effect=download_fixture({"scifact-data.tar.gz": content})):
            splits, manifest = data.scifact()
        retained = splits["train"] + splits["calibration"]
        self.assertEqual({row["claim_id"] for row in retained}, {"2", "3"})
        self.assertEqual(len({row["group"] for row in retained}), 1)
        self.assertEqual(manifest["purged_training_claims"], 1)
        self.assertEqual(len(splits["evaluation"]), 1, "Repeated citations are not independent observations")
        self.assertEqual(splits["evaluation"][0]["gold_label"], "SUPPORTS")
        self.assertEqual(splits["evaluation"][0]["rationale_sentence_ids"], [1])

    def test_disjoint_assertion_detects_shared_group_even_if_row_ids_differ(self):
        with self.assertRaises(ValueError):
            data.assert_disjoint({"train": [{"id": "a", "group": "identity"}],
                                  "evaluation": [{"id": "b", "group": "identity"}]}, lambda row: [row["group"]])


if __name__ == "__main__":
    unittest.main()
