# Stale Branch Triage — NIGHTWATCH

_Generated 2026-08-02 · covers all remote branches on `origin` (`thoclabs/nightwatch`)_

## Purpose & scope

This is the **S5** deliverable from `REVIEW_RECONCILIATION.md`: take stock of the
~80 branches that accumulated on the remote and produce a **decision-ready prune
plan**. It is a report, not an action.

> **I have NOT deleted, merged, or force-pushed any branch.** Branch deletion is
> destructive and outward-facing, so every removal below is left for you to run
> (or approve) explicitly. Ready-to-paste commands are provided; nothing runs
> until you run it.

## The headline

`origin` currently carries **82 non-`main` branches**. They fall into four buckets:

| Bucket | Count | Recommendation |
|--------|------:|----------------|
| ✅ **Merged this session** (`fix/*`, squash-merged, content in `main`) | 11 | **Delete** — zero unique content remains |
| 🟡 **March 2026 NEO/meteor cluster** (orphans, never opened as PRs, 39 commits behind `main`) | 59 | **Delete after skimming 3 reference branches** (below) |
| 🟠 **June 2026 `cursor/*` review orphans** (no PR, superseded by the reconciliation) | 6 | **Delete** — findings already folded into the backlog |
| 🔵 **Legacy / misc** (`master`, `claude/review-codebase-NsisM`) | 2 | **Handle individually** — see notes; do **not** bulk-delete `master` |
| 🔒 **KEEP — back open PRs or are the working branch** | 4 | **Do not touch** |

Net: after this triage you can retire **78 of 82** branches. The repo's live
surface is really just `main` + four open PRs.

---

## 🔒 KEEP (4) — do not delete

These back **open** PRs (or are an active working branch). Leave them alone; the
open/merge decision is yours.

| Branch | PR | What it is |
|--------|----|-----------|
| `claude/repo-landscape-audit-mdpb4f` | #90 (open) | The landscape audit + `REVIEW_RECONCILIATION.md` (this session's docs). Also the base this triage PR branches from. |
| `claude/install-review-org-37y4ck` | #93 (open) | The "review organization" effort — the second of the two reconciled reviews. |
| `claude/nightwatch-frontend-demo-takdve` | #92 (open) | v0.1 frontend design prompt pack for Claude Design. |
| `cursor/setup-dev-environment-39bf` | #89 (open) | Cursor Cloud dev environment + `AGENTS.md`. |

_(PR #91 — `codex/78-canonical-repo-urls` — is open too but its head lives on a
fork, `JSap0914/NIGHTWATCH`, so there is no branch on our remote to prune.)_

---

## ✅ Bucket 1 — Merged this session (11) → safe to delete

Every branch below was squash-merged into `main` this session; each squash commit
(`#94`–`#104`) is present in `git log origin/main`. The original branch commits show
as "ahead" of `main` only because squash rewrites SHAs — **the content is fully in
`main`**, so nothing is lost by deleting them. This is the safest bucket.

| Branch | PR | Merged as |
|--------|----|-----------|
| `fix/stage-0-boot-visibility` | #97 | `5b58ea7` |
| `fix/stage-1-physical-safety` | #95 | `5545d8a` |
| `fix/stage-2-data-integrity` | #94 | `55c7d6b` |
| `fix/stage-3-security-hardening` | #96 | `3bb9a20` |
| `fix/test-suite-hardening` | #98 | `ab4fe00` |
| `fix/flaky-power-events-test` | #100 | `4e3efbd` |
| `fix/stage-4-protocol-conformance` | #99 | `d891946` |
| `fix/stage-4-mount-async` | #101 | `8054bd9` |
| `fix/stage-4-lifecycle` | #102 | `83b8b99` |
| `fix/stage-4-aliases` | #103 | `fb061c3` |
| `fix/stage-4-dispatcher` | #104 | `1fda788` |

```bash
# Bucket 1 — merged this session (safest; content is in main)
git push origin --delete \
  fix/stage-0-boot-visibility fix/stage-1-physical-safety \
  fix/stage-2-data-integrity fix/stage-3-security-hardening \
  fix/test-suite-hardening fix/flaky-power-events-test \
  fix/stage-4-protocol-conformance fix/stage-4-mount-async \
  fix/stage-4-lifecycle fix/stage-4-aliases fix/stage-4-dispatcher
```

---

## 🟡 Bucket 2 — The March 2026 NEO/meteor cluster (59) → delete after skimming

**What this is:** between **2026-03-21 and 2026-03-24**, a single feature —
_"hourly sky-event scanner with NEO close-approach tracking, an event journal, AMS
meteor integration, and NOAA space-weather awareness"_ — was attempted **59 times
in parallel**. Nearly every branch is a near-duplicate re-roll of the same idea
under a different name (`feat/`, `feature/`, `hourly-*`, `neo-*`, `nightwatch/*`,
`fix/*`). Distinguishing facts:

- **None of the 59 was ever opened as a pull request.** They were pushed and
  abandoned — no review, no discussion, no merge intent on record.
