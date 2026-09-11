import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.plan_radar_intake import decide
from scripts.venue_identity import VenueIdentityError, canonicalize_venue, load_registry


def event(event_id, artist="Artist", showtimes=None, official="https://venue.example/events/show"):
    return {
        "id": event_id,
        "artist": artist,
        "subtitle": None,
        "dates": {"start": "2099-01-01", "end": None},
        "showtimes": showtimes or [],
        "venue": {"id": "the-anthem-washington-dc", "name": "The Anthem", "city": "Washington, DC", "state": "DC", "country": "US"},
        "links": {"official_event": official, "official_tickets": None},
        "lineup": [],
    }


class VenueIdentityTest(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_alias_id_name_and_city_normalize_to_declarative_identity(self):
        venue, changes = canonicalize_venue(
            {"id": "anthem-washington-dc", "name": "Anthem", "city": "Washington", "state": "DC", "country": "US"}, self.registry
        )
        self.assertEqual(venue["id"], "the-anthem-washington-dc")
        self.assertEqual(venue["name"], "The Anthem")
        self.assertEqual(venue["city"], "Washington, DC")
        self.assertEqual({change["field"] for change in changes}, {"venue.id", "venue.name", "venue.city"})

    def test_canonical_historical_alias_is_not_a_valid_final_identity(self):
        venue, changes = canonicalize_venue(
            {"id": "blue-note-tokyo-aoyama", "name": "Blue Note Tokyo", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, self.registry
        )
        self.assertEqual(venue["id"], "blue-note-tokyo-minamiaoyama")
        self.assertTrue(changes)

    def test_registry_rejects_duplicate_json_keys(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "venues.json"
            path.write_text('{"schema_version":1,"venues":{"same":{},"same":{}}}')
            with self.assertRaisesRegex(VenueIdentityError, "duplicate JSON key 'same'"):
                load_registry(path)

    def test_new_active_venue_identities_are_registered(self):
        venues = (
            ("blue-note-place-ebisu-tokyo", "Blue Note Place", "Shibuya, Tokyo"),
            ("fillmore-silver-spring-silver-spring-md", "The Fillmore Silver Spring", "Silver Spring"),
            ("keystone-club-tokyo", "KEYSTONE CLUB TOKYO", "Minato, Tokyo"),
            ("songbyrd-music-house-washington-dc", "Songbyrd Music House", "Washington, DC"),
            ("the-pocket-new-york", "The Pocket", "New York"),
            ("toyosu-pit-tokyo", "Toyosu PIT", "Koto, Tokyo"),
            ("victoria-theater-njpac-newark-nj", "Victoria Theater at NJPAC", "Newark"),
            ("wu-tsai-theater-david-geffen-hall-new-york", "Wu Tsai Theater, David Geffen Hall", "New York"),
        )
        for venue_id, name, city in venues:
            with self.subTest(venue_id=venue_id):
                venue, changes = canonicalize_venue(
                    {"id": venue_id, "name": name, "city": city, "state": self.registry["venues"][venue_id]["state"], "country": self.registry["venues"][venue_id]["country"]},
                    self.registry,
                )
                self.assertFalse(changes)
                self.assertEqual(venue["id"], venue_id)

    def test_new_observed_name_and_city_variants_normalize(self):
        cases = (
            ({"id": "songbyrd-music-house-washington-dc", "name": "Songbyrd Music House", "city": "Washington", "state": "DC", "country": "US"}, "songbyrd-music-house-washington-dc", "Washington, DC"),
            ({"id": "toyosu-pit-tokyo", "name": "Toyosu PIT", "city": "Tokyo", "state": "Tokyo", "country": "JP"}, "toyosu-pit-tokyo", "Koto, Tokyo"),
            ({"id": "victoria-theater-njpac-newark-nj", "name": "Victoria Theater, New Jersey Performing Arts Center", "city": "Newark", "state": "NJ", "country": "US"}, "victoria-theater-njpac-newark-nj", "Newark"),
        )
        for raw, expected_id, expected_city in cases:
            with self.subTest(venue_id=raw["id"]):
                venue, changes = canonicalize_venue(raw, self.registry)
                self.assertTrue(changes)
                self.assertEqual(venue["id"], expected_id)
                self.assertEqual(venue["city"], expected_city)


class IntakeDecisionTest(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()

    def test_identical_official_url_is_a_permitted_archive_duplicate(self):
        canonical = event("canonical-2099")
        candidate = event("candidate-2099")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "archive_duplicate")
        self.assertEqual(decision["approval"], "permitted")

    def test_distinct_showtimes_stay_in_review_not_automatic_merge(self):
        canonical = event("canonical-2099", artist="Same Artist", showtimes=["18:00"], official="https://venue.example/events/one")
        candidate = event("candidate-2099", artist="Same Artist", showtimes=["21:00"], official="https://venue.example/events/two")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")
        self.assertTrue(decision["evidence"][1]["value"])

    def test_shared_ticket_provider_url_does_not_merge_different_functions(self):
        canonical = event("canonical-2099", artist="First Artist", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        candidate = event("candidate-2099", artist="Second Artist", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "create")

    def test_generic_ticket_provider_listing_never_archives_same_artist(self):
        canonical = event("canonical-2099", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        candidate = event("candidate-2099", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/provider/listing"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_ticket_url_with_partial_artist_identity_stays_in_review(self):
        canonical = event("canonical-2099", artist="BEAT: Belew Vai Levin Bozzio", official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        candidate = event("candidate-2099", artist="BEAT", official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_trailing_slash_is_not_an_exact_official_event_url(self):
        canonical = event("canonical-2099", official="https://venue.example/events/show")
        candidate = event("candidate-2099", official="https://venue.example/events/show/")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_coming_soon_page_is_never_duplicate_evidence(self):
        canonical = event("canonical-2099", official="https://venue.example/event/coming-soon")
        candidate = event("candidate-2099", official="https://venue.example/event/coming-soon")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_shared_ticket_url_with_separate_showtimes_stays_in_review(self):
        canonical = event("canonical-2099", showtimes=["18:00"], official="https://venue.example/events/first")
        canonical["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        candidate = event("candidate-2099", showtimes=["21:00"], official="https://venue.example/events/second")
        candidate["links"]["official_tickets"] = "https://tickets.example.com/event/123"
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review")

    def test_factual_difference_never_becomes_replace_without_a_decision_record(self):
        canonical = event("canonical-2099", official="https://venue.example/events/old")
        candidate = event("candidate-2099", official="https://venue.example/events/new")
        decision = decide(candidate, [canonical], self.registry)
        self.assertEqual(decision["action"], "review" if decision["action"] == "review" else "create")


if __name__ == "__main__":
    unittest.main()
