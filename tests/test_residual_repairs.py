"""Regressions for exact enrichment metadata and explicit yen admission."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.merge_inbox import normalize, validate_canonical
from scripts.validate_events import validate_enrichment

ROOT = Path(__file__).resolve().parents[1]


class ResidualRepairTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repairs = json.loads((ROOT / "radar/inbox/review/residual-repair-2026-09-11.json").read_text())
        cls.original = {}
        cls.corrected = {}
        for batch in cls.repairs["batches"]:
            ids = {c["event_id"] for c in batch["changes"]}
            for field, target in (("original_text", cls.original), ("corrected_text", cls.corrected)):
                target.update({e["id"]: e for e in json.loads(batch[field])["events"] if e["id"] in ids})

    def sora(self):
        return deepcopy(next(e for key, e in self.corrected.items() if key.startswith("sora-")))

    def test_all_four_corrected_residuals_validate_individually(self):
        self.assertEqual(len(self.corrected), 4)
        for event in self.corrected.values():
            with self.subTest(event=event["id"]):
                normalized, _ = normalize(event)
                validate_canonical({"schema_version": 3, "events": [normalized]})

    def test_nonstandard_missing_labels_are_rejected(self):
        labels = ("individual_septet_personnel", "individual_chorus_personnel", "verified event-specific music charge", "complete verified 2026 touring personnel")
        for label in labels:
            event = self.sora()
            event["enrichment"]["missing"].append(label)
            with self.subTest(label=label), self.assertRaises(SystemExit):
                validate_enrichment(event, event["id"])

    def test_partial_status_is_rejected_for_sora_and_cortex(self):
        for event in self.original.values():
            if event["id"].startswith(("sora-", "cortex-")):
                with self.subTest(event=event["id"]), self.assertRaises(SystemExit):
                    validate_enrichment(event, event["id"])

    def test_special_guest_belongs_in_note_not_missing(self):
        original = next(e for key, e in self.original.items() if key.startswith("interpretations-"))
        with self.assertRaises(SystemExit):
            validate_enrichment(original, original["id"])
        corrected = self.corrected[original["id"]]
        self.assertEqual(corrected["enrichment"]["missing"], ["apple_music"])
        self.assertEqual(original["enrichment"]["note"], corrected["enrichment"]["note"])
        self.assertIn("special guest remains unannounced", corrected["enrichment"]["note"])

    def test_missing_describes_exactly_absent_link_components(self):
        for event in self.corrected.values():
            missing = {k for k in ("official_event", "official_tickets") if not event["links"].get(k)}
            if not any(e.get("apple_music_url") for e in event["recommended_listening"]):
                missing.add("apple_music")
            self.assertEqual(set(event["enrichment"]["missing"]), missing, event["id"])
            self.assertEqual(event["enrichment"]["status"], "pending")

    def test_explicit_usd_and_jpy_are_accepted_without_conversion(self):
        for currency in ("USD", "JPY"):
            event, _ = normalize(self.sora())
            event["tickets"]["currency"] = currency
            validate_canonical({"schema_version": 3, "events": [event]})
            self.assertEqual(event["tickets"]["official"]["minimum"], 5500)

    def test_unknown_null_and_implicit_currency_are_rejected(self):
        for value in (None, "", "jpy", "EUR", "YEN", 392, [], {}):
            event, _ = normalize(self.sora())
            event["tickets"]["currency"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "explicit supported ticket currency"):
                validate_canonical({"schema_version": 3, "events": [event]})
        del event["tickets"]["currency"]
        with self.assertRaisesRegex(ValueError, "explicit supported ticket currency"):
            validate_canonical({"schema_version": 3, "events": [event]})

    def test_sora_price_is_source_bound_and_no_ticket_url_is_invented(self):
        event = self.sora()
        self.assertEqual(self.original[event["id"]]["tickets"]["currency"], "JPY")
        self.assertEqual(event["tickets"]["currency"], "JPY")
        price = event["tickets"]["official"]
        self.assertEqual((price["minimum"], price["maximum"]), (5500, 5500))
        self.assertEqual(price["checked_on"], "2026-09-11")
        self.assertEqual(price["source_url"], "https://alfie.tokyo/schedule/202609.html")
        self.assertIn(price["source_url"], [s["url"] for s in event["sources"]])
        self.assertIsNone(event["links"]["official_tickets"])

    def test_every_unapproved_event_field_is_unchanged(self):
        for event_id, event in self.corrected.items():
            before = self.original[event_id]
            allowed = {"enrichment"}
            if event_id.startswith("sora-"):
                allowed |= {"tickets", "sources"}
            elif event_id.startswith("wycliffe-"):
                allowed |= {"sources"}
            self.assertEqual({k:v for k,v in before.items() if k not in allowed}, {k:v for k,v in event.items() if k not in allowed})
            self.assertEqual(event["sources"][:len(before["sources"])], before["sources"])


if __name__ == "__main__":
    unittest.main()
