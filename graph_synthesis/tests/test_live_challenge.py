import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reproduction"))
from pgc.decision.jev_real import JevAPIError
from graph_synthesis.run_challenge_live import run


class LiveChallengeJournalTests(unittest.TestCase):
    def test_authentication_failure_is_journaled_and_stops_remaining_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"TYPESAFE_API_KEY": "fake-test-only"}):
            output = Path(temp) / "run"
            with patch("pgc.decision.jev_real.JevRealBackend.send_payload",
                       side_effect=JevAPIError("HTTP 401", status_code=401, raw_response={"error": "denied"})) as send:
                run(output)
            self.assertEqual(send.call_count, 1)
            report = json.loads((output / "evaluation.json").read_text())
            self.assertEqual(report["overall"]["n"], 48)
            self.assertEqual(report["overall"]["statuses"], {"ERROR": 1, "MISSING": 47})
            self.assertNotIn("fake-test-only", "".join(p.read_text() for p in output.iterdir()))
            raw = json.loads((output / "raw.jsonl").read_text())
            self.assertEqual(set(raw["request"]), {"state", "questions", "model"})
            self.assertTrue(json.loads((output / "execution-audit.json").read_text())["request_response_hashes_verified"])

    def test_existing_run_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"TYPESAFE_API_KEY": "fake-test-only"}):
            with self.assertRaises(FileExistsError):
                run(Path(temp))
