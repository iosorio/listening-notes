import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.set_signal import SignalTransitionError, atomic_write_json, main as set_signal_main, transition_signal
from scripts.validate_signals import SignalValidationError, validate_signals


def event(event_id, priority="S", final_date="2099-12-31"):
    official = f"https://venue.example/events/{event_id}"
    return {
        "id": event_id,
        "artist": event_id.replace("-", " ").title(),
        "dates": {"start": final_date, "end": None},
        "venue": {"id": "venue-city", "name": "Venue", "city": "City", "state": "ST", "country": "US"},
        "priority": priority,
        "links": {"official_event": official, "official_tickets": None},
        "sources": [{"url": official, "publisher": "Official venue", "checked_on": "2099-01-01"}],
        "editorial": {
            "en": {"why_it_matters": "A durable reason this event belongs on RADAR."},
            "es": {"why_it_matters": "Una razón duradera para incluir esta fecha en RADAR."},
        },
    }


def reason(recorded_on, text="A documented urgent editorial reason."):
    return {
        "recorded_on": recorded_on,
        "editorial": {
            "en": {"reason": text},
            "es": {"reason": "Una razón editorial urgente y documentada."},
        },
    }


def record(event_id, activated_on, minimum_until, replaced_on=None, replaced_by=None):
    return {
        "signal_id": f"signal-{activated_on}-{event_id}",
        "event_id": event_id,
        "activated_on": activated_on,
        "minimum_until": minimum_until,
        "action_deadline": None,
        "replaced_on": replaced_on,
        "replaced_by": replaced_by,
        "editorial": {
            "en": {"why_now": "A specific reason this event needs attention now."},
            "es": {"why_now": "Una razón específica para prestar atención a esta fecha ahora."},
        },
        "early_replacement_override": None,
        "reentry_material_change": None,
    }


class SignalValidationTest(unittest.TestCase):
    def setUp(self):
        self.events = {"schema_version": 3, "events": [event("artist-one-2099"), event("artist-two-2099", "A+")]}
        self.signals = {"schema_version": 1, "signals": [record("artist-one-2099", "2099-01-01", "2099-01-08")]}

    def test_valid_current_signal(self):
        validate_signals(self.signals, self.events)

    def test_reference_priority_and_official_page_are_required(self):
        for mutation in ("reference", "priority", "official"):
            signals = deepcopy(self.signals)
            events = deepcopy(self.events)
            if mutation == "reference":
                signals["signals"][0]["event_id"] = "missing-event-2099"
            elif mutation == "priority":
                events["events"][0]["priority"] = "A"
            else:
                events["events"][0]["links"]["official_event"] = "https://venue.example/"
            with self.subTest(mutation=mutation), self.assertRaises(SignalValidationError):
                validate_signals(signals, events)

    def test_bilingual_why_now_is_required_and_must_be_distinct(self):
        missing = deepcopy(self.signals)
        missing["signals"][0]["editorial"]["es"]["why_now"] = ""
        with self.assertRaisesRegex(SignalValidationError, "nonempty native-language"):
            validate_signals(missing, self.events)
        duplicate = deepcopy(self.signals)
        duplicate["signals"][0]["editorial"]["en"]["why_now"] = self.events["events"][0]["editorial"]["en"]["why_it_matters"]
        with self.assertRaisesRegex(SignalValidationError, "distinct"):
            validate_signals(duplicate, self.events)

    def test_minimum_cycle_uses_event_or_action_deadline_exception(self):
        deadline = deepcopy(self.signals)
        deadline["signals"][0]["action_deadline"] = "2099-01-04"
        deadline["signals"][0]["minimum_until"] = "2099-01-04"
        validate_signals(deadline, self.events)
        bad = deepcopy(deadline)
        bad["signals"][0]["minimum_until"] = "2099-01-03"
        with self.assertRaisesRegex(SignalValidationError, "seven-day cycle"):
            validate_signals(bad, self.events)

        event_limited = {"schema_version": 3, "events": [event("artist-one-2099", final_date="2099-01-05")]}
        event_signal = {"schema_version": 1, "signals": [record("artist-one-2099", "2099-01-01", "2099-01-05")]}
        validate_signals(event_signal, event_limited)

    def test_early_replacement_requires_bilingual_override(self):
        second_id = "signal-2099-01-04-artist-two-2099"
        history = deepcopy(self.signals)
        history["signals"][0].update({"replaced_on": "2099-01-04", "replaced_by": second_id})
        history["signals"].append(record("artist-two-2099", "2099-01-04", "2099-01-11"))
        with self.assertRaisesRegex(SignalValidationError, "early_replacement_override"):
            validate_signals(history, self.events)
        history["signals"][0]["early_replacement_override"] = reason("2099-01-04")
        validate_signals(history, self.events)

    def test_chronology_and_replaced_by_must_match_next_record(self):
        next_record = record("artist-two-2099", "2099-01-08", "2099-01-15")
        history = deepcopy(self.signals)
        history["signals"][0].update({"replaced_on": "2099-01-08", "replaced_by": "wrong-record"})
        history["signals"].append(next_record)
        with self.assertRaisesRegex(SignalValidationError, "replaced_by"):
            validate_signals(history, self.events)

    def test_reentry_within_30_days_requires_material_change(self):
        first = record(
            "artist-one-2099", "2099-01-01", "2099-01-08", "2099-01-08",
            "signal-2099-01-08-artist-two-2099",
        )
        second = record(
            "artist-two-2099", "2099-01-08", "2099-01-15", "2099-01-15",
            "signal-2099-01-15-artist-one-2099",
        )
        reentry = record("artist-one-2099", "2099-01-15", "2099-01-22")
        history = {"schema_version": 1, "signals": [first, second, reentry]}
        with self.assertRaisesRegex(SignalValidationError, "reentry_material_change"):
            validate_signals(history, self.events)
        reentry["reentry_material_change"] = reason("2099-01-15", "The lineup materially changed.")
        validate_signals(history, self.events)

    def test_exactly_one_current_record_is_required(self):
        invalid = deepcopy(self.signals)
        invalid["signals"].append(record("artist-two-2099", "2099-01-08", "2099-01-15"))
        with self.assertRaisesRegex(SignalValidationError, "exactly one"):
            validate_signals(invalid, self.events)


