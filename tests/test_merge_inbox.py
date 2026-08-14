import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.merge_inbox import normalize, read_json, validate_batch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/merge_inbox.py"
PROCESSED = ROOT / "radar/inbox/processed"


class MergeInboxTest(unittest.TestCase):
    def test_historical_batch_normalizes_without_losing_evidence(self):
        path = PROCESSED / "historical-attendance-2026-08-14.json"
        candidates = validate_batch(read_json(path), path)
        self.assertEqual(len(candidates), 12)
        normalized, changes = normalize(candidates[0])
        self.assertIsNone(normalized["priority"])
        self.assertEqual(normalized["attendance"]["evidence"][0]["type"], "ticket_purchase")
        self.assertIn("category='Historical archive'", changes)

    def test_regional_batch_preserves_official_ticketing(self):
        path = PROCESSED / "regional-radar-2026-08-14.json"
        candidates = validate_batch(read_json(path), path)
        self.assertEqual(len(candidates), 3)
        ozone = candidates[1]
        self.assertEqual(ozone["tickets"]["official"]["minimum"], 45.76)
        self.assertIsNone(ozone["tickets"]["resale"]["minimum"])

    def test_deferred_batch_remains_unmerged_without_required_metadata(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--all", "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["added"], [])
        self.assertEqual(report["blocked"][0]["id"], "eddie-palmieri-2019-user-confirmed")


if __name__ == "__main__":
    unittest.main()
