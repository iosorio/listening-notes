"""Regressions for the September 30 discovery and intake outage."""

import copy
import json
import subprocess
import unittest
from pathlib import Path

from scripts.record_radar_run import append_run
from scripts.merge_inbox import merge
from scripts.validate_radar_discovery import DiscoveryValidationError, validate_runs
from scripts.verify_discovery_provenance_backfill import (
    require_published_intake, replay_processed_intake, verify,
)
from tests.test_radar_discovery import run


ROOT = Path(__file__).resolve().parents[1]
INCIDENT_BASE = "b5c793a846e38bf2a2adb54dd957ef6a8ac67bce"


class HeartbeatRecoveryTest(unittest.TestCase):
    def test_success_writer_supplies_null_without_mutating_input(self):
        record = run()
        del record["error_summary"]
        empty = {"schema_version": 1, "runs": []}
        result = append_run(empty, record)
        self.assertIsNone(result["runs"][0]["error_summary"])
        self.assertNotIn("error_summary", record)
        self.assertEqual(empty["runs"], [])
        self.assertEqual(append_run(result, record), result)

    def test_partial_and_error_writer_cannot_invent_explanations(self):
        for outcome in ("partial", "error"):
            record = run(outcome=outcome)
            del record["error_summary"]
            with self.subTest(outcome=outcome), self.assertRaises(DiscoveryValidationError):
                append_run({"schema_version": 1, "runs": []}, record)

    def test_writer_rejects_rewriting_a_run(self):
        record = run()
        existing = {"schema_version": 1, "runs": [record]}
        edited = dict(record, sources_checked=100)
        with self.assertRaisesRegex(DiscoveryValidationError, "immutable"):
            append_run(existing, edited)

    def test_repair_preserves_every_recorded_measurement(self):
        original = json.loads(subprocess.check_output(
            ["git", "show", f"{INCIDENT_BASE}:radar/discovery/runs.json"], cwd=ROOT,
        ))
        expected = copy.deepcopy(original)
        repaired = []
        for record in expected["runs"]:
            if "error_summary" not in record and record["status"] == "success":
                record["error_summary"] = None
                repaired.append(record["run_id"])
        self.assertEqual(len(repaired), 3)
        current = json.loads((ROOT / "radar/discovery/runs.json").read_text())
        validate_runs(current)
        self.assertEqual(current["runs"][:len(expected["runs"])], expected["runs"])


class PublishedDiscoveryEvolutionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT / "radar/inbox/review/discovery-provenance-backfill-2026-09-29.json").read_text())
        cls.baseline = json.loads(subprocess.check_output(
            ["git", "show", f"{manifest['source_ref']}:radar/events.json"], cwd=ROOT,
        ))
        by_id = {event["id"]: event for event in cls.baseline["events"]}
        for change in manifest["changes"]:
            by_id[change["event_id"]]["discovered_at"] = change["after"]
        cls.current = json.loads((ROOT / "radar/events.json").read_text())
        cls.batches = [p for p in sorted((ROOT / "radar/inbox/processed").glob("*.json"))
                       if json.loads(p.read_text()).get("batch_version") == 2]

    def test_published_catalog_can_grow_beyond_historical_snapshot(self):
        result = verify()
        self.assertGreater(result["processed_intake"]["events_added"], 0)
        self.assertNotEqual(result["target_sha256"], result["current_sha256"])

    def test_pending_v2_intake_is_publishable(self):
        paths = sorted((ROOT / "radar/inbox/curated").glob("*-intake.json"))
        report = merge(paths, True)
        for key in ("conflicts", "semantic_conflicts", "blocked"):
            self.assertEqual(report[key], [], key)

    def test_unrecorded_edits_deletions_and_additions_are_rejected(self):
        for mutation in ("edit", "delete", "add", "provenance"):
            current = copy.deepcopy(self.current)
            if mutation == "edit":
                current["events"][0]["artist"] = "Unrecorded change"
            elif mutation == "delete":
                current["events"].pop(0)
            elif mutation == "add":
                extra = copy.deepcopy(current["events"][0])
                extra["id"] = "unrecorded-addition-2099"
                current["events"].append(extra)
            else:
                event = next(e for e in current["events"] if "published_at" in e)
                event["discovered_at"] = "2026-09-01T12:00:00Z"
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "does not match"):
                replay_processed_intake(self.baseline, current, self.batches)

    def test_processed_source_cannot_be_rewritten_or_fabricated(self):
        source = self.batches[0]
        require_published_intake(source.name, source.read_bytes())
        with self.assertRaisesRegex(ValueError, "published curated source"):
            require_published_intake(source.name, source.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "published curated source"):
            require_published_intake("unpublished-intake.json", source.read_bytes())


if __name__ == "__main__":
    unittest.main()
