"""RADAR scene assignments, ordering, and complete filter partition."""

import json
import shutil
import subprocess
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from scripts.venue_identity import RADAR_AREAS, VenueIdentityError, load_registry


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


class RadarAreaRegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.events = json.loads((ROOT / "radar/events.json").read_text())["events"]

    def test_all_venues_have_one_controlled_area_and_events_inherit_it(self):
        venues = self.registry["venues"]
        self.assertTrue(all(identity["radar_area"] in RADAR_AREAS for identity in venues.values()))
        inherited = defaultdict(set)
        for event in self.events:
            inherited[event["venue"]["id"]].add(venues[event["venue"]["id"]]["radar_area"])
        self.assertTrue(all(len(areas) == 1 for areas in inherited.values()))
        self.assertEqual(sum(len(areas) for areas in inherited.values()), len(inherited))

    def test_documented_places_and_brooklyn_are_grouped_without_changing_facts(self):
        expected = {
            ("US", "DC", "Washington, DC"): "dmv",
            ("US", "MD", "Columbia"): "dmv",
            ("US", "MD", "North Bethesda"): "dmv",
            ("US", "MD", "Oxon Hill"): "dmv",
            ("US", "MD", "Rockville"): "dmv",
            ("US", "MD", "Silver Spring"): "dmv",
            ("US", "MD", "Takoma Park"): "dmv",
            ("US", "VA", "Alexandria"): "dmv",
            ("US", "VA", "Annandale"): "dmv",
            ("US", "VA", "Tysons"): "dmv",
            ("US", "VA", "Vienna"): "dmv",
            ("US", "MD", "Baltimore"): "baltimore",
            ("US", "PA", "Philadelphia"): "philadelphia",
            ("US", "NJ", "Newark"): "newark",
            ("US", "NJ", "Holmdel"): "new_jersey",
            ("US", "NY", "Brooklyn"): "new_york",
            ("US", "NY", "Flushing"): "new_york",
            ("US", "NY", "Queens"): "new_york",
            ("US", "NY", "New York"): "new_york",
            ("JP", "Kanagawa", "Kawasaki"): "kanagawa",
            ("JP", "Kanagawa", "Yokohama"): "kanagawa",
            ("JP", "Saitama", "Soka"): "saitama",
            ("JP", "Saitama", "Okegawa"): "saitama",
        }
        found = set()
        for identity in self.registry["venues"].values():
            location = tuple(identity[key] for key in ("country", "state", "city"))
            if location in expected:
                found.add(location)
                self.assertEqual(identity["radar_area"], expected[location], location)
            if identity["country"] == "JP" and identity["state"] == "Tokyo":
                self.assertEqual(identity["radar_area"], "tokyo", location)
        self.assertEqual(found, set(expected))
        columbia = next(event for event in self.events if event["venue"]["city"] == "Columbia")
        self.assertEqual(columbia["geography"], "Regional")
        self.assertEqual(columbia["geographic_domain"], "us_corridor")
        self.assertTrue(columbia["editorial"]["en"]["trip_verdict"])
        self.assertTrue(columbia["editorial"]["es"]["trip_verdict"])

    def test_missing_or_invalid_registry_area_fails_validation(self):
        for value in (None, "tokyo-ish", 7):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                payload = json.loads((ROOT / "radar/venue_identities.json").read_text())
                identity = payload["venues"]["the-anthem-washington-dc"]
                if value is None:
                    identity.pop("radar_area")
                else:
                    identity["radar_area"] = value
                path = Path(directory) / "registry.json"
                path.write_text(json.dumps(payload))
                with self.assertRaisesRegex(VenueIdentityError, "radar_area"):
                    load_registry(path)

    def test_unassigned_is_valid_for_a_reviewable_future_venue(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = json.loads((ROOT / "radar/venue_identities.json").read_text())
            payload["venues"]["the-anthem-washington-dc"]["radar_area"] = "unassigned"
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(payload))
            self.assertEqual(load_registry(path)["venues"]["the-anthem-washington-dc"]["radar_area"], "unassigned")


class RadarAreaBehaviorTest(unittest.TestCase):
    def test_order_partition_future_fallback_and_signal(self):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const fs = require('fs');
