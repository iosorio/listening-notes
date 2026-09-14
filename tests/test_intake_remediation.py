"""Safety and reproducibility tests for active intake validation remediation."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import remediate_radar_intake as remediation
from scripts.verify_radar_duplicate_resolution import verify as verify_duplicate_resolution
from scripts.verify_radar_residual_repairs import verify as verify_residual_repairs


ROOT = Path(__file__).resolve().parents[1]

PROVENANCE_REPORTS = (
    "radar/inbox/review/duplicate-resolution-2026-09-11-validation.json",
    "radar/inbox/review/duplicate-resolution-2026-09-11.md",
    "radar/inbox/review/residual-validation-2026-09-11.json",
    "radar/inbox/review/residual-resolution-2026-09-11.md",
)


def event(event_id="valid-candidate-2099"):
    return {
        "id": event_id,
        "artist": "Example Artist",
        "subtitle": None,
        "dates": {"start": "2099-01-01", "end": None},
        "showtimes": ["20:00"],
        "venue": {
            "id": "the-anthem-washington-dc",
            "name": "The Anthem",
            "city": "Washington, DC",
            "state": "DC",
            "country": "US",
        },
        "geographic_domain": "us_corridor",
        "geography": "Local",
        "priority": "A",
        "category": "Test",
        "genres": [],
        "musical_axes": [],
        "status": "considering",
        "lineup": [],
        "factual_description": None,
        "editorial": {
            "en": {"why_it_matters": "A test event.", "trip_verdict": "Consider it.", "listen_before": None},
            "es": {"why_it_matters": "Un evento de prueba.", "trip_verdict": "Vale considerarlo.", "listen_before": None},
        },
        "links": {
            "official_event": "https://venue.example/events/example",
            "official_tickets": "https://tickets.example/events/example",
        },
        "tickets": {
            "currency": "USD",
            "official": {"minimum": None, "maximum": None, "source_url": None, "checked_on": None},
            "resale": {"minimum": None, "maximum": None, "url": None, "checked_on": None},
        },
        "sources": [],
        "recommended_listening": [{
            "artist": "Example Artist",
            "title": "Example Album",
            "kind": "album",
            "apple_music_url": "https://music.apple.com/us/album/example/1",
        }],
        "enrichment": {"status": "complete", "missing": []},
        "provenance": {"status": "test", "note": "Test fixture."},
        "attendance": {"status": None, "evidence": [], "notes": None, "setlist": None, "photo_paths": []},
    }


class EnrichmentNormalizationTest(unittest.TestCase):
    def test_complete_with_absent_component_becomes_exact_pending(self):
        original = event()
        original["links"]["official_tickets"] = None
        original["enrichment"] = {"status": "complete", "missing": [], "note": "Existing explanation."}
        repaired, reasons = remediation.normalize_enrichment(original, "2026-09-11")
        self.assertTrue(reasons)
        self.assertEqual(repaired["enrichment"]["status"], "pending")
        self.assertEqual(repaired["enrichment"]["missing"], ["official_tickets"])
        self.assertTrue(repaired["enrichment"]["note"].startswith("Existing explanation."))
        self.assertEqual({k: v for k, v in repaired.items() if k != "enrichment"}, {k: v for k, v in original.items() if k != "enrichment"})

    def test_nonstandard_missing_labels_are_preserved_in_note(self):
        original = event()
        original["links"]["official_tickets"] = None
        original["recommended_listening"] = []
        original["enrichment"] = {"status": "partial", "missing": ["special_guest", "apple_music"], "note": "Uncertainty remains."}
        repaired, _reasons = remediation.normalize_enrichment(original, "2026-09-11")
        self.assertEqual(repaired["enrichment"]["status"], "pending")
        self.assertEqual(repaired["enrichment"]["missing"], ["official_tickets", "apple_music"])
        self.assertIn("special_guest", repaired["enrichment"]["note"])

    def test_complete_factual_note_is_not_deleted_or_moved_automatically(self):
        original = event()
        original["enrichment"]["note"] = "Verified context that must remain preserved."
        repaired, reasons = remediation.normalize_enrichment(original, "2026-09-11")
        self.assertFalse(reasons)
        self.assertEqual(repaired, original)


class MaterializationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.active = self.root / "radar/inbox/curated"
        self.active.mkdir(parents=True)
        self.review = self.root / "radar/inbox/review/validation-decisions"
        self.canonical = self.root / "radar/events.json"
        self.registry = self.root / "radar/venue_identities.json"
        self.canonical.write_text(json.dumps({"schema_version": 3, "events": []}))
        self.registry.write_bytes((ROOT / "radar/venue_identities.json").read_bytes())
        valid = event()
        automatic = event("automatic-candidate-2099")
        automatic["artist"] = "Automatic Artist"
        automatic["dates"]["start"] = "2099-01-02"
        automatic["links"]["official_tickets"] = None
        automatic["enrichment"] = {"status": "complete", "missing": []}
        review = event("review-candidate-2099")
        review["artist"] = "Review Artist"
        review["dates"]["start"] = "2099-01-03"
        review["links"]["official_event"] = "https://venue.example/"
        review["enrichment"] = {"status": "pending", "missing": ["official_event"], "note": "Needs an exact page."}
        eddie = event("eddie-palmieri-2019-user-confirmed")
        eddie["artist"] = "Eddie Palmieri"
        eddie["dates"]["start"] = None
        self.batch = {
            "batch_version": 1,
            "kind": "curated_event_candidates",
            "batch_id": "remediation-test",
            "events": [valid, automatic, review, eddie],
        }
        self.path = self.active / "mixed.json"
        self.path.write_text(json.dumps(self.batch, ensure_ascii=False, indent=2) + "\n")
        for name, value in (
            ("ROOT", self.root), ("ACTIVE", self.active), ("CANONICAL", self.canonical),
            ("REGISTRY", self.registry), ("REVIEW", self.review),
        ):
            started = patch.object(remediation, name, value)
            started.start()
            self.addCleanup(started.stop)

    def test_plan_apply_and_archive_preserve_original(self):
        original = self.path.read_bytes()
        manifest = remediation.build_plan("2026-09-11")
        self.assertEqual(
            manifest["summary"],
            {"valid": 1, "normalize_enrichment": 1, "correct_from_official": 0, "review_validation": 2},
        )
        eddie = next(item for item in manifest["decisions"] if item["candidate_event_id"].startswith("eddie-"))
        self.assertEqual(eddie["materialization"], "preserve_active_review")
        dry = remediation.materialize(manifest, False)
        self.assertTrue(dry["dry_run"])
        self.assertEqual(self.path.read_bytes(), original)
        report = remediation.materialize(manifest, True)
        self.assertEqual(report["automatic_repairs"], 1)
        self.assertEqual(report["review_candidates"], 1)
        archive = json.loads(next(self.review.glob("*.json")).read_text())
        self.assertEqual(archive["source"]["original_text"].encode(), original)
        current = json.loads(self.path.read_text())
        self.assertEqual([item["id"] for item in current["events"]], [
            "valid-candidate-2099", "automatic-candidate-2099", "eddie-palmieri-2019-user-confirmed",
        ])
        self.assertEqual(current["events"][1]["enrichment"]["status"], "pending")
        self.assertEqual(current["events"][1]["enrichment"]["missing"], ["official_tickets"])

    def test_stale_manifest_prevents_every_write(self):
        manifest = remediation.build_plan("2026-09-11")
        manifest["decisions"][0]["candidate_sha256"] = "stale"
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "plan changed"):
            remediation.materialize(manifest, True)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.review.exists())


class HistoricalChainTest(unittest.TestCase):
    def test_duplicate_verifier_reaches_current_validation_state(self):
        manifest = json.loads((ROOT / "radar/inbox/review/duplicate-resolution-2026-09-11.json").read_text())
        report = verify_duplicate_resolution(manifest)
        self.assertEqual(len(report["archived_candidates"]), 11)
        self.assertEqual(report["reviews"], ["eddie-palmieri-2019-user-confirmed"])
        self.assertEqual(report["later_remediation"]["report"]["ingestible_candidates"], 270)

    def test_residual_verifier_reaches_current_validation_state(self):
        repairs = json.loads((ROOT / "radar/inbox/review/residual-repair-2026-09-11.json").read_text())
        decisions = json.loads((ROOT / "radar/inbox/review/residual-duplicates-2026-09-11.json").read_text())
        report = verify_residual_repairs(repairs, decisions)
        self.assertEqual(len(report["residuals"]), 4)
        self.assertEqual(len(report["archives"]["archived_candidates"]), 3)
        self.assertEqual(report["archives"]["reviews"], ["eddie-palmieri-2019-user-confirmed"])


class PortableProvenanceTest(unittest.TestCase):
    def test_historical_reports_do_not_publish_ephemeral_paths(self):
        forbidden_markers = (
            "/" + "Users" + "/",
            "/" + "tmp" + "/",
            "Israels" + "-Mac",
        )
        for relative_path in PROVENANCE_REPORTS:
            with self.subTest(path=relative_path):
                text = (ROOT / relative_path).read_text(encoding="utf-8")
                for marker in forbidden_markers:
                    self.assertNotIn(marker, text)

    def test_validation_reports_record_portable_execution_metadata(self):
        for relative_path in (PROVENANCE_REPORTS[0], PROVENANCE_REPORTS[2]):
            with self.subTest(path=relative_path):
                report = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
                artifact = report["execution_artifact"]
                self.assertEqual(artifact["host"], "Mac Pro")
                self.assertEqual(artifact["checked_on"], "2026-09-11")
                self.assertEqual(artifact["type"], "temporary detached validation worktree")
                self.assertIsNone(artifact["artifact_sha256"])
                self.assertEqual(
                    artifact["validated_tracked_diff_sha256"],
                    report["tracked_diff_sha256"],
                )
                self.assertEqual(
                    artifact["status"],
                    "temporary artifact removed after validation",
                )


if __name__ == "__main__":
    unittest.main()
