"""Contextual RADAR facets against fixed view and Signal fixtures."""

import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node") or str(Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


class RadarFacetBehaviorTest(unittest.TestCase):
    def test_contextual_facets_transitions_views_and_signal(self):
        if not Path(NODE).is_file():
            self.skipTest("Node.js runtime is unavailable")
        script = r"""
const assert = require('node:assert/strict');
const logic = require('./radar/app.js');
const registry = {venues:{
  blues:{name:'Blues Alley',radar_area:'dmv'},
  blue:{name:'Blue Note Jazz Club',radar_area:'new_york'},
  signal:{name:'Signal room',radar_area:'kanagawa'},
  old:{name:'Archive room',radar_area:'dmv'},
  twin:{name:'Blues Alley',radar_area:'new_york'}
}};
const event = (id, venue, priority, start, status='considering') => ({
  id, venue:{id:venue,name:registry.venues[venue]?.name || 'New room',city:'Ignored city'},
  priority, dates:{start,end:null}, status
});
const events = [
  event('blues-a','blues','A','2026-10-01'),
  event('blues-aplus','blues','A+','2026-10-02'),
  event('blue-s','blue','S','2026-10-03'),
  event('twin-splus','twin','S+','2026-10-04'),
  event('signal-aplus','signal','A+','2026-10-05'),
  event('old-a','old','A','2026-08-01','passed'),
  event('old-splus','old','S+','2026-08-02','attended'),
  {id:'unassigned-a',venue:{id:'missing',name:'New room',city:'Washington, DC'},priority:'A',dates:{start:'2026-10-06',end:null},status:'considering'}
];
const today = '2026-09-15';
const base = {radar_area:'',venue:'',priority:'',view:'upcoming'};
const view = state => logic.deriveRadarView(events,state,events[4],today,registry);
const counts = state => {
  const options = {radar_area:logic.availableAreas(view(state).viewEvents,registry),venue:['blues','blue','signal','old','twin','missing'],priority:['S+','S','A+','A']};
  return logic.facetCounts(view(state).viewEvents,state,registry,options);
};
const dmv = {...base,radar_area:'dmv'};
assert.equal(counts(dmv).venue.get('blue'),0,'DMV must disable Blue Note');
assert.equal(counts(dmv).venue.get('blues'),2);
assert.equal(counts(dmv).venue.get('twin'),0,'identical display names must not merge IDs');
assert.deepEqual(logic.visibleFacetValues(['blue','blues','twin'],counts(dmv).venue,''),['blues'],'zero-match venues leave the DOM');
assert.deepEqual(logic.visibleFacetValues(['blue','blues','twin'],counts(dmv).venue,'blue'),['blue','blues'],'a selected zero-match venue stays visible');
assert.equal(view({...dmv,venue:'blue'}).selected.length,0);
const blues = logic.selectFacet(base,'venue','blues',registry);
assert.equal(blues.radar_area,'dmv');
assert.equal(blues.venue,'blues');
assert.equal(view(blues).selected.length,2);
assert.deepEqual(logic.selectFacet(blues,'radar_area','dmv',registry),blues,'same area keeps venue');
const newYork = logic.selectFacet(blues,'radar_area','new_york',registry);
assert.equal(newYork.venue,'');
assert.equal(counts(newYork).venue.get('blue'),1);
const allAreas = logic.selectFacet(blues,'radar_area','',registry);
assert.equal(allAreas.venue,'');
assert.equal(allAreas.radar_area,'');
const allVenues = logic.selectFacet(blues,'venue','',registry);
assert.equal(allVenues.venue,'');
assert.equal(allVenues.radar_area,'dmv');
const aSelected = {...blues,priority:'A'};
assert.equal(counts(aSelected).priority.get('A+'),1,'priority replaces A');
assert.equal(counts(aSelected).priority.get('A'),1);
assert.equal(counts(aSelected).priority.get('S'),0);
assert.equal(counts(aSelected).priority.get('S+'),0);
assert.equal(counts(aSelected).radar_area.get('new_york'),0,'scene remains available as a disabled navigation value');
assert.deepEqual(logic.visibleFacetValues(['S+','S','A+','A'],counts(aSelected).priority,'A'),['A+','A']);
assert.deepEqual(logic.visibleFacetValues(['S+','S','A+','A'],counts(aSelected).priority,'S'),['S','A+','A'],'a selected zero-match priority stays visible');
assert.equal(logic.selectFacet(aSelected,'priority','A+',registry).priority,'A+');
const archive = {...base,view:'archive'};
assert.equal(view(archive).viewEvents.length,2);
assert.equal(counts(archive).venue.get('old'),2);
assert.equal(counts(archive).venue.get('blue'),0);
assert.equal(counts(archive).priority.get('S+'),1);
assert.equal(counts(archive).priority.get('S'),0);
assert.equal(counts(base).venue.get('old'),0);
const unfiltered = view(base);
assert.equal(unfiltered.signalVisible,true);
assert.equal(unfiltered.selected.length,6);
assert.equal(unfiltered.results.length,5);
assert.equal(counts(base).radar_area.get('kanagawa'),1,'Signal counts for availability');
assert.deepEqual(logic.availableAreas(view(base).viewEvents,registry),['dmv','new_york','kanagawa','unassigned'],'scenes retain editorial order');
const signalFiltered = view({...base,radar_area:'kanagawa'});
assert.equal(signalFiltered.signalVisible,false);
assert.equal(signalFiltered.results[0].id,'signal-aplus');
assert.equal(counts({...base,radar_area:'kanagawa'}).priority.get('A+'),1);
assert.equal(logic.radarAreaFor(events[7],registry),'unassigned','unknown ID uses registry fallback');
assert.equal(logic.radarAreaFor(events[7],registry),'unassigned','city does not infer DMV');
const revised = events.filter(item => item.id !== 'blues-a' && item.id !== 'blues-aplus');
const impossible = {...blues,priority:'A'};
const repaired = logic.validFacetState(logic.deriveRadarView(revised,impossible,null,today,registry).viewEvents,impossible,registry);
assert.equal(repaired.venue,'');
assert.equal(repaired.radar_area,'');
assert.equal(repaired.priority,'A');
const empty = logic.validFacetState([],impossible,registry);
assert.equal(empty.venue,'');
assert.equal(empty.radar_area,'');
assert.equal(empty.priority,'');
"""
        subprocess.run([NODE, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True)


if __name__ == "__main__":
    unittest.main()
