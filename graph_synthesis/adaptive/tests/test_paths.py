"""Cross-platform provenance must use canonical repository-relative paths."""
from pathlib import PurePosixPath, PureWindowsPath
import unittest
from graph_synthesis.adaptive.run import repository_key


class ProvenancePathTests(unittest.TestCase):
    def test_windows_uses_forward_slashes(self):
        root = PureWindowsPath("D:/a/paper-package/paper-package")
        self.assertEqual(repository_key(root / "experiments/study/calls.jsonl", root),
                         "experiments/study/calls.jsonl")

    def test_posix_matches_windows(self):
        root = PurePosixPath("/home/runner/work/paper-package/paper-package")
        self.assertEqual(repository_key(root / "experiments/study/calls.jsonl", root),
                         "experiments/study/calls.jsonl")


if __name__ == "__main__":
    unittest.main()
