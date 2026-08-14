# Event Data Model

`radar/events.json` is the only event dataset. It is JSON, formatted with one
object per event where practical, and is designed to stay readable in Git.

## Root shape

```json
{
  "schema_version": 2,
  "events": []
}
```

## Event shape

```json
{
  "id": "artist-project-2026",
  "artist": "Artist",
  "subtitle": null,
  "dates": {"start": "YYYY-MM-DD", "end": null},
  "showtimes": [],
  "venue": {"name": "Venue", "city": "City", "state": "State"},
  "geography": "Local",
  "priority": "A+",
  "category": "Masters",
  "genres": ["Jazz"],
  "status": "considering",
  "lineup": [],
  "factual_description": null,
  "editorial": {
    "en": {"why_it_matters": "…", "trip_verdict": "…"},
    "es": {"why_it_matters": "…", "trip_verdict": "…"}
  },
  "links": {"official_event": null, "official_tickets": null},
  "tickets": {
    "currency": "USD",
    "official": {"minimum": null, "maximum": null, "source_url": null, "checked_on": null},
    "resale": {"minimum": null, "maximum": null, "url": null, "checked_on": null}
  },
  "sources": [],
  "recommended_listening": [],
  "attendance": {"notes": null, "setlist": null, "photo_paths": []}
}
```

## Field rules

- `id` is stable and never reused. Correct a record in place; do not make a new
  ID solely because copy, pricing, or a URL changed.
- `dates.start` is required; `dates.end` is optional and inclusive.
- `showtimes` is an array because multi-night engagements can have distinct
  times. Use ISO-like local time strings such as `19:30` only when verified.
- `status` is one of `considering`, `going`, `attended`, or `passed`.
- `factual_description` is source-backed; set it to `null` when not verified.
- `editorial` has native English and Spanish copy. Do not put display-language
  lookup tables in application JavaScript.
- `sources` records provenance as `{ "url", "publisher", "checked_on", "note" }`.
- All ticket prices are numeric face values or resale values in `currency`.
  Unknown prices are `null`; never infer them from a resale listing.
- `recommended_listening` contains objects with `artist`, `title`, `kind`
  (`album` or `track`), and optional `apple_music_url`.
- `attendance` preserves personal material after a show; photo paths refer to
  committed local assets only.

## Migration policy

Legacy records may retain source-less editorial copy during migration, but must
use empty `sources`, null URLs/prices, and a provenance-backfill note. New or
factually changed records require source entries before publication.