class SetSignalTest(unittest.TestCase):
    def setUp(self):
        self.events = {"schema_version": 3, "events": [event("artist-one-2099"), event("artist-two-2099", "A+")]}
        self.signals = {"schema_version": 1, "signals": [record("artist-one-2099", "2099-01-01", "2099-01-08")]}

    def test_transition_closes_only_current_and_adds_valid_record(self):
        before = deepcopy(self.signals["signals"][:-1])
        proposed, report = transition_signal(
            self.signals, self.events, "artist-two-2099", "2099-01-08",
            "Tickets now require a decision.", "Los boletos ya exigen una decisión.",
        )
        self.assertEqual(proposed["signals"][:-2], before)
        self.assertEqual(proposed["signals"][0]["replaced_on"], "2099-01-08")
        self.assertEqual(report["to"]["event_id"], "artist-two-2099")
        self.assertFalse(report["early_replacement"])
        validate_signals(proposed, self.events)

    def test_helper_enforces_urgent_override_and_bilingual_pairs(self):
        with self.assertRaisesRegex(SignalTransitionError, "urgent-override copy is required"):
            transition_signal(
                self.signals, self.events, "artist-two-2099", "2099-01-04",
                "A new urgency.", "Hay una urgencia nueva.",
            )
        with self.assertRaisesRegex(SignalTransitionError, "both English and Spanish"):
            transition_signal(
                self.signals, self.events, "artist-two-2099", "2099-01-04",
                "A new urgency.", "Hay una urgencia nueva.", urgent_override_en="Urgent.",
            )

    def test_dry_run_does_not_write(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            signal_path = root / "signals.json"
            event_path = root / "events.json"
            signal_path.write_text(json.dumps(self.signals) + "\n")
            event_path.write_text(json.dumps(self.events) + "\n")
            before = signal_path.read_bytes()
            result = set_signal_main([
                "artist-two-2099", "--activated-on", "2099-01-08",
                "--why-now-en", "Tickets now require a decision.",
                "--why-now-es", "Los boletos ya exigen una decisión.",
                "--signals", str(signal_path), "--events", str(event_path), "--dry-run",
            ])
            self.assertEqual(result, 0)
            self.assertEqual(signal_path.read_bytes(), before)

    def test_atomic_write_replaces_complete_json(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "signals.json"
            path.write_text('{"old": true}\n')
            atomic_write_json(path, self.signals)
            self.assertEqual(json.loads(path.read_text()), self.signals)
            self.assertEqual(list(path.parent.glob(".signals.json.*")), [])

    def test_atomic_write_failure_preserves_original(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "signals.json"
            path.write_text('{"old": true}\n')
            before = path.read_bytes()
            with patch("scripts.set_signal.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    atomic_write_json(path, self.signals)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob(".signals.json.*")), [])


if __name__ == "__main__":
    unittest.main()
