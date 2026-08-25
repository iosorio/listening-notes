import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path


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
    def test_controls_signal_recent_and_results_have_required_dom_order(self):
        for relative in ("radar/index.html", "radar/es/index.html"):
            parser = StructureParser()
            parser.feed((ROOT / relative).read_text())
            with self.subTest(page=relative):
                self.assertEqual(parser.markers, ["controls", "signal", "recent-signals", "radar"])

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
    def model_report(self):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const fs = require('fs');
const logic = require('./radar/app.js');
const events = JSON.parse(fs.readFileSync('./radar/events.json', 'utf8')).events;
const signals = JSON.parse(fs.readFileSync('./radar/signals.json', 'utf8'));
const resolved = logic.resolveSignalState(signals, events);
const today = '2026-08-25';
const base = {city: '', venue: '', priority: '', view: 'upcoming'};
const report = state => {
  const model = logic.deriveRadarView(events, state, resolved.current && resolved.current.event, today);
  return {signalVisible: model.signalVisible, count: model.results.length, ids: model.results.map(event => event.id), artists: model.results.map(event => event.artist)};
};
const failed = logic.resolveSignalState(null, events);
const failedModel = logic.deriveRadarView(events, base, failed.current, today);
console.log(JSON.stringify({
  resolved: {valid: resolved.valid, recentCount: resolved.recent.length, current: resolved.current && resolved.current.event.id},
  unfiltered: report(base),
  bluesAlley: report({...base, venue: 'Blues Alley'}),
  wharf: report({...base, venue: 'The Wharf'}),
  city: report({...base, city: 'Washington, DC'}),
  priority: report({...base, priority: 'S'}),
  archive: report({...base, view: 'archive'}),
  failed: {signalVisible: failedModel.signalVisible, ids: failedModel.results.map(event => event.id)}
}));
"""
        result = subprocess.run(
            [NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True
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

    def test_blues_alley_filter_returns_all_eight_as_normal_results(self):
        report = self.model_report()["bluesAlley"]
        self.assertFalse(report["signalVisible"])
        self.assertEqual(report["count"], 8)
        self.assertIn("Nanny Assis ‘Afro-Jobim’ feat. Toninho Horta", report["artists"])

    def test_the_wharf_filter_returns_its_single_normal_result(self):
        report = self.model_report()["wharf"]
        self.assertFalse(report["signalVisible"])
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["artists"], ["African Rhythms Alumni Quintet"])

    def test_every_filter_and_archive_hide_signal(self):
        report = self.model_report()
        for key in ("city", "priority", "archive"):
            with self.subTest(state=key):
                self.assertFalse(report[key]["signalVisible"])


if __name__ == "__main__":
    unittest.main()
