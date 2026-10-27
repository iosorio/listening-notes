import json
import shutil
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.audit_enrichment import audit

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


class LatestAdditionsTest(unittest.TestCase):
    def test_ingestion_order_unknown_dates_and_return_visits(self):
        if not Path(NODE).exists():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const assert = require('node:assert/strict');
const {latestAdditions, additionsSince} = require('./radar/app.js');
const events = Array.from({length: 8}, (_, i) => ({id:`event-${i}`, canonicalized_at:`2026-10-${10+i}T12:00:00Z`, dates:{start:`2027-01-${20-i}`}, discovered_at:'2026-01-01T00:00:00Z'}));
events.push({id:'unknown', dates:{start:'2099-12-31'}, published_at:'2099-01-01T00:00:00Z'});
events.push({id:'invalid',canonicalized_at:'yesterday'});
events.push({id:'no-zone',canonicalized_at:'2099-01-01T12:00:00'});
const before = JSON.stringify(events);
assert.deepEqual(latestAdditions(events).map(e=>e.id),['event-7','event-6','event-5','event-4','event-3','event-2']);
assert.deepEqual(additionsSince(events,'2026-10-16T12:00:00Z').map(e=>e.id),['event-7']);
assert.deepEqual(additionsSince(events,null),[]);
assert.deepEqual(latestAdditions([{id:'b',canonicalized_at:events[0].canonicalized_at},{id:'a',canonicalized_at:events[0].canonicalized_at}]).map(e=>e.id),['a','b']);
assert.equal(JSON.stringify(events),before);
assert.deepEqual(latestAdditions([]),[]);
"""
        subprocess.run([NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True)

    def test_backlog_is_explicit_and_does_not_change_data(self):
        events = [
            {"id": "pending", "artist": "A", "dates": {"start": "2026-12-01"}, "enrichment": {"status": "pending", "missing": ["apple_music"], "note": "Catalog review pending."}},
            {"id": "verified", "artist": "B", "dates": {"start": "2026-12-02"}, "recommended_listening": [{"apple_music_url": "https://music.apple.com/us/album/verified/123"}]},
            {"id": "past", "artist": "C", "dates": {"start": "2026-01-01"}},
            {"id": "profile-only", "artist": "D", "dates": {"start": "2026-12-03"}, "recommended_listening": [{"apple_music_url": "https://music.apple.com/us/artist/profile/123"}]},
        ]
        before = deepcopy(events)
        result = audit(events, "2026-10-27")
        self.assertEqual(result["missing_apple_music"], 2)
        self.assertEqual([row["id"] for row in result["events"]], ["pending", "profile-only"])
        self.assertEqual(result["events"][0]["note"], "Catalog review pending.")
        self.assertEqual(events, before)
