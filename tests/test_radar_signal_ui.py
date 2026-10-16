import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path

from scripts.merge_inbox import semantic_duplicate


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


class StructureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.markers = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if "controls" in classes:
            self.markers.append("controls")
        for marker in ("signal", "recent-signals", "radar"):
            if attributes.get("id") == marker:
                self.markers.append(marker)


class RadarSignalStructureTest(unittest.TestCase):
    def test_signal_controls_recent_and_results_have_required_dom_order(self):
        for relative in ("radar/index.html", "radar/es/index.html"):
            parser = StructureParser()
            parser.feed((ROOT / relative).read_text())
            with self.subTest(page=relative):
                self.assertEqual(parser.markers, ["signal", "controls", "recent-signals", "radar"])

    def test_archive_deep_link_remains_in_bilingual_navigation(self):
        for relative in ("radar/index.html", "radar/es/index.html"):
            html = (ROOT / relative).read_text()
            with self.subTest(page=relative):
                self.assertIn('href="?view=archive"', html)

    def test_dynamic_signal_selector_is_removed(self):
        source = (ROOT / "radar/app.js").read_text()
        self.assertNotIn("chooseSignal", source)
        self.assertIn("fetchJson(signalUrl).catch(() => null)", source)
        self.assertIn("resolveSignalState", source)


class RadarSignalBehaviorTest(unittest.TestCase):
    def venue_fixture(self):
        def event(event_id, venue_id, venue_name, start="2026-10-01", status="considering"):
            return {
                "id": event_id, "artist": event_id, "subtitle": None,
                "venue": {"id": venue_id, "name": venue_name, "city": "Washington, DC"},
                "dates": {"start": start, "end": None}, "status": status, "priority": "A",
            }

        # Exercise venue identity with a fixed catalog, independent of live intake.
        return [
            event("blues-first", "blues-alley-washington-dc", "Blues Alley"),
            event("blues-new", "blues-alley-washington-dc", "Blues Alley", "2026-11-25"),
            event("same-name-other-id", "other-room", "Blues Alley"),
            event("blues-past", "blues-alley-washington-dc", "Blues Alley", "2026-08-01"),
            event("blues-attended", "blues-alley-washington-dc", "Blues Alley", status="attended"),
            event("wharf-show", "the-wharf-washington-dc", "The Wharf"),
            event("tsuyoshi-yamamoto-trio-yokohama-jazz-first-2026-08-28", "yokohama-jazz-first-yokohama", "Jazz First", "2026-08-28"),
        ]

    def model_report(self, events=None):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const fs = require('fs');
const logic = require('./radar/app.js');
const events = JSON.parse(fs.readFileSync(0, 'utf8'));
const venues = JSON.parse(fs.readFileSync('./radar/venue_identities.json', 'utf8'));
const signals = JSON.parse(fs.readFileSync('./radar/signals.json', 'utf8'));
const resolved = logic.resolveSignalState(signals, events);
const today = '2026-08-25';
const base = {radar_area: '', venue: '', priority: '', view: 'upcoming'};
const report = state => {
  const model = logic.deriveRadarView(events, state, resolved.current && resolved.current.event, today, venues);
  return {
    signalVisible: model.signalVisible,
    count: model.results.length,
    selectedCount: model.selected.length,
    viewCount: model.viewEvents.length,
    ids: model.results.map(event => event.id),
    artists: model.results.map(event => event.artist),
    events: model.results.map(({id, artist, subtitle, dates, venue}) => ({id, artist, subtitle, dates, venue})),
  };
};
const failed = logic.resolveSignalState(null, events);
const failedModel = logic.deriveRadarView(events, base, failed.current, today, venues);
console.log(JSON.stringify({
  resolved: {valid: resolved.valid, recentCount: resolved.recent.length, current: resolved.current && resolved.current.event.id},
  unfiltered: report(base),
  bluesAlley: report({...base, venue: 'blues-alley-washington-dc'}),
  wharf: report({...base, venue: 'the-wharf-washington-dc'}),
  area: report({...base, radar_area: 'dmv'}),
  priority: report({...base, priority: 'S'}),
  archive: report({...base, view: 'archive'}),
  failed: {signalVisible: failedModel.signalVisible, ids: failedModel.results.map(event => event.id)}
}));
"""
        result = subprocess.run(
            [NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True,
            input=json.dumps(events if events is not None else json.loads(
                (ROOT / "radar/events.json").read_text()
            )["events"]),
        )
        return json.loads(result.stdout)

    def test_explicit_signal_and_zero_history_resolve(self):
        report = self.model_report()
        self.assertTrue(report["resolved"]["valid"])
        self.assertEqual(report["resolved"]["current"], "tsuyoshi-yamamoto-trio-yokohama-jazz-first-2026-08-28")
        self.assertEqual(report["resolved"]["recentCount"], 0)

    def test_unfiltered_upcoming_excludes_only_visible_current_signal(self):
        report = self.model_report()
        current = report["resolved"]["current"]
        self.assertTrue(report["unfiltered"]["signalVisible"])
        self.assertNotIn(current, report["unfiltered"]["ids"])
        self.assertFalse(report["failed"]["signalVisible"])
        self.assertIn(current, report["failed"]["ids"])

    def test_blues_alley_filter_uses_canonical_identity_and_upcoming_view(self):
        models = self.model_report(self.venue_fixture())
        self.assertTrue(models["unfiltered"]["signalVisible"])
        report = models["bluesAlley"]
        ids = set(report["ids"])
        self.assertFalse(report["signalVisible"])
        self.assertEqual(ids, {"blues-first", "blues-new"})
        self.assertEqual(report["count"], len(ids))
        self.assertEqual(len(report["ids"]), len(ids))
        self.assertTrue(all(event["venue"]["id"] == "blues-alley-washington-dc" for event in report["events"]))
        for left, right in combinations(report["events"], 2):
            self.assertFalse(
                semantic_duplicate(left, right),
                f"Blues Alley filter contains a semantic duplicate: {left['id']} / {right['id']}",
            )

    def test_the_wharf_filter_returns_its_single_normal_result(self):
        report = self.model_report(self.venue_fixture())["wharf"]
        self.assertFalse(report["signalVisible"])
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["ids"], ["wharf-show"])

    def test_every_filter_and_archive_hide_signal(self):
        report = self.model_report()
        for key in ("area", "priority", "archive"):
            with self.subTest(state=key):
                self.assertFalse(report[key]["signalVisible"])


if __name__ == "__main__":
    unittest.main()
