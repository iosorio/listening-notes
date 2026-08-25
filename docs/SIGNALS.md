# The Signal

The Signal is the event that Listening Notes considers most important to notice
now during the current editorial cycle. It is an explicit editorial
recommendation, not the result of sorting the current page. It is not
necessarily the newest event, the nearest event, or the event with the highest
priority.

Priority and Signal answer different questions. Priority records the durable
strength of the event recommendation. The Signal records why one eligible event
needs attention in a particular moment. Discovery and ingestion may nominate a
candidate, but they never promote or replace The Signal.

## Eligibility

A Signal must reference one canonical event in `radar/events.json`. At the time
of activation, that event must:

- have priority `S+`, `S`, or `A+`;
- have a sufficiently verified artist or project identity;
- have a verified date, stable venue identity, and exact official event page;
- preserve that official page in its factual sources;
- have native English and Spanish `why_now` copy that is specific to the
  current moment and distinct from general `why_it_matters` or priority copy;
- merit replacing the current Signal for an editorial reason, not merely
  because it was recently discovered or ingested.

Valid why-now reasons include an imminent sale or presale, a real risk of
losing the opportunity, an approaching decision, a reunion or farewell, a
premiere or exceptional setting, an unusually important discovery, a material
change in tickets or lineup, or a particularly strong connection to the
current Listening Notes narrative.

## Canonical history

`radar/signals.json` is the human-readable system of record. Its schema is:

```json
{
  "schema_version": 1,
  "signals": [
    {
      "signal_id": "signal-YYYY-MM-DD-canonical-event-id",
      "event_id": "canonical-event-id",
      "activated_on": "YYYY-MM-DD",
      "minimum_until": "YYYY-MM-DD",
      "action_deadline": null,
      "replaced_on": null,
      "replaced_by": null,
      "editorial": {
        "en": {"why_now": "Native English rationale."},
        "es": {"why_now": "Razón editorial escrita en español."}
      },
      "early_replacement_override": null,
      "reentry_material_change": null
    }
  ]
}
```

Records are chronological. Exactly one record is current; it is the final
record and has null `replaced_on` and `replaced_by`. `replaced_by` identifies
the next record's `signal_id`, not merely its event. Historical records are
immutable except that the current record receives its closing fields when it
is replaced.

The normal minimum cycle is seven days. `minimum_until` is the earliest of
seven days after activation, the event's final date, or a documented
`action_deadline`. An action deadline is used only when a real sale, presale,
reservation, or other decision expires before the normal cycle.

Replacing the current Signal before `minimum_until` requires
`early_replacement_override` with native English and Spanish urgent reasons.
The same event cannot re-enter within 30 days of its replacement unless the new
record includes `reentry_material_change` with a specific bilingual account of
what materially changed. These objects contain the transition date and an
`editorial.en.reason` / `editorial.es.reason` pair.

Do not backfill or infer earlier Signals. History begins when explicit Signal
records begin.

## Manual promotion

Validate the current files, preview the editorial transition, then run the same
command without `--dry-run`:

```sh
python3 scripts/validate_signals.py radar/signals.json radar/events.json
python3 scripts/set_signal.py canonical-event-id \
  --why-now-en "English why-now copy" \
  --why-now-es "Texto editorial en español" \
  --dry-run
python3 scripts/set_signal.py canonical-event-id \
  --why-now-en "English why-now copy" \
  --why-now-es "Texto editorial en español"
```

Use `--action-deadline` only for a verified earlier deadline. An early
transition also requires both `--urgent-override-en` and
`--urgent-override-es`. Re-entry inside 30 days also requires both
`--material-change-en` and `--material-change-es`. The helper never generates
editorial reasoning, never calls AI, reports the proposed transition, validates
the whole history, and writes atomically.

RADAR discovery and ingestion do not call this helper.

## Page behavior

The page loads `events.json` and `signals.json` independently. The active
record is the only source for the large Signal card. There is no priority,
date, featured-field, or ranking fallback. If the Signal file cannot load or
its current event cannot be resolved, the module is hidden and every upcoming
event remains in the normal results.

The Signal and at most two real, replaced Recent Signals appear only in the
completely unfiltered Upcoming view. The large Signal card precedes the view
and filter controls; Recent Signals follow the controls. Any city, venue, or
priority filter hides both editorial sections and displays every matching event
as a normal card. Archive also hides them. The current event is removed from the
normal grid only while its explicit Signal card is visible. Previous Signals
may remain in the normal listing. Switching Upcoming and Archive resets filters;
filter choices continue to come from the active view.