- **All 59 are 39 commits behind `main`** and each is only 1–8 commits ahead of a
  now-ancient merge-base. Since March, `main` has absorbed the entire safety/CI/
  Protocol overhaul (PRs #94–#104). None of these branches would rebase cleanly;
  each would need a from-scratch reimplementation against current `main`.

**Therefore: treat the whole cluster as one stalled feature, not 59 branches to
salvage.** Do not try to revive a branch — instead, if you still want this feature,
mine **one** representative for its design/data and reimplement fresh. Below are the
best reference branches to skim before deleting the rest. They are **reference
specs, not mergeable branches.**

### Reference branches worth a skim before deletion

| Capability | Best reference branch | Why this one |
|-----------|----------------------|--------------|
| **Overall / most complete** | `feat/neo-close-approach-client` | Richest single branch — 8 commits ahead, 12 files; the fullest end-to-end take. |
| **Hourly event scanner** | `feat/hourly-event-scanner` | Most-evolved scanner: adds severity classification + zone mapping (11 files). |
| **Event journal (persistence)** | `feat/event-journal` | Cleanest, most focused — a single persistent `EventJournal` (5 files), easy to read as a spec. |
| **NEO / CNEOS CAD API client** | `feature/close-approach-client` | Focused first cut of just the NASA CNEOS Close-Approach-Data client. |
| **NOAA space-weather clients** | `feat/neo-space-weather-clients` | Focused NEO + NOAA space-weather client pair (6 files). |
| **AMS meteor→orchestrator wiring + trajectory bug** | `fix/ams-monitoring-integration` | Tightly scoped (2 files): wires the AMS client into the monitoring loop and fixes a trajectory calc. |
| **⚠ Possible real bug fixes** | `fix/hourly-scan-and-test-fixes-20260323` | Claims _"Fix 12 bugs across catalog, mount, focuser, orchestrator, and tests."_ Some may still apply to `main` — **worth a diff before deleting** in case any fix was never independently reproduced. |

> **Recommendation:** open the six capability references + the bug-fix branch in a
> browser (or `git diff origin/main...<branch>`), copy anything you still want into a
> fresh issue or spec, **then** delete all 59. Given they're 39 behind and the
> feature was never PR'd, my default recommendation is to prune the whole cluster and
> re-scope the scanner as new work gated on the CI/Protocol suite that now exists.

<details>
<summary><b>All 59 March-cluster branches (click to expand)</b></summary>

```
add-event-journal-and-neo-client
feat/close-approach-client
feat/event-journal
feat/historic-fireballs-neo-client-voice-tools
feat/hourly-event-polling
feat/hourly-event-scanner
feat/hourly-neo-scanner
feat/hourly-neo-tracking-and-event-journal
feat/hourly-scan-and-close-approach
feat/hourly-scan-neo-client
feat/hourly-scan-report
feat/hourly-scan-system
feat/hourly-scanner-and-cad-client
feat/hourly-scanner-close-approach
feat/hourly-scanner-neo-client
feat/hourly-scanner-neo-tracking
feat/neo-client-and-event-journal
feat/neo-client-hourly-scan
feat/neo-close-approach-and-ams-fix
feat/neo-close-approach-client
feat/neo-close-approach-monitoring
feat/neo-close-approach-tracking
feat/neo-hourly-scan
feat/neo-hourly-scanner
feat/neo-space-weather-clients
feat/neo-space-weather-hourly-scan
feat/neo-tracking-and-event-log
feat/neo-tracking-and-event-logs
feat/neo-tracking-and-historic-events
feat/neo-tracking-hourly-scanner
feat/trajectory-biased-hopi-circles
feature/close-approach-client
feature/event-journal-and-neo-client
feature/hourly-event-scanner
feature/neo-client-scan-log
feature/neo-close-approach-client
feature/neo-close-approach-tracking
feature/neo-tracking-and-event-log
fix/ams-monitoring-integration
fix/hourly-scan-and-test-fixes-20260323
fix/meteor-tracking-ams-hourly-scan
hourly-meteor-integration-2026-03-22
hourly-scan-2026-03-24
hourly-scan-and-bugfixes
hourly-scan-neo-client
hourly-scan-report
hourly-scan-system
hourly-scan/2026-03-21-ams-integration
hourly-scan/2026-03-23-test-coverage
hourly-scanner-and-space-weather
hourly-watch-neo-client
hourly/2026-03-23-meteor-tracking-enhancements
integrate-meteor-config
neo-approach-client
neo-close-approach-client
neo-close-approach-tracking
nightwatch-hourly-scan-2026-03-23
nightwatch/neo-tracking-and-event-journal
wire-meteor-to-orchestrator
```
</details>

```bash
# Bucket 2 — March 2026 NEO/meteor cluster (59). Skim the reference branches first.
git push origin --delete \
  add-event-journal-and-neo-client feat/close-approach-client feat/event-journal \
  feat/historic-fireballs-neo-client-voice-tools feat/hourly-event-polling \
  feat/hourly-event-scanner feat/hourly-neo-scanner feat/hourly-neo-tracking-and-event-journal \
  feat/hourly-scan-and-close-approach feat/hourly-scan-neo-client feat/hourly-scan-report \
  feat/hourly-scan-system feat/hourly-scanner-and-cad-client feat/hourly-scanner-close-approach \
  feat/hourly-scanner-neo-client feat/hourly-scanner-neo-tracking feat/neo-client-and-event-journal \
  feat/neo-client-hourly-scan feat/neo-close-approach-and-ams-fix feat/neo-close-approach-client \
  feat/neo-close-approach-monitoring feat/neo-close-approach-tracking feat/neo-hourly-scan \
  feat/neo-hourly-scanner feat/neo-space-weather-clients feat/neo-space-weather-hourly-scan \
  feat/neo-tracking-and-event-log feat/neo-tracking-and-event-logs feat/neo-tracking-and-historic-events \
  feat/neo-tracking-hourly-scanner feat/trajectory-biased-hopi-circles feature/close-approach-client \
  feature/event-journal-and-neo-client feature/hourly-event-scanner feature/neo-client-scan-log \
  feature/neo-close-approach-client feature/neo-close-approach-tracking feature/neo-tracking-and-event-log \
  fix/ams-monitoring-integration fix/hourly-scan-and-test-fixes-20260323 fix/meteor-tracking-ams-hourly-scan \
  hourly-meteor-integration-2026-03-22 hourly-scan-2026-03-24 hourly-scan-and-bugfixes \
  hourly-scan-neo-client hourly-scan-report hourly-scan-system \
  hourly-scan/2026-03-21-ams-integration hourly-scan/2026-03-23-test-coverage \
  hourly-scanner-and-space-weather hourly-watch-neo-client \
  hourly/2026-03-23-meteor-tracking-enhancements integrate-meteor-config \
  neo-approach-client neo-close-approach-client neo-close-approach-tracking \
  nightwatch-hourly-scan-2026-03-23 nightwatch/neo-tracking-and-event-journal \
  wire-meteor-to-orchestrator
```

---

## 🟠 Bucket 3 — June 2026 `cursor/*` review orphans (6) → delete

Six competing "holistic review / team-ownership / issue-backlog" branches from
**2026-06-23**. None was opened as a PR. Their substance — findings, ownership
model, backlog — was reconciled into the current backlog in
`REVIEW_RECONCILIATION.md`, so they carry no unique live value.

```
cursor/holistic-repo-review-5af9
cursor/holistic-review-team-ownership-5a9b
cursor/holistic-review-team-ownership-8f3f
cursor/repo-operations-ownership-55a0
cursor/repo-review-and-team-ownership-a9c0
cursor/repo-review-team-and-issue-backlog-2d56
```

```bash
# Bucket 3 — cursor review orphans (superseded by REVIEW_RECONCILIATION.md)
git push origin --delete \
  cursor/holistic-repo-review-5af9 cursor/holistic-review-team-ownership-5a9b \
  cursor/holistic-review-team-ownership-8f3f cursor/repo-operations-ownership-55a0 \
  cursor/repo-review-and-team-ownership-a9c0 cursor/repo-review-team-and-issue-backlog-2d56
```

---

## 🔵 Bucket 4 — Legacy / misc (2) → handle individually

- **`master`** (2026-03-24, 8 ahead / 39 behind) — the repo's **pre-`main` default
  branch**. Its unique commits are just more of the March scanner cluster
  (_"Add space weather tracking and March 24 hourly event scan"_). Recommendation:
  delete it **once you've confirmed** nothing still points at it — check the default
  branch is `main` (it is), and that no CI trigger, badge, deploy hook, or external
  clone references `master`. Because a stray legacy default can be load-bearing for
  tooling, I've deliberately **left it out of the bulk command**:
  ```bash
  # Only after confirming nothing references `master`:
  git push origin --delete master
  ```

- **`claude/review-codebase-NsisM`** (2026-02-23, 1 file, no PR) — an old one-file
  codebase-review doc, superseded by the audit on #90. Safe to delete:
  ```bash
  git push origin --delete claude/review-codebase-NsisM
  ```

---

## How this was determined (methodology)

- **Merge status** came from the GitHub PR records (`merged_at` set) cross-checked
  against `git log origin/main` for each squash commit — not from `git branch
  --merged`, which misses squash-merges.
- **"Never PR'd"** means the branch name never appears as a PR head ref in the
  repo's full PR list (#1–#104).
- **Ahead/behind and file counts** are `git rev-list --count` / `git diff
  --name-only` against `origin/main`'s merge-base, taken 2026-08-02.
- A branch was only ever placed in a **delete** bucket when its content is either
  (a) provably in `main` (Bucket 1) or (b) an un-PR'd orphan ≥39 commits behind with
  a live successor path (Buckets 2–4).

## Suggested order of operations

1. Run **Bucket 1** now (zero risk — content is in `main`).
2. Skim the 7 reference branches in **Bucket 2**; copy anything you still want into
   a fresh issue/spec; then run the Bucket 2 command.
3. Run **Bucket 3**.
4. Confirm `master` is unreferenced, then delete it and `claude/review-codebase-NsisM`.
5. You're left with `main` + PRs #89/#90/#92/#93 — decide each of those on its own.
