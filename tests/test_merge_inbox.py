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

    def test_root_ticket_endpoint_with_meaningful_query_is_valid(self):
        def mutate(event):
            event["enrichment"] = {"status": "complete", "missing": []}
            event["links"] = {"official_event": "https://example.com/events/test", "official_tickets": "https://tickets.example.com/?itemNumber=24054"}
            event["recommended_listening"] = [{"title": "Test", "apple_music_url": "https://music.apple.com/us/album/test/123"}]
        result = self.validate_modified_event(mutate)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_naked_homepage_and_search_url_are_invalid(self):
        for url in ("https://tickets.example.com/", "https://tickets.example.com/?", "https://tickets.example.com/search?query=test"):
            def mutate(event, url=url):
                event["enrichment"] = {"status": "complete", "missing": []}
                event["links"] = {"official_event": "https://example.com/events/test", "official_tickets": url}
                event["recommended_listening"] = [{"title": "Test", "apple_music_url": "https://music.apple.com/us/album/test/123"}]
            result = self.validate_modified_event(mutate)
            self.assertNotEqual(result.returncode, 0, url)

    def test_rejects_non_exact_apple_music_urls(self):
        for url in ("https://music.apple.com/us/search?term=test", "https://example.com/album/test", "not-a-url"):
            def mutate(event, url=url):
                event["recommended_listening"] = [{"title": "Test", "apple_music_url": url}]
            result = self.validate_modified_event(mutate)
            self.assertNotEqual(result.returncode, 0, url)

    def test_editorial_tier_claim_must_match_priority(self):
        for language, field, text in (
            ("en", "why_it_matters", "This clears S because the setting is unusual."),
            ("es", "trip_verdict", "S regional. Hay que proteger la noche."),
        ):
            def mutate(event, language=language, field=field, text=text):
                event["priority"] = "A+"
                event["editorial"][language][field] = text
            result = self.validate_modified_event(mutate)
            self.assertNotEqual(result.returncode, 0, (language, field))

    def test_lower_tiers_reject_higher_tier_action_language(self):
        for priority, language, text in (
            ("A+", "en", "Protect the night."),
            ("A", "es", "Vale priorizar la noche."),
        ):
            def mutate(event, priority=priority, language=language, text=text):
                event["priority"] = priority
                event["editorial"][language]["trip_verdict"] = text
            result = self.validate_modified_event(mutate)
            self.assertNotEqual(result.returncode, 0, (priority, language))

    def test_aligned_editorial_priority_language_is_valid(self):
        def mutate(event):
            event["priority"] = "A+"
            event["editorial"] = {
                "en": {"why_it_matters": "This earns A+ because the setting is unusually strong.", "trip_verdict": "A+ regional. Prioritize it if the date fits."},
                "es": {"why_it_matters": "Merece A+ por la fuerza particular del contexto.", "trip_verdict": "A+ regional. Vale priorizarla si la fecha cuadra."},
            }
        result = self.validate_modified_event(mutate)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_negated_higher_tier_comparison_is_valid(self):
        def mutate(event):
            event["priority"] = "S"
            event["editorial"] = {
                "en": {"why_it_matters": "A rare working-band context.", "trip_verdict": "S. It remains below S+ because this is a multi-night run."},
                "es": {"why_it_matters": "Un contexto poco común de banda estable.", "trip_verdict": "S. No llega a S+ porque es una residencia de varias noches."},
            }
        result = self.validate_modified_event(mutate)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_venue_rejects_alternate_name(self):
        def mutate(event):
            event["venue"] = {
                "id": "keystone-korner-baltimore",
                "name": "Keystone Korner",
                "city": "Baltimore",
                "state": "MD",
                "country": "US",
            }
        result = self.validate_modified_event(mutate)
        self.assertNotEqual(result.returncode, 0)

    def test_retired_venue_alias_is_rejected(self):
        def mutate(event):
            event["venue"]["id"] = "blue-note-tokyo-minami-aoyama"
        result = self.validate_modified_event(mutate)
        self.assertNotEqual(result.returncode, 0)

    def test_dc_city_spelling_is_canonical(self):
        def mutate(event):
            event["venue"] = {
                "id": "test-dc-venue",
                "name": "Test DC Venue",
                "city": "Washington",
                "state": "DC",
                "country": "US",
            }
        result = self.validate_modified_event(mutate)
        self.assertNotEqual(result.returncode, 0)

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

    def test_id_duplicate_is_reported_without_merging(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            canonical, curated, processed = self._paths(root)
            canonical.write_text(json.dumps({"schema_version": 3, "events": [self._event("same-id-2099")]}))
            batch = curated / "duplicate.json"
            batch.write_text(json.dumps(self._batch(self._event("same-id-2099"))))
            report = merge([batch], True, canonical, curated, processed)
            self.assertEqual(report["added"], [])
            self.assertEqual(report["conflicts"][0]["id"], "same-id-2099")

    def test_semantic_duplicate_is_reported_without_merging(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            canonical, curated, processed = self._paths(root)
            canonical.write_text(json.dumps({"schema_version": 3, "events": [self._event("beat-2099", artist="BEAT")]}))
            batch = curated / "semantic.json"
            batch.write_text(json.dumps(self._batch(self._event("beat-expanded-2099", artist="BEAT: Belew/Vai/Levin/Bozzio"))))
            report = merge([batch], True, canonical, curated, processed)
            self.assertEqual(report["added"], [])
            self.assertEqual(report["semantic_conflicts"][0]["conflict_with"], "beat-2099")

    def test_same_venue_and_date_with_different_artist_is_not_a_duplicate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            canonical, curated, processed = self._paths(root)
            canonical.write_text(json.dumps({"schema_version": 3, "events": [self._event("first-artist-2099", artist="First Artist")]}))
            batch = curated / "different-artist.json"
            batch.write_text(json.dumps(self._batch(self._event("second-artist-2099", artist="Second Artist"))))
            report = merge([batch], True, canonical, curated, processed)
            self.assertEqual(report["added"], ["second-artist-2099"])
            self.assertEqual(report["semantic_conflicts"], [])

    @staticmethod
    def _paths(root):
        curated = root / "radar/inbox/curated"
        curated.mkdir(parents=True)
        return root / "radar/events.json", curated, root / "radar/inbox/processed"

    @staticmethod
    def _event(event_id, artist="Test Artist"):
        return {
            "id": event_id, "artist": artist, "subtitle": None, "dates": {"start": "2099-01-01", "end": None}, "showtimes": [],
            "venue": {"id": "test-venue", "name": "Test Venue", "city": "Test City", "state": "TS", "country": "US"},
            "geographic_domain": "us_corridor", "geography": "Local", "priority": "A", "category": "Test", "genres": [], "musical_axes": [], "status": "passed", "lineup": [], "factual_description": None,
            "editorial": {"en": {}, "es": {}}, "links": {"official_event": None, "official_tickets": None},
            "tickets": {"currency": "USD", "official": {"minimum": None, "maximum": None, "source_url": None, "checked_on": None}, "resale": {"minimum": None, "maximum": None, "url": None, "checked_on": None}},
            "sources": [], "recommended_listening": [], "provenance": {"status": "test", "note": "Test fixture."}, "attendance": {"status": None, "evidence": [], "notes": None, "setlist": None, "photo_paths": []},
        }

    @staticmethod
    def _batch(event):
        return {"batch_version": 1, "kind": "curated_event_candidates", "batch_id": "test-batch", "events": [event]}


if __name__ == "__main__":
    unittest.main()
