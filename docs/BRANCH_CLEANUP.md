# Branch cleanup triage

**87 stale remote branches** vs `main` (`f0f7a66`). None carries active development; all are safe to delete once the salvage decision below is made.

## Why there are so many branches

A single unmerged feature — autonomous NEO / meteor / hourly-scan event tracking — spawned a swarm of ~59 near-duplicate AI-generated branches in March 2026, none of which ever merged. Layered on top: ~15 branches whose work was squash-merged to `main` in this session (the mechanical-design packages and the Stage 0–5 fixes), ~12 old review/experiment branches, and the legacy `master` branch. Squash-merges don't preserve branch commit SHAs, so genuinely-merged branches still *look* unmerged by ancestry — which is why the count looked alarming.

## Categories

| Category | Count | Meaning |
|---|--:|---|
| MERGED | 15 | Already merged into main this session (content is on main). |
| SWARM | 59 | March 2026 NEO/hourly-scan swarm — near-duplicate attempts at one feature. The coherent NEO core (CNEOS close-approach + NEO feed clients) is now on main (#108/#109); these carry no unique work worth keeping except the three salvage candidates noted below. |
| REVIEW | 12 | Old cursor/claude review & experiment branches, long behind main. |
| OLD-DEFAULT | 1 | Superseded old default branch (main is the default now — verify before deleting). |

## Salvage candidates (distinct features NOT on main — recover BEFORE deleting the swarm, or they are lost)

The NEO close-approach + feed clients were already salvaged to `main`. The swarm additionally contains three *distinct* capabilities not on `main` (spread across many conflicting duplicates):

- **Hourly event scanner** — `hourly_scanner.py` / `hourly_scan.py` (autonomous hourly sky-event scan).
- **Event journal** — `event_journal.py` / `event_log.py` (persistent event logging).
- **Space-weather client** — `space_weather_client.py` (NOAA space-weather feed).

If you want any of these, say so and they can be salvaged onto `main` the same way the NEO clients were (pick the best implementation, adapt to current `main`, test, squash-merge). Otherwise they go with the swarm.

## Full branch list

| Category | Last commit | ahead/behind | Branch |
|---|---|---|---|
| MERGED | 2026-08-01 | +7/-19 | `fix/stage-0-boot-visibility` |
| MERGED | 2026-08-01 | +6/-18 | `fix/stage-1-physical-safety` |
| MERGED | 2026-08-01 | +5/-18 | `fix/stage-2-data-integrity` |
| MERGED | 2026-08-01 | +4/-18 | `fix/stage-3-security-hardening` |
| MERGED | 2026-08-02 | +0/-6 | `design/mechanical-proveout` |
| MERGED | 2026-08-02 | +1/-14 | `fix/flaky-power-events-test` |
| MERGED | 2026-08-02 | +1/-10 | `fix/stage-4-aliases` |
| MERGED | 2026-08-02 | +1/-9 | `fix/stage-4-dispatcher` |
| MERGED | 2026-08-02 | +1/-11 | `fix/stage-4-lifecycle` |
| MERGED | 2026-08-02 | +2/-12 | `fix/stage-4-mount-async` |
| MERGED | 2026-08-02 | +1/-14 | `fix/stage-4-protocol-conformance` |
| MERGED | 2026-08-02 | +4/-15 | `fix/test-suite-hardening` |
| MERGED | 2026-08-06 | +0/-3 | `design/mechanical-tender` |
| MERGED | 2026-08-06 | +1/-1 | `fix/neo-feed-distance-utc` |
| MERGED | 2026-08-06 | +2/-2 | `salvage/neo-close-approach-clients` |
| OLD-DEFAULT | 2026-03-24 | +8/-47 | `master` |
| REVIEW | 2026-02-23 | +1/-47 | `claude/review-codebase-NsisM` |
| REVIEW | 2026-06-23 | +1/-19 | `cursor/holistic-repo-review-5af9` |
| REVIEW | 2026-06-23 | +1/-19 | `cursor/holistic-review-team-ownership-5a9b` |
| REVIEW | 2026-06-23 | +2/-19 | `cursor/holistic-review-team-ownership-8f3f` |
| REVIEW | 2026-06-23 | +2/-19 | `cursor/repo-operations-ownership-55a0` |
| REVIEW | 2026-06-23 | +2/-19 | `cursor/repo-review-and-team-ownership-a9c0` |
| REVIEW | 2026-06-23 | +5/-19 | `cursor/repo-review-team-and-issue-backlog-2d56` |
| REVIEW | 2026-06-24 | +1/-19 | `cursor/setup-dev-environment-39bf` |
| REVIEW | 2026-07-06 | +1/-19 | `claude/nightwatch-frontend-demo-takdve` |
| REVIEW | 2026-07-12 | +13/-19 | `claude/install-review-org-37y4ck` |
| REVIEW | 2026-08-02 | +5/-19 | `claude/repo-landscape-audit-mdpb4f` |
| REVIEW | 2026-08-03 | +2/-8 | `cursor/nightwatch-demo-console-86da` |
| SWARM | 2026-03-21 | +1/-47 | `add-event-journal-and-neo-client` |
| SWARM | 2026-03-21 | +1/-47 | `feat/hourly-event-polling` |
| SWARM | 2026-03-21 | +2/-47 | `feat/neo-client-hourly-scan` |
| SWARM | 2026-03-21 | +2/-47 | `feat/neo-hourly-scan` |
| SWARM | 2026-03-21 | +1/-47 | `feat/neo-space-weather-hourly-scan` |
| SWARM | 2026-03-21 | +1/-47 | `feat/neo-tracking-and-event-log` |
| SWARM | 2026-03-21 | +2/-47 | `feat/neo-tracking-and-event-logs` |
| SWARM | 2026-03-21 | +2/-47 | `feat/trajectory-biased-hopi-circles` |
| SWARM | 2026-03-21 | +1/-47 | `feature/close-approach-client` |
| SWARM | 2026-03-21 | +1/-47 | `feature/neo-client-scan-log` |
| SWARM | 2026-03-21 | +1/-47 | `feature/neo-close-approach-client` |
| SWARM | 2026-03-21 | +1/-47 | `feature/neo-tracking-and-event-log` |
| SWARM | 2026-03-21 | +1/-47 | `hourly-scan-and-bugfixes` |
| SWARM | 2026-03-21 | +2/-47 | `hourly-scan/2026-03-21-ams-integration` |
| SWARM | 2026-03-21 | +1/-47 | `hourly-scanner-and-space-weather` |
| SWARM | 2026-03-21 | +1/-47 | `neo-close-approach-client` |
| SWARM | 2026-03-21 | +2/-47 | `wire-meteor-to-orchestrator` |
| SWARM | 2026-03-22 | +2/-47 | `feat/close-approach-client` |
| SWARM | 2026-03-22 | +1/-47 | `feat/hourly-scanner-and-cad-client` |
| SWARM | 2026-03-22 | +1/-47 | `feat/hourly-scanner-neo-tracking` |
| SWARM | 2026-03-22 | +1/-47 | `feat/neo-space-weather-clients` |
| SWARM | 2026-03-22 | +1/-47 | `feat/neo-tracking-and-historic-events` |
| SWARM | 2026-03-22 | +1/-47 | `feature/hourly-event-scanner` |
| SWARM | 2026-03-22 | +2/-47 | `hourly-meteor-integration-2026-03-22` |
| SWARM | 2026-03-22 | +2/-47 | `hourly-scan-neo-client` |
| SWARM | 2026-03-22 | +1/-47 | `hourly-scan-report` |
| SWARM | 2026-03-22 | +2/-47 | `hourly-watch-neo-client` |
| SWARM | 2026-03-22 | +1/-47 | `integrate-meteor-config` |
| SWARM | 2026-03-22 | +1/-47 | `neo-close-approach-tracking` |
| SWARM | 2026-03-22 | +2/-47 | `nightwatch/neo-tracking-and-event-journal` |
| SWARM | 2026-03-23 | +1/-47 | `feat/historic-fireballs-neo-client-voice-tools` |
| SWARM | 2026-03-23 | +1/-47 | `feat/hourly-neo-scanner` |
| SWARM | 2026-03-23 | +1/-47 | `feat/hourly-scan-and-close-approach` |
| SWARM | 2026-03-23 | +2/-47 | `feat/hourly-scan-neo-client` |
| SWARM | 2026-03-23 | +2/-47 | `feat/hourly-scan-report` |
| SWARM | 2026-03-23 | +1/-47 | `feat/hourly-scan-system` |
| SWARM | 2026-03-23 | +2/-47 | `feat/hourly-scanner-close-approach` |
| SWARM | 2026-03-23 | +2/-47 | `feat/hourly-scanner-neo-client` |
| SWARM | 2026-03-23 | +1/-47 | `feat/neo-close-approach-and-ams-fix` |
| SWARM | 2026-03-23 | +2/-47 | `feat/neo-close-approach-monitoring` |
| SWARM | 2026-03-23 | +2/-47 | `feat/neo-tracking-hourly-scanner` |
| SWARM | 2026-03-23 | +1/-47 | `fix/ams-monitoring-integration` |
| SWARM | 2026-03-23 | +1/-47 | `fix/hourly-scan-and-test-fixes-20260323` |
| SWARM | 2026-03-23 | +1/-47 | `fix/meteor-tracking-ams-hourly-scan` |
| SWARM | 2026-03-23 | +2/-47 | `hourly-scan-system` |
| SWARM | 2026-03-23 | +2/-47 | `hourly-scan/2026-03-23-test-coverage` |
| SWARM | 2026-03-23 | +1/-47 | `hourly/2026-03-23-meteor-tracking-enhancements` |
| SWARM | 2026-03-23 | +2/-47 | `neo-approach-client` |
| SWARM | 2026-03-23 | +4/-47 | `nightwatch-hourly-scan-2026-03-23` |
| SWARM | 2026-03-24 | +1/-47 | `feat/event-journal` |
| SWARM | 2026-03-24 | +5/-47 | `feat/hourly-event-scanner` |
| SWARM | 2026-03-24 | +1/-47 | `feat/hourly-neo-tracking-and-event-journal` |
| SWARM | 2026-03-24 | +1/-47 | `feat/neo-client-and-event-journal` |
| SWARM | 2026-03-24 | +8/-47 | `feat/neo-close-approach-client` |
| SWARM | 2026-03-24 | +6/-47 | `feat/neo-close-approach-tracking` |
| SWARM | 2026-03-24 | +4/-47 | `feat/neo-hourly-scanner` |
| SWARM | 2026-03-24 | +1/-47 | `feature/event-journal-and-neo-client` |
| SWARM | 2026-03-24 | +2/-47 | `feature/neo-close-approach-tracking` |
| SWARM | 2026-03-24 | +3/-47 | `hourly-scan-2026-03-24` |

## Deletion

Remote deletion is blocked from the automation sandbox, so run `scripts/delete_stale_branches.sh` locally (it deletes all listed branches from `origin`). Review first; comment out any you want to keep.
