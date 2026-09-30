# RADAR operations

RADAR is a repository-backed service with an external discovery executor. The
repository is the authority for desired state, run telemetry, reviewed intake,
and canonical events; an executor is responsible for doing research and
publishing those records.

## Runtime architecture

```text
static site (read only)
  -> radar/discovery/status.json (desired state)
  -> external discovery executor (currently a ChatGPT automation)
  -> web/search research and editorial review
  -> radar/inbox/curated/*-intake.json
  -> GitHub Actions RADAR ingest
  -> radar/events.json (canonical RADAR)

external discovery executor
  -> radar/discovery/runs.json (append-only heartbeat ledger)
  -> static site operational status
```

The site-to-state arrow is read-only today. The state-to-executor arrow is a
contract, not an in-repository scheduler. The executor-to-inbox and
executor-to-ledger arrows are external Git commits. GitHub Actions implements
only the reviewed-inbox-to-canonical arrow.

`radar-ingest.yml` merges reviewed creation and enrichment batches, validates
the result, archives processed intake, and commits the canonical update.
`validate.yml` validates data and audits the backlog on a weekly/manual
schedule. Neither workflow searches the web, invokes an agent, or constitutes
a RADAR discovery run.

The static GitHub Pages site has no authenticated write surface. It cannot
safely hold a GitHub token or an executor credential. Consequently it exposes
status and authenticated GitHub management links, but no in-page switch or
Run-now button. A real control plane would need an authenticated backend or
GitHub App that can commit desired-state changes and dispatch a credentialed
executor. GitHub `workflow_dispatch` alone is not a discovery path until such
an executor exists.

## Durable files

- `radar/discovery/status.json`: desired runtime state. `enabled` says what
  should happen, not what is happening. `state_history` is append-only and
  explains changes.
- `radar/discovery/runs.json`: append-only, chronological run heartbeats. A
  successful run with zero events is still a required record.
- `radar/events.json`: canonical event data, including immutable discovery
  provenance when known.

Run `python3 scripts/validate_radar_discovery.py` to validate the two
operational files and print derived health. Staleness is an operational warning,
not a schema failure.

To answer “what did RADAR discover this week,” filter canonical events by
`discovered_at`. Events without established historical provenance remain
unknown and must not be grouped by concert date or intake filename instead.

## Health rules

- `OFF`: desired `enabled` is false, regardless of run history.
- `UNKNOWN`: desired state is on but the repository has no run heartbeat.
  It also applies when only partial runs exist, or telemetry is unavailable,
  malformed, or dated in the future; none proves a completed successful scan.
- `ERROR`: an `error` has no later success. A later partial run does not clear it.
- `HEALTHY`: the latest successful run completed no more than
  `expected_max_silence_hours` ago.
- `STALE`: desired state is on and the last success is older than that
  threshold. A recent partial run does not replace the last successful
  heartbeat.

The headline shows derived health alone; requested ON/OFF is a separately
labeled fact with an explicit explanation that it does not control or confirm
the external executor. The GitHub edit link changes only desired state.
Operational telemetry loads independently of events, so a catalog failure
cannot hide status or a telemetry failure hide the catalog.

The browser uses the visitor's current time and refreshes telemetry every minute
without using the browser cache. This is read-only status refresh, not discovery.
The audit script accepts `--now`
for deterministic checks. The next expected window is the last successful
completion plus the configured cadence when the cadence is expressed as
`hourly` or `every_N_hours`; it is an expectation, not a confirmed scheduler
appointment, and is omitted when requested state is OFF.

## External executor contract

For every scheduled or manual attempt, an executor must:

1. Fetch the current default branch and validate `status.json`.
2. Skip scheduled research when `enabled` is false. A manual override must be
   identified as `trigger: manual`; it must never pretend the desired state is
   on.
3. Generate a globally unique `run_id` and preserve `started_at`. Serialize runs
   so publication follows their strictly increasing start order.
4. Search the documented Tokyo/Kanto and US-corridor domains with its declared
   web/search capability and editorial rules.
5. Publish qualifying new candidates through a version 2 curated intake batch,
   preserving `discovered_at`; publish enrichment separately.
6. Append exactly one completed run to `runs.json`, even when all counters are
   zero. Record broad, non-private `threads_checked`, not research transcripts.
7. Use `success` only when the intended scan completed, `partial` when useful
   work completed with gaps, and `error` when the scan failed. Include a concise
   `error_summary` for partial/error outcomes.
8. Commit/push the intake and heartbeat together when possible. Never rewrite
   or delete earlier run records.

Run records must follow the contract enforced by
`scripts/validate_radar_discovery.py`. Counters are non-negative integers and
`completed_at` may not precede `started_at`.

### Heartbeat publication

`scripts/record_radar_run.py` is a deterministic ledger writer, not a discovery
executor. Supply one JSON object containing actual measurements after a scan:

