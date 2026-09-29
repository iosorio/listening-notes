# RADAR discovery provenance backfill report

Prepared before historical backfill on September 29, 2026.

## Classification

The canonical dataset contained 226 events.

| Classification | Count | Treatment |
| --- | ---: | --- |
| Exact timestamp recoverable | 2 | Backfill `discovered_at` from the explicitly established first RADAR add commit. |
| Date recoverable | 0 | No date-only value met the evidence threshold. |
| Unknown | 224 | Leave discovery fields absent; do not infer them. |

The two exact cases are:

- `mastodon-deafheaven-alcest-anthem-washington-dc-2026-09-25` — commit
  `f666225bd37efb145ea437ba81c317569ea5c348`, authored
  `2026-08-20T11:42:34-04:00`.
- `nicholas-payton-a-supreme-blue-blues-alley-2026-09-26` — commit
  `e7f556400d4f25fb1a081b7d0d32eaeffab47880`, authored
  `2026-08-17T19:33:31-04:00`.

These regressions prove that concert date is not discovery date. The later
Mastodon update in `b5efcaa6f37f42a06be90e42276ff4ed0fce6015` does not replace the
earlier discovery timestamp.

## Conservative exclusions

The audit did not treat an event date, source `checked_on`, filename suffix,
processed archive date, or the first bulk migration commit as proof of initial
discovery. Git commits that merely publish or enrich a record establish neither
an earlier research moment nor a precise discovery time unless the evidence is
explicit. Unknown historical provenance remains valid and visible as unknown.

Future version 2 intake removes this ambiguity by requiring `discovered_at` and
`published_at` before a new candidate can be merged. Historical filenames are
preserved; future files use `*-intake.json`, and fields are authoritative.
