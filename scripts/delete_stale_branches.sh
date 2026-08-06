#!/usr/bin/env bash
# Delete all stale NIGHTWATCH remote branches (see docs/BRANCH_CLEANUP.md).
# Review before running. Comment out any branch you want to keep.
# The NEO feature is already salvaged to main (#108/#109). Deleting the SWARM
# discards the un-salvaged hourly-scanner / event-journal / space-weather work.
set -euo pipefail

# --- MERGED: Already merged into main this session (content is on main).
git push origin --delete fix/stage-0-boot-visibility
git push origin --delete fix/stage-1-physical-safety
git push origin --delete fix/stage-2-data-integrity
git push origin --delete fix/stage-3-security-hardening
git push origin --delete design/mechanical-proveout
git push origin --delete fix/flaky-power-events-test
git push origin --delete fix/stage-4-aliases
git push origin --delete fix/stage-4-dispatcher
git push origin --delete fix/stage-4-lifecycle
git push origin --delete fix/stage-4-mount-async
git push origin --delete fix/stage-4-protocol-conformance
git push origin --delete fix/test-suite-hardening
git push origin --delete design/mechanical-tender
git push origin --delete fix/neo-feed-distance-utc
git push origin --delete salvage/neo-close-approach-clients

# --- SWARM: March 2026 NEO/hourly-scan swarm — near-duplicate attempts at one feature. The coherent NEO core (CNEOS close-approach + NEO feed clients) is now on main (#108/#109); these carry no unique work worth keeping except the three salvage candidates noted below.
git push origin --delete add-event-journal-and-neo-client
git push origin --delete feat/hourly-event-polling
git push origin --delete feat/neo-client-hourly-scan
git push origin --delete feat/neo-hourly-scan
git push origin --delete feat/neo-space-weather-hourly-scan
git push origin --delete feat/neo-tracking-and-event-log
git push origin --delete feat/neo-tracking-and-event-logs
git push origin --delete feat/trajectory-biased-hopi-circles
git push origin --delete feature/close-approach-client
git push origin --delete feature/neo-client-scan-log
git push origin --delete feature/neo-close-approach-client
git push origin --delete feature/neo-tracking-and-event-log
git push origin --delete hourly-scan-and-bugfixes
git push origin --delete hourly-scan/2026-03-21-ams-integration
git push origin --delete hourly-scanner-and-space-weather
git push origin --delete neo-close-approach-client
git push origin --delete wire-meteor-to-orchestrator
git push origin --delete feat/close-approach-client
git push origin --delete feat/hourly-scanner-and-cad-client
git push origin --delete feat/hourly-scanner-neo-tracking
git push origin --delete feat/neo-space-weather-clients
git push origin --delete feat/neo-tracking-and-historic-events
git push origin --delete feature/hourly-event-scanner
git push origin --delete hourly-meteor-integration-2026-03-22
git push origin --delete hourly-scan-neo-client
git push origin --delete hourly-scan-report
git push origin --delete hourly-watch-neo-client
git push origin --delete integrate-meteor-config
git push origin --delete neo-close-approach-tracking
git push origin --delete nightwatch/neo-tracking-and-event-journal
git push origin --delete feat/historic-fireballs-neo-client-voice-tools
git push origin --delete feat/hourly-neo-scanner
git push origin --delete feat/hourly-scan-and-close-approach
git push origin --delete feat/hourly-scan-neo-client
git push origin --delete feat/hourly-scan-report
git push origin --delete feat/hourly-scan-system
git push origin --delete feat/hourly-scanner-close-approach
git push origin --delete feat/hourly-scanner-neo-client
git push origin --delete feat/neo-close-approach-and-ams-fix
git push origin --delete feat/neo-close-approach-monitoring
git push origin --delete feat/neo-tracking-hourly-scanner
git push origin --delete fix/ams-monitoring-integration
git push origin --delete fix/hourly-scan-and-test-fixes-20260323
git push origin --delete fix/meteor-tracking-ams-hourly-scan
git push origin --delete hourly-scan-system
git push origin --delete hourly-scan/2026-03-23-test-coverage
git push origin --delete hourly/2026-03-23-meteor-tracking-enhancements
git push origin --delete neo-approach-client
git push origin --delete nightwatch-hourly-scan-2026-03-23
git push origin --delete feat/event-journal
git push origin --delete feat/hourly-event-scanner
git push origin --delete feat/hourly-neo-tracking-and-event-journal
git push origin --delete feat/neo-client-and-event-journal
git push origin --delete feat/neo-close-approach-client
git push origin --delete feat/neo-close-approach-tracking
git push origin --delete feat/neo-hourly-scanner
git push origin --delete feature/event-journal-and-neo-client
git push origin --delete feature/neo-close-approach-tracking
git push origin --delete hourly-scan-2026-03-24

# --- REVIEW: Old cursor/claude review & experiment branches, long behind main.
git push origin --delete claude/review-codebase-NsisM
git push origin --delete cursor/holistic-repo-review-5af9
git push origin --delete cursor/holistic-review-team-ownership-5a9b
git push origin --delete cursor/holistic-review-team-ownership-8f3f
git push origin --delete cursor/repo-operations-ownership-55a0
git push origin --delete cursor/repo-review-and-team-ownership-a9c0
git push origin --delete cursor/repo-review-team-and-issue-backlog-2d56
git push origin --delete cursor/setup-dev-environment-39bf
git push origin --delete claude/nightwatch-frontend-demo-takdve
git push origin --delete claude/install-review-org-37y4ck
git push origin --delete claude/repo-landscape-audit-mdpb4f
git push origin --delete cursor/nightwatch-demo-console-86da

# --- OLD-DEFAULT: Superseded old default branch (main is the default now — verify before deleting).
# git push origin --delete master

echo "Done. Remaining branches:"; git ls-remote --heads origin | wc -l