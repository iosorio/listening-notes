"""Public RADAR must hide explicitly retracted events without changing canon."""
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from scripts.validate_editorial_exclusions import validate

ROOT = Path(__file__).resolve().parents[1]
LEDGER = json.loads((ROOT / "radar/editorial_exclusions.json").read_text())
CANONICAL = json.loads((ROOT / "radar/events.json").read_text())

class EditorialRetractionTests(unittest.TestCase):
    def test_original_event_stays_in_canonical(self):
        before = deepcopy(CANONICAL)
        self.assertEqual(validate(LEDGER, CANONICAL), 1)
        record = next(e for e in CANONICAL["events"] if e["id"] == LEDGER["exclusions"][0]["event_id"])
        self.assertTrue(record["discovered_at"] and record["published_at"] and record["canonicalized_at"])
        self.assertEqual(before, CANONICAL)

    def test_reject_invalid_and_duplicate_retractions(self):
        duplicate = deepcopy(LEDGER)
        duplicate["exclusions"].append(deepcopy(duplicate["exclusions"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(duplicate, CANONICAL)
        unknown = deepcopy(LEDGER)
        unknown["exclusions"][0]["event_id"] = "unknown-event-2026"
        with self.assertRaisesRegex(ValueError, "unknown canonical"):
            validate(unknown, CANONICAL)

    def test_excluded_from_all_views_latest_and_signal(self):
        code = r"""
const assert=require('node:assert/strict');
const ui=require('./radar/app.js');
const canonical=require('./radar/events.json').events;
const ledger=require('./radar/editorial_exclusions.json');
const id=ledger.exclusions[0].event_id;
const visible=ui.applyEditorialExclusions(canonical,ledger);
assert(canonical.some(e=>e.id===id));
assert.equal(canonical.length-visible.length,1);
assert(!visible.some(e=>e.id===id));
for(const view of ['archive','upcoming']){
 const m=ui.deriveRadarView(visible,{view,radar_area:'',venue:'',priority:''},null,'2026-10-31',{});
 assert(!m.viewEvents.some(e=>e.id===id));
 assert(!m.results.some(e=>e.id===id));
}
assert(!ui.latestAdditions(visible,9999).some(e=>e.id===id));
assert(!ui.additionsSince(visible,'2026-10-30T00:00:00Z').some(e=>e.id===id));
assert.equal(ui.resolveSignalState({schema_version:1,signals:[{event_id:id,replaced_on:null,replaced_by:null}]},visible).valid,false);
assert.deepEqual(ui.applyEditorialExclusions(visible,ledger),visible);
assert.throws(()=>ui.applyEditorialExclusions(canonical,null),/Invalid/);
assert.throws(()=>ui.applyEditorialExclusions(canonical,{schema_version:1,exclusions:[ledger.exclusions[0],ledger.exclusions[0]]}),/duplicate/);
"""
        result=subprocess.run(["node","-e",code],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
