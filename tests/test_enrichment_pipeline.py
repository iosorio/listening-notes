import hashlib
import json
import os
import shutil
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch as mock_patch

from scripts.enrichment_common import (
    CURATED_KIND,
    RESEARCH_KIND,
    EnrichmentError,
    apply_patch,
    validate_research_batch,
)
from scripts.merge_enrichment_patches import merge


def event(event_id="test-artist-2026"):
    return {
        "id": event_id,
        "artist": "Test Artist",
        "subtitle": None,
        "dates": {"start": "2026-09-01", "end": None},
        "showtimes": [],
        "venue": {"id": "test-venue-city", "name": "Test Venue", "city": "City", "state": "State", "country": "US"},
        "geographic_domain": "us_corridor",
        "geography": "Local",
        "priority": "S",
        "category": "Masters",
        "genres": ["Jazz"],
        "musical_axes": ["Masters"],
        "status": "considering",
        "lineup": [],
        "factual_description": None,
        "editorial": {"en": {}, "es": {}},
        "links": {"official_event": None, "official_tickets": None},
        "tickets": {
            "currency": "USD",
            "official": {"minimum": None, "maximum": None, "source_url": None, "checked_on": None},
            "resale": {"minimum": None, "maximum": None, "url": None, "checked_on": None},
        },
        "sources": [],
        "recommended_listening": [],
        "enrichment": {"status": "pending", "missing": ["official_event", "official_tickets", "apple_music"], "note": "Research pending."},
        "provenance": {"status": "legacy", "note": "Original record."},
        "attendance": {"status": None, "evidence": [], "notes": None, "setlist": None, "photo_paths": []},
    }


def source(url="https://venue.example/events/test"):
    return {"publisher": "Official Venue", "url": url, "checked_on": "2026-08-15"}


def recommendation(url="https://music.apple.com/us/album/test/123"):
    return {"artist": "Test Artist", "title": "Test Album", "kind": "album", "apple_music_url": url}


def complete_patch(event_id="test-artist-2026"):
    return {
        "id": event_id,
        "links": {
            "official_event": "https://venue.example/events/test",
            "official_tickets": "https://tickets.example/events/test",
        },
        "recommended_listening": [recommendation()],
        "enrichment": {"status": "complete", "missing": []},
        "sources": [source(), source("https://tickets.example/events/test")],
    }


def research_batch(*patches):
    return {"batch_version": 1, "kind": RESEARCH_KIND, "batch_id": "test-batch-001", "created_on": "2026-08-15", "events": list(patches)}


class EnrichmentContractTest(unittest.TestCase):
    def canonical(self, *events):
        return {"schema_version": 3, "events": list(events or (event(),))}

    def validate(self, *patches):
        return validate_research_batch(research_batch(*patches), self.canonical(), Path("research.json"))

    def test_unknown_and_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(EnrichmentError, "unknown canonical event id"):
            self.validate(complete_patch("unknown-event-2026"))
        with self.assertRaisesRegex(EnrichmentError, "duplicate event id"):
            self.validate(complete_patch(), complete_patch())

    def test_forbidden_fields_are_rejected(self):
        patch = complete_patch()
        patch["venue"] = {"city": "Elsewhere"}
        with self.assertRaisesRegex(EnrichmentError, "forbidden updates: venue"):
            self.validate(patch)

    def test_malformed_official_urls_are_rejected(self):
        for bad_url in ("http://venue.example/events/test", "https://venue.example/", "https://google.com/search?q=test"):
            patch = complete_patch()
            patch["links"]["official_event"] = bad_url
            with self.subTest(bad_url=bad_url), self.assertRaises(EnrichmentError):
                self.validate(patch)

    def test_invalid_apple_music_forms_are_rejected(self):
        urls = (
            "https://music.apple.com/us/search?term=test",
            "https://music.apple.com/us/artist/test/123",
            "https://example.com/album/test/123",
            "not-a-url",
        )
        for bad_url in urls:
            patch = complete_patch()
            patch["recommended_listening"] = [recommendation(bad_url)]
            with self.subTest(bad_url=bad_url), self.assertRaises(EnrichmentError):
                self.validate(patch)

    def test_complete_must_have_all_resulting_enrichment(self):
        patch = {
            "id": "test-artist-2026",
            "links": {"official_event": "https://venue.example/events/test"},
            "enrichment": {"status": "complete", "missing": []},
        }
        with self.assertRaisesRegex(EnrichmentError, "claims complete"):
            self.validate(patch)

    def test_valid_pending_and_unavailable_are_accepted(self):
        for status in ("pending", "unavailable"):
            patch = {
                "id": "test-artist-2026",
                "links": {"official_event": "https://venue.example/events/test"},
                "enrichment": {
                    "status": status,
                    "missing": ["official_tickets", "apple_music"],
                    "note": "No exact destination is currently verifiable.",
                },
            }
            with self.subTest(status=status):
                self.validate(patch)

    def test_omission_preserves_unrelated_and_existing_values(self):
        original = event()
        original["links"]["official_tickets"] = "https://tickets.example/events/original"
        original["editorial"]["en"]["why_it_matters"] = "Keep this exact copy."
        patch = {
            "id": original["id"],
            "links": {"official_event": "https://venue.example/events/test"},
            "enrichment": {"status": "pending", "missing": ["apple_music"], "note": "Listening link pending."},
        }
        before = deepcopy(original)
        apply_patch(original, patch)
        self.assertEqual(original["links"]["official_tickets"], before["links"]["official_tickets"])
        self.assertEqual(original["editorial"], before["editorial"])

    def test_verified_link_requires_justified_replacement(self):
        original = event()
        original["links"]["official_event"] = "https://venue.example/events/old"
        patch = {
            "id": original["id"],
            "links": {"official_event": "https://venue.example/events/new"},
            "enrichment": {"status": "pending", "missing": ["official_tickets", "apple_music"], "note": "Other fields pending."},
        }
        with self.assertRaisesRegex(EnrichmentError, "replacement_reason"):
            apply_patch(original, patch)
        patch["replacement_reason"] = "The venue replaced its temporary listing."
        patch["sources"] = [source("https://venue.example/events/unrelated")]
        with self.assertRaisesRegex(EnrichmentError, "source for the new URL"):
            apply_patch(original, patch)
        patch["sources"] = [source("https://venue.example/events/new")]
        apply_patch(original, patch)
        self.assertEqual(original["links"]["official_event"], "https://venue.example/events/new")

    def test_sources_recommendations_and_provenance_are_idempotent(self):
        original = event()
        patch = complete_patch()
        equivalent_source = deepcopy(patch["sources"][0])
        equivalent_source["url"] += "/"
        patch["sources"].append(equivalent_source)
        patch["recommended_listening"].append(deepcopy(patch["recommended_listening"][0]))
        patch["provenance"] = {"status": "reviewed-backfill", "note": "Explicitly approved.", "recorded_on": "2026-08-15"}
        apply_patch(original, patch)
        once = deepcopy(original)
        changes = apply_patch(original, patch)
        self.assertEqual(original, once)
        self.assertEqual(changes, [])
        self.assertEqual(len(original["sources"]), 2)
        self.assertEqual(len(original["recommended_listening"]), 1)
        self.assertEqual(len(original["provenance"]["enrichment_history"]), 1)
        self.assertEqual(original["provenance"]["status"], "legacy")


