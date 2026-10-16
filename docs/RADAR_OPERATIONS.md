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
- `ERROR`: the latest completed run is `error` and no later success exists.
- `HEALTHY`: the latest successful run completed no more than
  `expected_max_silence_hours` ago.
- `STALE`: desired state is on and the last success is older than that
  threshold. A recent partial run does not replace the last successful
  heartbeat.

The browser uses the visitor's current time. The audit script accepts `--now`
for deterministic checks. The next expected window is the last successful
completion plus the configured cadence when the cadence is expressed as
`hourly` or `every_N_hours`.

## External executor contract

For every scheduled or manual attempt, an executor must:

1. Fetch the current default branch and validate `status.json`.
2. Skip scheduled research when `enabled` is false. A manual override must be
   identified as `trigger: manual`; it must never pretend the desired state is
   on.
3. Generate a globally unique `run_id` and preserve `started_at`.
4. Search the documented Tokyo/Kanto and US-corridor domains with its declared
   web/search capability and editorial rules.
5. Publish qualifying new candidates through a version 2 curated intake batch,
   preserving `discovered_at`; publish enrichment separately.
6. Append exactly one completed run to `runs.json`, even when all counters are
   zero. Record broad, non-private `threads_checked`, not research transcripts.
7. Use `success` only when the intended scan completed, `partial` when useful
   work completed with gaps, and `error` when the scan failed. Include a concise
   `error_summary` for partial/error outcomes. The key is always required:
   explicitly use `"error_summary": null` for success. Use
   `python3 scripts/record_radar_run.py --record /path/to/completed-run.json`
   to validate and append the actual record; identical retries are idempotent.
8. Commit/push the intake and heartbeat together when possible. Never rewrite
   or delete earlier run records.

Run records must follow the contract enforced by
`scripts/validate_radar_discovery.py`. Counters are non-negative integers and
`completed_at` may not precede `started_at`.

## Manual operation

There is no repository-hosted discovery command today. The exact reconnection
action is to re-enable `Yamamoto + Listening Notes RADAR`, update its prompt to
follow this executor contract, give it authenticated repository write access,
and require a heartbeat commit on every run. Its first reconnected execution
must append a real run record; until then the public state must remain UNKNOWN
or STALE rather than claiming that search is healthy.

The reported external incident context is: prior hourly cadence, automation
disabled, and last recorded execution on September 10, 2026. The repository
does not contain the automation control history and cannot establish why it was
disabled. That date is intentionally not converted into a run heartbeat because
an exact time, outcome, and counters are unavailable.

## Dependencies

- A discovery executor capable of following this contract.
- Web/search access for the executor.
- Authenticated GitHub repository access for publishing intake and heartbeats.
- GitHub Actions for deterministic ingestion and validation.
- GitHub Pages for the read-only public interface.

No browser credential, PAT, repository secret, OpenAI key, or scraped research
log belongs in the public repository.

## September 30 outage, investigated October 14, 2026

Production remained at `b5c793a` until the October 14 recovery. The October 12 validation
run failed because three real success records omitted `error_summary`.
The discovery chat reported pausing after that failure. The repair adds only
the three explicit nulls, preserving all six runs, timestamps and counters;
it does not record a new scan or claim restored search health.

Separately, RADAR ingest failed because historical discovery verification
compared the entire live catalog with the fixed September 29 backfill hash.
The first two legitimate v2 additions made that condition impossible. The
verifier now checks the original backfill hash and reconstructs the current
catalog by replaying processed v2 intake. Each processed batch must preserve
an exact curated source in Git history. Unrecorded edits, deletions and
additions still fail validation; historical manifests are unchanged.

The five pending September 30 intake batches contain 12 candidates. The ingest
workflow retries them when the repair is deployed. Recovery also registers
Jammin' Java from its official promoter page, removes the unsupported
`official_ticket_price` enrichment label from Oz Noy and SQUANDERERS (prices
remain null and the explanatory notes remain), and aligns Luke Stewart's
English travel text with its existing A+ rating. The October 14 primary-source
check corrects Oz Noy's doors time to 6:00 PM; the older source note is retained
with an explicit superseding note. Past dates remain valid
historical records and do not imply attendance. Deployment and queue recovery
are separate from re-enabling the external discovery automation. Update that
automation to use the complete heartbeat schema, then require a real successful
scan before reporting recovery. Do not disable its schedule automatically on a
validation error: report the error and retry on the existing cadence.

Evidence: [October 12 validation failure](https://github.com/iosorio/listening-notes/actions/runs/38254308729),
[September 30 ingest failure](https://github.com/iosorio/listening-notes/actions/runs/36753523090).

### Published recovery — October 14, 2026

[PR #4](https://github.com/iosorio/listening-notes/pull/4) was merged as
`7315434`. [RADAR ingest](https://github.com/iosorio/listening-notes/actions/runs/38616734246)
successfully processed all five pending batches, adding 12 events in commit
`75fac81` and bringing the canonical catalog to 240 events. The
[Pages deployment](https://github.com/iosorio/listening-notes/actions/runs/38616889754)
succeeded; the public `radar/events.json` was verified byte-for-byte against
that commit. Event, signal, and discovery-schema validation passed on Mac Pro,
as did all 136 tests. Both machine checkouts were synchronized to the published
commit.

The external executor received a request to reactivate its existing schedule,
adopt the corrected heartbeat contract, and perform a real manual recovery
scan. At the recovery check, that chat had returned to idle without an answer;
schedule activation and a new discovery run were therefore unconfirmed. The
latest successful heartbeat still dated from September 30, so discovery health
correctly remained `STALE`. Queue recovery and deployment did not create a new
heartbeat or establish that recurring research had resumed.

### Executor recovery — October 16, 2026

The existing external task is now confirmed active with an hourly schedule.
Its saved instructions include the complete heartbeat schema, fresh reads of
`main`, and continued retries after validation failures. The first reconnected
scan, `radar-20261016T134422863Z-t2v6cy9dko`, completed successfully at
13:49:19 UTC and published three candidates in
[`17f5814`](https://github.com/iosorio/listening-notes/commit/17f581486a274fda1ec57805b71672ce92187dae).
Those three reached canonical in `60409df`. Further scheduled runs followed;
the latest verified run at this check, `radar-20261016T171620904Z-gd4qkea9n7`,
completed at 17:20:22 UTC with 26 sources, 20 candidates reviewed, and two
published candidates. Discovery health is now `HEALTHY`.

The next six candidates exposed a separate ingest blocker:
[the October 16 workflow](https://github.com/iosorio/listening-notes/actions/runs/38939231573)
failed because a UI test compared Blues Alley results with a fixed list of
production event IDs. A legitimate new Dani Cortaza event changed that list.
The Blues Alley and Wharf filter tests now use a controlled fixture instead
of freezing the evolving catalog. They still verify canonical venue identity,
exclusion of same-name venues and archived/attended events, unique results,
and Signal behavior. Production filtering and intake/provenance validation
are unchanged. Research-only factual updates remain outside automatic intake.
