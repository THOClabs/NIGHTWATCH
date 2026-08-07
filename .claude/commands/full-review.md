---
description: Run the 7-level full repository review organization (agents in .claude/agents/)
argument-hint: [optional subtree path to scope a pilot run]
---

Run a complete review of this repository to build durable, full understanding.

You are the executive layer of a 7-level review organization; your standing staff is defined in .claude/agents/ — repo-cartographer (L1), git-historian (L2), domain-analyst (L3), security-auditor (L4), quality-auditor (L4), chief-architect (L5-6), executive-scribe (L7). Do not perform any analysis yourself: delegate every phase to the named agent and hold each to the output contract in its definition. On surfaces that support dynamic workflows you may run this as a workflow; otherwise orchestrate it directly with subagents.

If arguments were provided ($ARGUMENTS), treat this as a scoped pilot: restrict the entire organization to that subtree and cap Phase 3 at two domain-analysts.

Pipeline — strict ordering between phases, maximum parallelism within a phase. A phase may not begin until the prior phase's report file(s) exist on disk:

Phase 1 — Recon: repo-cartographer → docs/review/00-inventory.md
Phase 2 — Forensics: git-historian → docs/review/10-history.md
Phase 3 — Deep dives (matrix rows): take the "Suggested domain decomposition" from 00-inventory.md, spawn one domain-analyst PER DOMAIN in parallel, each assigned its domain name and directories → docs/review/20-domain-<slug>.md each
Phase 4 — Cross-cutting audits (matrix columns, in parallel): security-auditor → docs/review/30-security.md, quality-auditor → docs/review/31-quality.md. Both must consume every Phase 3 report and explicitly confirm or refute each analyst's flagged observations.
Phase 5 — Synthesis: chief-architect reads everything, resolves conflicts against the code → docs/review/40-architecture.md and docs/review/50-risk-register.md
Phase 6 — Board report: executive-scribe → docs/review/60-executive-summary.md, then updates CLAUDE.md inside its generated markers.

Rules of engagement:
- The entire organization is read-only toward source code. Writes are permitted ONLY under docs/review/, .claude/agent-memory/, and to CLAUDE.md.
- Every claim in every report cites file paths (file:line where useful). Surprising findings are independently re-verified before they appear in any report.
- If a phase's output is missing or malformed, re-run that agent before advancing; do not paper over gaps yourself.
- When complete: commit all review outputs on the current working branch, then reply with the executive summary verbatim and a table of contents of docs/review/.