const logic = require('./radar/app.js');
const events = JSON.parse(fs.readFileSync('./radar/events.json', 'utf8')).events;
const registry = JSON.parse(fs.readFileSync('./radar/venue_identities.json', 'utf8'));
const signal = logic.resolveSignalState(JSON.parse(fs.readFileSync('./radar/signals.json', 'utf8')), events).current?.event || null;
const today = '2026-09-15';
const base = {radar_area:'', venue:'', priority:'', view:'upcoming'};
const check = (state, eventList=events, table=registry) => logic.deriveRadarView(eventList, state, signal, today, table);
const partitions = {};
for (const view of ['upcoming', 'archive']) {
  const all = check({...base, view});
  const buckets = logic.availableAreas(all.viewEvents, registry).map(area => ({area, model:check({...base, view, radar_area:area})}));
  partitions[view] = {
    viewIds:all.viewEvents.map(event => event.id),
    areaOrder:buckets.map(bucket => bucket.area),
    bucketIds:buckets.flatMap(bucket => bucket.model.selected.map(event => event.id)),
    counts:buckets.map(bucket => bucket.model.selected.length),
    signalVisible:all.signalVisible,
    unfilteredResults:all.results.map(event => event.id),
  };
}
const future = {...events[0], id:'future-venue-2027', status:'considering', dates:{start:'2027-01-01',end:null}, venue:{...events[0].venue,id:'future-venue-id',name:'Future room',city:'Future town'}};
const futureModel = check({...base,radar_area:'unassigned'}, [future]);
const areaModel = check({...base,radar_area:'kanagawa'});
const signalArea = signal && logic.radarAreaFor(signal, registry);
const filteredSignal = signal && logic.deriveRadarView(events, {...base,radar_area:signalArea}, signal, '2026-08-25', registry);
const combined = check({...base,radar_area:'dmv',venue:'Blues Alley',priority:'A'});
console.log(JSON.stringify({partitions, labels:{en:logic.COPY.en.areas,es:logic.COPY.es.areas}, futureArea:logic.radarAreaFor(future,registry), futureIds:futureModel.selected.map(event=>event.id), futureOptions:logic.availableAreas([future],registry), kanagawaIds:areaModel.selected.map(event=>event.id), combined:combined.selected.map(event=>({id:event.id, venue:event.venue.name, priority:event.priority})), filteredSignalVisible:filteredSignal?.signalVisible, filteredSignalCount:filteredSignal?.results.filter(event=>event.id===signal.id).length, signalId:signal?.id}));
"""
        result = subprocess.run([NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        for view, part in report["partitions"].items():
            with self.subTest(view=view):
                self.assertCountEqual(part["bucketIds"], part["viewIds"])
                self.assertEqual(len(part["bucketIds"]), len(set(part["bucketIds"])))
                self.assertEqual(sum(part["counts"]), len(part["viewIds"]))
                order = part["areaOrder"]
                corridor = [name for name in ("dmv", "baltimore", "philadelphia", "newark", "new_york") if name in order]
                self.assertEqual(order[:len(corridor)], corridor)
                if view == "archive":
                    self.assertFalse(part["signalVisible"])
        self.assertEqual(report["futureArea"], "unassigned")
        self.assertEqual(report["futureIds"], ["future-venue-2027"])
        self.assertEqual(report["futureOptions"], ["unassigned"])
        self.assertEqual(report["labels"]["en"]["dmv"], "DMV / local scene")
        self.assertEqual(report["labels"]["es"]["dmv"], "DMV / escena local")
        self.assertEqual(report["labels"]["es"]["tokyo"], "Tokio")
        self.assertNotEqual(report["labels"]["es"]["new_york"], report["labels"]["es"]["newark"])
        self.assertTrue(report["kanagawaIds"])
        self.assertFalse(report["filteredSignalVisible"])
        self.assertEqual(report["filteredSignalCount"], 1)
        self.assertTrue(all(item["venue"] == "Blues Alley" and item["priority"] == "A" for item in report["combined"]))
        for page in ("radar/index.html", "radar/es/index.html"):
            html = (ROOT / page).read_text()
            self.assertIn('id="count" role="status" aria-live="polite"', html)
        source = (ROOT / "radar/app.js").read_text()
        self.assertIn("setAttribute('aria-pressed'", source)
        self.assertIn("setAttribute('role', 'group')", source)


if __name__ == "__main__":
    unittest.main()
