import copy
import json
import shutil
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.enrichment_common import EnrichmentError, validate_patch_shape
from scripts.validate_radar_discovery import (
    DiscoveryValidationError,
    derive_health,
    validate_runs,
    validate_status,
)


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_EVENTS = ROOT / "scripts/validate_events.py"
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


def status(enabled=True):
    return {
        "schema_version": 1,
        "enabled": enabled,
        "cadence": "hourly",
        "expected_max_silence_hours": 12,
        "changed_at": "2026-09-29T12:00:00-04:00",
        "changed_by": "Test",
        "reason": "Test state.",
        "state_history": [{
            "enabled": enabled,
            "changed_at": "2026-09-29T12:00:00-04:00",
            "changed_by": "Test",
            "reason": "Test state.",
        }],
    }


def run(run_id="run-1", started="2026-09-29T12:00:00-04:00", completed="2026-09-29T12:10:00-04:00", outcome="success", published=0):
    return {
        "run_id": run_id,
        "started_at": started,
        "completed_at": completed,
        "trigger": "scheduled",
        "status": outcome,
        "executor": "test-executor",
        "threads_checked": ["tokyo_kanto", "us_corridor"],
        "sources_checked": 34,
        "candidates_reviewed": 7,
        "events_admitted": published,
        "events_published": published,
        "material_updates": 0,
        "error_summary": None if outcome == "success" else "A source family was unavailable.",
    }


class RadarDiscoveryLedgerTest(unittest.TestCase):
    def test_successful_zero_result_and_published_run_are_valid(self):
        payload = {"schema_version": 1, "runs": [run(), run("run-2", "2026-09-29T13:00:00-04:00", "2026-09-29T13:12:00-04:00", published=2)]}
        self.assertEqual(validate_runs(payload)[0]["events_published"], 0)
        self.assertEqual(validate_runs(payload)[1]["events_published"], 2)

    def test_partial_and_error_runs_require_summaries(self):
        self.assertEqual(validate_runs({"schema_version": 1, "runs": [run(outcome="partial")]})[0]["status"], "partial")
        self.assertEqual(validate_runs({"schema_version": 1, "runs": [run(outcome="error")]})[0]["status"], "error")
        malformed = run(outcome="error")
        malformed["error_summary"] = None
        with self.assertRaises(DiscoveryValidationError):
            validate_runs({"schema_version": 1, "runs": [malformed]})

    def test_malformed_timestamp_status_and_order_are_rejected(self):
        malformed = run()
        malformed["started_at"] = "2026-09-29"
        with self.assertRaises(DiscoveryValidationError):
            validate_runs({"schema_version": 1, "runs": [malformed]})
        malformed = run()
        malformed["status"] = "okay"
        with self.assertRaises(DiscoveryValidationError):
            validate_runs({"schema_version": 1, "runs": [malformed]})
        with self.assertRaises(DiscoveryValidationError):
            validate_runs({"schema_version": 1, "runs": [run("later", "2026-09-29T13:00:00-04:00", "2026-09-29T13:01:00-04:00"), run("earlier")]})

    def test_health_states_and_later_success_clears_error(self):
        desired = validate_status(status())
        recent = [run()]
        self.assertEqual(derive_health(desired, recent, datetime.fromisoformat("2026-09-29T13:00:00-04:00"))["state"], "healthy")
        self.assertEqual(derive_health(desired, recent, datetime.fromisoformat("2026-09-30T13:00:00-04:00"))["state"], "stale")
        self.assertEqual(derive_health(validate_status(status(False)), recent, datetime.fromisoformat("2026-09-30T13:00:00-04:00"))["state"], "off")
        failed = recent + [run("failed", "2026-09-29T14:00:00-04:00", "2026-09-29T14:05:00-04:00", "error")]
        self.assertEqual(derive_health(desired, failed, datetime.fromisoformat("2026-09-29T15:00:00-04:00"))["state"], "error")
        recovered = failed + [run("recovered", "2026-09-29T15:30:00-04:00", "2026-09-29T15:40:00-04:00")]
        self.assertEqual(derive_health(desired, recovered, datetime.fromisoformat("2026-09-29T16:00:00-04:00"))["state"], "healthy")


class DiscoveryProvenanceTest(unittest.TestCase):
    def test_historical_records_without_discovery_remain_valid(self):
        data = json.loads((ROOT / "radar/events.json").read_text())
        event = next(item for item in data["events"] if "discovered_at" not in item)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.json"
            path.write_text(json.dumps({"schema_version": 3, "events": [event]}))
            result = subprocess.run([sys.executable, str(VALIDATE_EVENTS), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_known_discovery_dates_precede_concert_dates(self):
        events = {event["id"]: event for event in json.loads((ROOT / "radar/events.json").read_text())["events"]}
        mastodon = events["mastodon-deafheaven-alcest-anthem-washington-dc-2026-09-25"]
        payton = events["nicholas-payton-a-supreme-blue-blues-alley-2026-09-26"]
        self.assertEqual(mastodon["discovered_at"], "2026-08-20T11:42:34-04:00")
        self.assertEqual(payton["discovered_at"], "2026-08-17T19:33:31-04:00")
        self.assertLess(mastodon["discovered_at"][:10], mastodon["dates"]["start"])
        self.assertLess(payton["discovered_at"][:10], payton["dates"]["start"])

    def test_enrichment_cannot_replace_discovery_timestamp(self):
        with self.assertRaises(EnrichmentError):
            validate_patch_shape({
                "id": "event-2099",
                "discovered_at": "2026-09-29T12:00:00-04:00",
                "enrichment": {"status": "pending", "missing": ["official_event"], "note": "Test"},
            }, "patch")


class RadarStatusBrowserLogicTest(unittest.TestCase):
    def test_browser_health_matches_contract_and_ignores_event_discovery(self):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const assert = require('node:assert/strict');
const {deriveOperationalHealth} = require('./radar/app.js');
const status = {schema_version:1,enabled:true,cadence:'hourly',expected_max_silence_hours:12};
const run = (id, completed, outcome='success') => ({run_id:id,completed_at:completed,status:outcome});
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[run('recent','2026-09-29T12:00:00-04:00')]},new Date('2026-09-29T13:00:00-04:00')).state,'healthy');
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[run('old','2026-09-27T12:00:00-04:00')]},new Date('2026-09-29T13:00:00-04:00')).state,'stale');
assert.equal(deriveOperationalHealth({...status,enabled:false},{schema_version:1,runs:[]},new Date()).state,'off');
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[run('failed','2026-09-29T12:00:00-04:00','error')]},new Date()).state,'error');
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[run('failed','2026-09-29T11:00:00-04:00','error'),run('recovered','2026-09-29T12:00:00-04:00')]},new Date('2026-09-29T13:00:00-04:00')).state,'healthy');
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[]},new Date()).state,'unknown');
assert.equal(deriveOperationalHealth(status,{schema_version:1,runs:[run('scan','2026-09-29T12:00:00-04:00')]},new Date('2026-09-29T13:00:00-04:00')).latestRun.run_id,'scan');
"""
        subprocess.run([NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