class EnrichmentMergeTest(unittest.TestCase):
    def fixture(self, directory: Path, patches):
        root = directory
        research_dir = root / "radar/inbox/research"
        curated_dir = root / "radar/inbox/curated/enrichment"
        processed_dir = root / "radar/inbox/processed/enrichment"
        research_dir.mkdir(parents=True)
        curated_dir.mkdir(parents=True)
        canonical_path = root / "radar/events.json"
        canonical_path.write_text(json.dumps({"schema_version": 3, "events": [event()]}, indent=2) + "\n")
        research_path = research_dir / "test.json"
        research = research_batch(*patches)
        research_path.write_text(json.dumps(research, indent=2) + "\n")
        curated = {
            "batch_version": 1,
            "kind": CURATED_KIND,
            "batch_id": research["batch_id"],
            "review": {
                "research_path": "radar/inbox/research/test.json",
                "research_batch_id": research["batch_id"],
                "research_sha256": hashlib.sha256(research_path.read_bytes()).hexdigest(),
                "approved_by": "Test Reviewer",
                "approved_on": "2026-08-15",
            },
            "patches": research["events"],
        }
        curated_path = curated_dir / "test.json"
        curated_path.write_text(json.dumps(curated, indent=2) + "\n")
        return root, research_dir, canonical_path, curated_path, processed_dir

    def test_merge_is_atomic_and_preserves_canonical_on_failure(self):
        with TemporaryDirectory() as directory:
            root, research, canonical, curated, processed = self.fixture(Path(directory), [complete_patch(), complete_patch("unknown-event-2026")])
            before = canonical.read_bytes()
            with self.assertRaises(EnrichmentError):
                merge([curated], False, canonical, processed, root, research)
            self.assertEqual(canonical.read_bytes(), before)
            self.assertTrue(curated.exists())
            self.assertFalse(processed.exists())

    def test_successful_merge_archives_and_repeat_is_noop(self):
        with TemporaryDirectory() as directory:
            root, research, canonical, curated, processed = self.fixture(Path(directory), [complete_patch()])
            report = merge([curated], False, canonical, processed, root, research)
            self.assertEqual(report["events"][0]["id"], "test-artist-2026")
            archived = processed / curated.name
            self.assertTrue(archived.exists())
            self.assertFalse(curated.exists())
            once = canonical.read_bytes()
            curated.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archived, curated)
            report = merge([curated], False, canonical, processed, root, research)
            self.assertEqual(report["already_processed"], ["test-batch-001"])
            self.assertEqual(canonical.read_bytes(), once)

    def test_filesystem_failure_rolls_back_canonical(self):
        with TemporaryDirectory() as directory:
            root, research, canonical, curated, processed = self.fixture(Path(directory), [complete_patch()])
            before = canonical.read_bytes()
            real_replace = os.replace
            calls = 0

            def fail_archive_once(source_path, destination_path):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated archive failure")
                return real_replace(source_path, destination_path)

            with mock_patch("scripts.merge_enrichment_patches.os.replace", side_effect=fail_archive_once):
                with self.assertRaisesRegex(EnrichmentError, "changes rolled back"):
                    merge([curated], False, canonical, processed, root, research)
            self.assertEqual(canonical.read_bytes(), before)
            self.assertTrue(curated.exists())


if __name__ == "__main__":
    unittest.main()