| Fields | Required value |
| --- | --- |
| `run_id` | Unique ID generated once for this attempt; reuse it only for publication retries. |
| `started_at`, `completed_at` | Actual timezone-aware ISO-8601 instants, never a scheduled or future time. |
| `trigger` | `scheduled`, `manual`, or `external`. |
| `status` | `success`, `partial`, or `error` according to scan completion. |
| `executor` | Accurate executor name, such as `ChatGPT automation: Yamamoto + Listening Notes RADAR`. |
| `threads_checked` | Array of broad research threads actually checked; may be empty on failure. |
| `sources_checked`, `candidates_reviewed` | Counts of sources actually consulted and candidates actually evaluated. |
| `events_admitted`, `events_published` | Admitted candidates and new candidates included in the published curated intake; not canonical merges. |
| `material_updates` | Existing-event updates published through the permitted review workflow. |
| `error_summary` | `null` for success; concise, non-private explanation for partial/error. |

Keep the per-attempt JSON outside the public repository until appended. With
`/tmp/radar-run.json` holding the actual record, run:

```sh
python3 scripts/record_radar_run.py --record /tmp/radar-run.json --dry-run
python3 scripts/record_radar_run.py --record /tmp/radar-run.json
python3 scripts/validate_radar_discovery.py --base-ref HEAD
```

Review and commit `radar/discovery/runs.json` and any reviewed intake in one
commit, then use a normal, non-force push to `main`. Use a dedicated checkout,
serialize executor attempts, and do not commit unrelated local work. If another
publisher advances `main`, fetch that version, preserve its full ledger, and
reapply the same run record and intake. An exact retry is a no-op; a changed
record with the same ID is rejected. Never resolve a conflict by replacing the
ledger with an older copy. If an earlier run cannot append in chronological
order, report the publication failure for operator reconciliation instead of
changing timestamps or rewriting history.

A connector-based executor can perform the equivalent append with a GitHub
commit whose parent is the fetched `main`, followed by a non-force ref update.
It must preserve the entire prior array, use the same validation contract, and
verify the resulting commit through a fresh read. No shell or repository-owned
scheduler is required. GitHub validation compares the previous ledger on pushes
and pull requests to reject deletion or modification of existing heartbeats.

If research fails, publish a real error/partial heartbeat when repository access
still works. If publication itself fails, report it explicitly and retain the
same record for retry; neither an uncommitted local record nor a notification is
a repository heartbeat. A scheduled check of requested OFF skips research and
does not fabricate a successful scan. Manual overrides must be explicit.

## Manual operation

There is no repository-hosted discovery command today. The exact reconnection
action is to re-enable `Yamamoto + Listening Notes RADAR`, update its prompt to
follow this executor contract (prepend `docs/RADAR_EXECUTOR_PROMPT.md` to the
existing editorial prompt), give it authenticated repository write access,
and require a heartbeat commit on every run. Its first reconnected execution
must append a real run record; until then the public state must remain UNKNOWN
or STALE rather than claiming that search is healthy.

The reported external incident context is: prior hourly cadence, automation
disabled, and last recorded execution on September 10, 2026. The repository
does not contain the automation control history and cannot establish why it was
disabled. That date is intentionally not converted into a run heartbeat because
an exact time, outcome, and counters are unavailable.

### Reconnection audit — September 30, 2026

The audit started at `main` commit `e4e0b274458e4440fac751bef4f73933507e0e2b`,
which includes observability commit `221750bb5a36a9a592c28fbb5127017b3b0fc56d`.
Desired state was ON, hourly, with a 12-hour silence threshold; the ledger was
empty, so the supported observed health was UNKNOWN.

A read-only inspection of the external automation control confirmed that the
existing `Yamamoto + Listening Notes RADAR` task was disabled, retained an hourly
schedule, and reported its last execution at `2026-09-10T19:36:27.669204+00:00`.
Its prompt read editorial/inbox policy but did not read operational state or
require `runs.json` publication. The control timestamp does not establish a
scan outcome or counters and must not be backfilled as a heartbeat. The reason
for disabling the task remains unknown.

The external reconnection action is to apply the operational prompt addendum to
that existing task and resume it with repository-write and web/search access.
Do not create a replacement task or a GitHub Actions discovery schedule. A
successful interactive GitHub read during this audit does not prove write
access in a future scheduled execution. Acceptance is the first real heartbeat
commit from that executor, including a zero-result scan if nothing qualifies;
turning on either switch alone must not turn the page green.

Audit verification: 131 repository unit tests passed in the isolated Linux
checkout, as did the event/Signal validators, operational audit, JavaScript
syntax check, and whitespace check. The operational audit still reported
UNKNOWN against the unchanged empty ledger. The optional bilingual browser
regression is `tests/radar_operations_browser.cjs`; it could not execute in
that environment because Chromium was unavailable and its download failed.
`AGENTS.md` requires final validation and checkout synchronization on Mac Pro;
`ssh MacPro` could not resolve there, so these Linux checks do not claim to
complete that machine-specific publication gate.

## Dependencies

- A discovery executor capable of following this contract.
- Web/search access for the executor.
- Authenticated GitHub repository access for publishing intake and heartbeats.
- GitHub Actions for deterministic ingestion and validation.
- GitHub Pages for the read-only public interface.

No browser credential, PAT, repository secret, OpenAI key, or scraped research
log belongs in the public repository.
