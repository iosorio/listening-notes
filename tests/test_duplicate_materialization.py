"""Safety regressions for hash-bound duplicate archival and mixed batches."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import materialize_radar_intake as materializer
from scripts.plan_radar_intake import decide
from scripts.venue_identity import load_registry


def performance(event_id, artist="Artist", url="https://venue.example/event/specific"):
    return {
        "id": event_id, "artist": artist, "subtitle": None,
        "dates": {"start": "2099-01-01", "end": None}, "showtimes": ["20:00"],
        "venue": {"id": "the-anthem-washington-dc", "name": "The Anthem", "city": "Washington, DC", "state": "DC", "country": "US"},
        "links": {"official_event": url, "official_tickets": None}, "lineup": [],
    }


class DuplicateSafetyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.active = self.root / "radar/inbox/curated"
        self.active.mkdir(parents=True)
        self.archive = self.root / "radar/inbox/review/decisions"
        self.canonical = self.root / "radar/events.json"
        self.registry = load_registry()
        self.existing = performance("canonical-2099")
        self.canonical.write_text(json.dumps({"schema_version": 3, "events": [self.existing]}))
        self.batch = {
            "batch_version": 1, "kind": "curated_event_candidates", "batch_id": "mixed",
            "notes": "Preserve envelope and every residual field.",
            "events": [performance("duplicate-2099"), performance("residual-2099", "Other", "https://venue.example/event/other")],
        }
        self.path = self.active / "mixed.json"
        self.path.write_text(json.dumps(self.batch, ensure_ascii=False, indent=4) + "\n")
        for name, value in (("ROOT", self.root), ("ACTIVE", self.active), ("CANONICAL", self.canonical), ("ARCHIVE", self.archive)):
            p = patch.object(materializer, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(materializer, "validate_canonical")
        p.start()
        self.addCleanup(p.stop)

    def manifest(self, index=0):
        batch = json.loads(self.path.read_text())
        candidate = batch["events"][index]
        detail = decide(deepcopy(candidate), [self.existing], self.registry)
        return {
            "canonical": {"sha256": materializer.digest(self.canonical)},
            "venue_registry": {"sha256": materializer.digest(materializer.REGISTRY)},
            "decisions": [{
                "path": str(self.path.relative_to(self.root)), "sha256": materializer.digest(self.path),
                "event_index": index, "candidate_event_id": candidate["id"],
                "recorded_on": "2026-09-11", "reason": "Specific official URL confirmed.", **detail,
            }],
        }

    def test_dry_run_is_read_only_and_split_preserves_exact_original(self):
        original = self.path.read_bytes()
        manifest = self.manifest()
        dry = materializer.materialize(manifest, False)
        self.assertTrue(dry["dry_run"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.archive.exists())
        report = materializer.materialize(manifest, True)
        self.assertFalse(report["dry_run"])
        archived = json.loads(next(self.archive.glob("*.json")).read_text())
        self.assertEqual(archived["source"]["original_text"].encode(), original)
        self.assertEqual(archived["source"]["original_batch"], self.batch)
        self.assertEqual(archived["duplicates"][0]["original_event"], self.batch["events"][0])
        self.assertEqual(archived["duplicates"][0]["decision"], manifest["decisions"][0])
        self.assertEqual(json.loads(self.path.read_text()), dict(self.batch, events=self.batch["events"][1:]))

    def test_fully_duplicated_batch_is_recoverable_and_replay_fails(self):
        self.batch["events"] = self.batch["events"][:1]
        self.path.write_text(json.dumps(self.batch))
        manifest = self.manifest()
        report = materializer.materialize(manifest, True)
        self.assertFalse(self.path.exists())
        self.assertEqual(len(report["removed_active"]), 1)
        self.assertEqual(json.loads(next(self.archive.glob("*.json")).read_text())["source"]["original_batch"], self.batch)
        with self.assertRaises(ValueError):
            materializer.materialize(manifest, True)

    def test_stale_batch_or_canonical_or_registry_fails_before_writes(self):
        for target in ("batch", "canonical", "registry"):
            with self.subTest(target=target):
                manifest = self.manifest()
                if target == "batch":
                    manifest["decisions"][0]["sha256"] = "stale"
                else:
                    manifest["venue_registry" if target == "registry" else target]["sha256"] = "stale"
                before = self.path.read_bytes()
                with self.assertRaises(ValueError):
                    materializer.materialize(manifest, True)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertFalse(self.archive.exists())

    def test_tampered_index_id_evidence_and_canonical_are_rejected(self):
        for key, value in (("event_index", -1), ("event_index", True), ("event_index", 99),
                           ("candidate_event_id", "wrong"), ("canonical_event_id", "missing"),
                           ("evidence", [{"kind": "same_official_event_url", "url": "https://wrong.example/"}])):
            with self.subTest(key=key, value=value):
                manifest = self.manifest()
                manifest["decisions"][0][key] = value
                with self.assertRaises(ValueError):
                    materializer.materialize(manifest, True)
                self.assertFalse(self.archive.exists())

    def test_repeated_decision_is_rejected(self):
        manifest = self.manifest()
        manifest["decisions"] *= 2
        with self.assertRaisesRegex(ValueError, "repeated"):
            materializer.materialize(manifest, True)

    def test_invalid_residual_blocks_all_writes(self):
        self.batch["events"][1]["artist"] = None
        self.path.write_text(json.dumps(self.batch))
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            materializer.materialize(self.manifest(), True)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.archive.exists())

    def test_late_archive_collision_blocks_earlier_batch(self):
        manifest = self.manifest()
        second = self.active / "second.json"
        second.write_bytes(self.path.read_bytes())
        other = deepcopy(manifest["decisions"][0])
        other["path"] = str(second.relative_to(self.root))
        manifest["decisions"].append(other)
        self.archive.mkdir(parents=True)
        collision = self.archive / f"{materializer.digest(second)}-{second.name}"
        collision.write_text("existing evidence")
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            materializer.materialize(manifest, True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.archive.iterdir()), [collision])

    def test_review_is_never_materialized(self):
        manifest = self.manifest()
        manifest["decisions"][0]["action"] = "review"
        before = self.path.read_bytes()
        self.assertFalse(materializer.materialize(manifest, True)["archived"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_blocked_duplicate_remains_active_without_any_writes(self):
        manifest = self.manifest()
        manifest["decisions"][0]["materialization"] = {"status": "blocked_residual_validation"}
        before = self.path.read_bytes()
        self.assertFalse(materializer.materialize(manifest, True)["archived"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_individual_normalized_residual_failure_prevents_all_writes(self):
        before = self.path.read_bytes()
        with patch.object(materializer, "validate_canonical", side_effect=[None, ValueError("invalid enrichment")]):
            with self.assertRaisesRegex(ValueError, "invalid enrichment"):
                materializer.materialize(self.manifest(), True)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_researched_duplicate_requires_official_evidence_and_event_hashes(self):
        self.batch["events"][0]["links"]["official_event"] = "https://venue.example/"
        self.path.write_text(json.dumps(self.batch))
        manifest = self.manifest()
        d = manifest["decisions"][0]
        detail = {k: d[k] for k in ("action", "approval", "canonical_event_id", "evidence", "diff", "normalization")}
        d.update(action="archive_duplicate", approval="approved", planned_decision=detail)
        with self.assertRaisesRegex(ValueError, "official research"):
            materializer.materialize(manifest, False)
        d["research"] = {"outcome": "same_engagement", "reason": "Official program confirms the full engagement.", "checked_on": "2026-09-11", "sources": [{"url": "https://venue.example/program", "finding": "The same complete program and personnel are listed."}]}
        d["candidate_event_sha256"] = materializer.data_digest(self.batch["events"][0])
        d["canonical_event_sha256"] = "stale"
        with self.assertRaisesRegex(ValueError, "hashes"):
            materializer.materialize(manifest, False)
        d["canonical_event_sha256"] = materializer.data_digest(self.existing)
        self.assertEqual(len(materializer.materialize(manifest, False)["archived"]), 1)

    def test_festival_lineup_is_not_a_specific_event_url(self):
        for slug in ("lineup", "lineup-2026", "schedule_2026", "calendar-2026"):
            with self.subTest(slug=slug):
                a = performance("a-2099", "Chuck Brown", f"https://festival.example/{slug}")
                b = performance("b-2099", "African Rhythms", f"https://festival.example/{slug}")
                self.assertEqual(decide(a, [b], self.registry)["action"], "create")

    def test_specific_page_cannot_archive_distinct_dates_or_sets(self):
        a = performance("a-2099")
        b = performance("b-2099")
        b["dates"]["start"] = "2099-01-02"
        self.assertEqual(decide(a, [b], self.registry)["action"], "review")
        b["dates"] = deepcopy(a["dates"])
        b["showtimes"] = ["22:00"]
        self.assertEqual(decide(a, [b], self.registry)["action"], "review")
