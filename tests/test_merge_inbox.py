import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.merge_inbox import merge, normalize, read_json, validate_batch


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_events.py"
PROCESSED = ROOT / "radar/inbox/processed"
FIXTURES = ROOT / "tests/fixtures"


class MergeInboxTest(unittest.TestCase):
    def validate_modified_event(self, mutate):
        data = json.loads((ROOT / "radar/events.json").read_text())
        event = next(item for item in data["events"] if item["status"] == "considering")
        mutate(event)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(json.dumps(data))
            return subprocess.run([sys.executable, str(VALIDATOR), str(path)], capture_output=True, text=True)

    def test_complete_enrichment_rejects_bad_urls_and_missing_fields(self):
        def mutate(event):
            event["enrichment"] = {"status": "complete", "missing": []}
            event["links"] = {"official_event": "https://example.com/search?q=show", "official_tickets": "not-a-url"}
            event["recommended_listening"] = [{"title": "Test", "apple_music_url": "https://music.apple.com/us/search?term=test"}]
        result = self.validate_modified_event(mutate)
        self.assertNotEqual(result.returncode, 0)

    def test_pending_enrichment_is_explicit_and_valid(self):
        def mutate(event):
            event["enrichment"] = {"status": "pending", "missing": ["official_tickets", "apple_music"], "note": "Official tickets are not yet published; Apple Music match needs review."}
            event["links"] = {"official_event": "https://example.com/events/test", "official_tickets": None}
            event["recommended_listening"] = []
        result = self.validate_modified_event(mutate)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_non_exact_apple_music_urls(self):
        for url in ("https://music.apple.com/us/search?term=test", "https://example.com/album/test", "not-a-url"):
            def mutate(event, url=url):
                event["recommended_listening"] = [{"title": "Test", "apple_music_url": url}]
            result = self.validate_modified_event(mutate)
            self.assertNotEqual(result.returncode, 0, url)
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

    def test_mixed_batch_merges_valid_candidate_and_defers_incomplete_record(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "radar/events.json"
            curated = root / "radar/inbox/curated"
            processed = root / "radar/inbox/processed"
            curated.mkdir(parents=True)
            canonical.write_text(json.dumps({"schema_version": 3, "events": []}) + "\n")
            batch = curated / "mixed-curated-batch.json"
            shutil.copy2(FIXTURES / "mixed-curated-batch.json", batch)

            report = merge([batch], False, canonical, curated, processed)

            self.assertEqual(report["added"], ["fixture-valid-event-2099"])
            self.assertEqual(
                report["blocked"],
                [{
                    "id": "eddie-palmieri-2019-user-confirmed",
                    "batch": "test-mixed-curated-batch",
                    "reason": "missing dates.start",
                }],
            )
            merged = json.loads(canonical.read_text())
            self.assertEqual([event["id"] for event in merged["events"]], ["fixture-valid-event-2099"])
            self.assertTrue((processed / batch.name).exists())
            self.assertFalse(batch.exists())
            deferred = read_json(curated / "mixed-curated-batch-deferred.json")
            self.assertEqual(deferred["batch_id"], "test-mixed-curated-batch-deferred")
            self.assertEqual([event["id"] for event in deferred["events"]], ["eddie-palmieri-2019-user-confirmed"])


if __name__ == "__main__":
    unittest.main()
