"""Dataset acquisition rejects bad bytes before invoking frozen preparation."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from graph_synthesis import datasets


class DatasetAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.destination = Path(self.directory.name) / "sources"
        self.target = self.destination / datasets.SCIFACT_NAME
        self.content = b"original source fixture"
        record = {"name": datasets.SCIFACT_NAME, "bytes": len(self.content),
                  "sha256": hashlib.sha256(self.content).hexdigest()}
        self.enterContext(patch.object(datasets, "SCIFACT_RECORD", record))
        self.stdout = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def test_empty_cache_prefers_versioned_object_without_requesting_latest(self):
        with patch.object(datasets, "urlopen", return_value=io.BytesIO(self.content)) as fetch:
            datasets.ensure_scifact(self.destination)
        self.assertEqual(fetch.call_args.args[0].full_url, datasets.SCIFACT_VERSION_URL)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(self.target.read_bytes(), self.content)
        self.assertIn(datasets.SCIFACT_VERSION_URL, self.stdout.getvalue())

    def test_unavailable_preferred_source_uses_verified_fallback(self):
        with patch.object(datasets, "urlopen", side_effect=[URLError("unavailable"), io.BytesIO(self.content)]) as fetch:
            datasets.ensure_scifact(self.destination)
        self.assertEqual([call.args[0].full_url for call in fetch.call_args_list],
                         list(datasets.SCIFACT_SOURCES))
        self.assertEqual(self.target.read_bytes(), self.content)
        self.assertIn("unavailable", self.stderr.getvalue())

    def test_changed_source_is_reported_and_only_verified_fallback_is_installed(self):
        with patch.object(datasets, "urlopen", side_effect=[io.BytesIO(b"wrong"), io.BytesIO(self.content)]):
            datasets.ensure_scifact(self.destination)
        self.assertEqual(self.target.read_bytes(), self.content)
        self.assertIn(hashlib.sha256(b"wrong").hexdigest(), self.stderr.getvalue())
        self.assertIn(datasets.SCIFACT_VERSION_URL, self.stderr.getvalue())

    def test_all_mismatches_fail_closed_with_expected_and_observed_digests(self):
        bad = b"wrong"
        with patch.object(datasets, "urlopen", side_effect=[io.BytesIO(bad), io.BytesIO(bad)]):
            with self.assertRaises(ValueError) as raised:
                datasets.ensure_scifact(self.destination)
        message = str(raised.exception)
        self.assertIn(datasets.SCIFACT_VERSION_URL, message)
        self.assertIn(datasets.SCIFACT_LATEST_URL, message)
        self.assertIn(hashlib.sha256(self.content).hexdigest(), message)
        self.assertIn(hashlib.sha256(bad).hexdigest(), message)
        self.assertIn("--scifact-archive PATH", message)
        self.assertFalse(self.target.exists())

    def test_all_unavailable_sources_provide_local_recovery(self):
        with patch.object(datasets, "urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(ValueError, "--scifact-archive PATH"):
                datasets.ensure_scifact(self.destination)
        self.assertFalse(self.target.exists())

    def test_existing_verified_archive_requires_no_network(self):
        self.destination.mkdir()
        self.target.write_bytes(self.content)
        with patch.object(datasets, "urlopen", side_effect=AssertionError("network attempted")):
            datasets.ensure_scifact(self.destination)
        self.assertEqual(self.target.read_bytes(), self.content)

    def test_corrupt_cached_archive_is_preserved_and_reported(self):
        self.destination.mkdir()
        self.target.write_bytes(b"corrupt")
        with patch.object(datasets, "urlopen", side_effect=AssertionError("network attempted")):
            with self.assertRaisesRegex(ValueError, "observed 7 bytes"):
                datasets.ensure_scifact(self.destination)
        self.assertEqual(self.target.read_bytes(), b"corrupt")

    def test_local_archive_recovery_checks_before_replacing_cache(self):
        self.destination.mkdir()
        self.target.write_bytes(b"corrupt")
        local = Path(self.directory.name) / "supplied.tar.gz"
        local.write_bytes(b"wrong")
        with patch.object(datasets, "urlopen", side_effect=AssertionError("network attempted")):
            with self.assertRaises(ValueError):
                datasets.ensure_scifact(self.destination, local)
            self.assertEqual(self.target.read_bytes(), b"corrupt")
            local.write_bytes(self.content)
            datasets.ensure_scifact(self.destination, local)
        self.assertEqual(self.target.read_bytes(), self.content)

    def test_write_failure_removes_temporary_download(self):
        with patch.object(Path, "replace", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                datasets.install_scifact(self.content, self.target)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_check_only_delegates_to_frozen_six_file_verifier(self):
        with patch.object(datasets, "ensure_scifact", side_effect=AssertionError("acquisition attempted")):
            with patch.object(datasets.subprocess, "run") as run:
                run.return_value.returncode = 7
                self.assertEqual(datasets.main(["--check"]), 7)
        self.assertEqual(run.call_args.args[0][-2:],
                         [str(datasets.REPOSITORY / "scripts/download_datasets.py"), "--check"])


if __name__ == "__main__":
    unittest.main()
