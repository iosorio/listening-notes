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
from scripts.record_radar_run import append_run
from scripts.validate_radar_discovery import (
    DiscoveryValidationError,
    derive_health,
    validate_append_only,
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
    def test_heartbeat_append_is_idempotent_and_preserves_history(self):
        empty = {"schema_version": 1, "runs": []}
        first = append_run(empty, run())
        self.assertEqual(empty["runs"], [])
        self.assertEqual(append_run(first, run()), first)
        with self.assertRaises(DiscoveryValidationError):
            append_run(first, run(published=2))
        second = append_run(first, run("second", "2026-09-29T13:00:00-04:00", "2026-09-29T13:10:00-04:00"))
        validate_append_only(first, second)
        for corrupted in (empty, {"schema_version": 1, "runs": [run(published=3)]}):
            with self.assertRaises(DiscoveryValidationError):
                validate_append_only(first, corrupted)

    def test_record_command_dry_run_and_retry(self):
        with TemporaryDirectory() as directory:
            ledger = Path(directory) / "runs.json"
            ledger.write_text(json.dumps({"schema_version": 1, "runs": []}))
            record = Path(directory) / "record.json"
            record.write_text(json.dumps(run()))
            command = [sys.executable, str(ROOT / "scripts/record_radar_run.py"), "--record", str(record), "--runs", str(ledger)]
            subprocess.run(command + ["--dry-run"], check=True, capture_output=True)
            self.assertEqual(json.loads(ledger.read_text())["runs"], [])
            subprocess.run(command, check=True, capture_output=True)
            original = ledger.read_bytes()
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(ledger.read_bytes(), original)
            record.write_text(json.dumps(run(published=3)))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(ledger.read_bytes(), original)

    def test_nonfinite_silence_is_rejected(self):
        for value in (float("inf"), float("nan"), True, 0):
            malformed = status()
            malformed["expected_max_silence_hours"] = value
            with self.assertRaises(DiscoveryValidationError):
                validate_status(malformed)

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
    def test_python_and_browser_health_agree(self):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        now = datetime.fromisoformat("2026-09-29T16:00:00-04:00")
        success = run()
        failed = run("failed", "2026-09-29T14:00:00-04:00", "2026-09-29T14:05:00-04:00", "error")
        partial = run("partial", "2026-09-29T15:00:00-04:00", "2026-09-29T15:05:00-04:00", "partial")
        recovered = run("recovered", "2026-09-29T15:30:00-04:00", "2026-09-29T15:40:00-04:00")
        cases = [
            (status(), [], now, "unknown"),
            (status(False), [], now, "off"),
            (status(), [success], now, "healthy"),
            (status(False), [success], now, "off"),
            (status(), [success], datetime.fromisoformat("2026-09-30T00:10:00-04:00"), "healthy"),
            (status(), [success], datetime.fromisoformat("2026-09-30T00:10:01-04:00"), "stale"),
            (status(), [success, failed], now, "error"),
            (status(), [success, failed, partial], now, "error"),
            (status(), [failed, partial], now, "error"),
            (status(), [partial], now, "unknown"),
            (status(), [success, partial], now, "healthy"),
            (status(), [success, partial], datetime.fromisoformat("2026-09-30T16:00:00-04:00"), "stale"),
            (status(), [failed, partial, recovered], now, "healthy"),
            (status(), [success], datetime.fromisoformat("2026-09-29T11:00:00-04:00"), "unknown"),
        ]
        fixtures = []
        for desired, runs, clock, expected in cases:
            with self.subTest(expected=expected, runs=runs, clock=clock):
                report = derive_health(validate_status(desired), validate_runs({"schema_version": 1, "runs": runs}), clock)
                self.assertEqual(report["state"], expected)
                if expected == "off":
                    self.assertIsNone(report["next_expected_at"])
                fixtures.append({"status": desired, "runs": {"schema_version": 1, "runs": runs}, "now": clock.isoformat(), "expected": expected})
        script = r"""
const assert = require('node:assert/strict');
const {deriveOperationalHealth} = require('./radar/app.js');
const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));
for (const fixture of cases) {
  const model = deriveOperationalHealth(fixture.status, fixture.runs, new Date(fixture.now));
  assert.equal(model.state, fixture.expected, JSON.stringify(fixture));
  if (model.state === 'off') assert.equal(model.nextExpectedAt, null);
}
const valid = cases[2];
for (const runs of [null, {}, {schema_version:1,runs:[null]}, {schema_version:1,runs:[{}]},
  {schema_version:1,runs:[{...valid.runs.runs[0],completed_at:'invalid'}]},
  {schema_version:1,runs:[{...valid.runs.runs[0],sources_checked:-1}]}]) {
  assert.equal(deriveOperationalHealth(valid.status,runs,new Date(valid.now)).state,'unknown');
}
assert.equal(deriveOperationalHealth({...valid.status,enabled:false},null).state,'off');
assert.equal(deriveOperationalHealth({...valid.status,expected_max_silence_hours:Infinity},valid.runs).state,'unknown');
const realStatus = require('./radar/discovery/status.json');
const realRuns = require('./radar/discovery/runs.json');
// The canonical catalog is deliberately not an input to operational health.
if (realStatus.enabled && realRuns.runs.length === 0) assert.equal(deriveOperationalHealth(realStatus,realRuns).state,'unknown');
"""
        result = subprocess.run([NODE, "-e", script], input=json.dumps(fixtures), cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
