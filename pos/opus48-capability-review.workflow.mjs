/**
 * NIGHTWATCH — Opus 4.8 (1M) Capability Re-Review  ·  Panel of Specialists
 * ----------------------------------------------------------------------------
 * This is a Claude Code *dynamic workflow* — run it with the Workflow tool
 * (NOT GitHub Actions):
 *
 *     Workflow({ scriptPath: "<repo>/pos/opus48-capability-review.workflow.mjs" })
 *     // optional: args = { repoRoot: "/abs/path/to/NIGHTWATCH" }
 *
 * WHY THIS EXISTS
 * NIGHTWATCH was designed and planned in the early-Opus-4 / late-Claude-3 era,
 * when the *builder* model couldn't hold the whole codebase in context and agents
 * were weaker — so the plan favored many small hand-held tasks and conservative
 * autonomy. We now build with Opus 4.8 + a 1M-token context: an agent can hold the
 * entire system at once and execute large, coherent changes. This POS re-review asks
 * one question from five expert lenses: given that leap in the BUILDER's capability,
 * what can NIGHTWATCH now become — which v0.2 gaps are suddenly cheap, what new
 * autonomy is unlocked — and (do-good-us) what we must deliberately NOT do.
 *
 * GUARDRAILS (immovable):
 *   - RUNTIME stays no-cloud / local-AI. The builder leap is about how we develop it.
 *   - Safety stays DETERMINISTIC. No LLM in the hard-safety loop, ever.
 *   - Nothing proposed should exceed a solo dev + a small hardware budget.
 *
 * It follows the project's existing POS tradition (see pos/POS_RETREAT_SIMULATION.md)
 * and writes a leverage-ranked roadmap to pos/OPUS48_CAPABILITY_REVIEW.md.
 */

export const meta = {
  name: 'nightwatch-opus48-pos-review',
  description: 'Panel-of-Specialists re-review of NIGHTWATCH for the Opus 4.8 (1M) era: what is now buildable that the early-Opus-4/Claude-3-era plan assumed away. Grounds in the real codebase, converges to a leverage-ranked roadmap, and keeps the safety loop deterministic + the runtime no-cloud.',
  phases: [
    { title: 'Ground', detail: 'read the codebase, ROADMAP, v0.2 gaps, modernization plan, and the early-model assumptions baked in' },
    { title: 'Panel', detail: 'five named specialist lenses each assess what Opus 4.8 1M unlocks' },
    { title: 'Converge', detail: 'synthesize agreements, tensions, a leverage-ranked roadmap, and a do-not-do list' },
    { title: 'Roadmap', detail: 'write the review into pos/OPUS48_CAPABILITY_REVIEW.md' },
  ],
}

const REPO = (args && args.repoRoot) || '/Users/timhennessey/wessa/projects/NIGHTWATCH'
const PLAN = '/Users/timhennessey/.claude/plans/good-catch-on-the-glistening-deer.md'

const CONTEXT = `NIGHTWATCH = a voice-controlled autonomous observatory (Python, uv, pytest). Layered: nightwatch/ (orchestrator, voice pipeline, safety state machines), services/ (21 domain services: mount_control, weather, safety_monitor, ephemeris, catalog, camera, guiding, astrometry, focus, voice, meteor_tracking, scheduling, simulators, alpaca, indi, nlp, power, enclosure, encoder, alerts), voice/ (audio I/O + LLM tool registrations), tests/ (unit/integration/e2e/hardware). v0.1 dev; v0.2 gaps still open: camera capture, plate-solving, autoguiding, autofocus (partial), web UI, all-sky. RUNTIME is no-cloud / local-AI (NVIDIA DGX Spark). License CC BY-NC-SA 4.0. It already practices POS (see ${REPO}/pos/, spine POS_RETREAT_SIMULATION.md). CLAUDE.md + ROADMAP.md + NIGHTWATCH_Build_Package.md + the ~290-task modernization plan at ${PLAN} hold the design intent.

THE PIVOT: NIGHTWATCH was designed/planned when the BUILDER model was early-Opus-4 / late-Claude-3 — limited context, weaker agents — so the plan favored many small hand-held tasks and conservative autonomy. We now build with Opus 4.8 + 1M context: an agent can hold the whole codebase, reason across all 21 services at once, and execute large coherent changes. RE-EVALUATE accordingly. Always distinguish BUILDER capability (how we develop NIGHTWATCH) from RUNTIME (the observatory itself, which stays no-cloud, local-AI, deterministic-safety). do-good-us: never put an LLM in the hard-safety loop; never propose what a solo dev + small budget cannot actually run.`

const GUARD = `GROUND TRUTH ONLY: read real files under ${REPO} (and ${PLAN}); never invent services, file paths, or capabilities. If unsure, say so. Be concrete and honest — this is a real project Tim is building, not a brainstorm.`

const BRIEF_SCHEMA = {
  type: 'object',
  properties: {
    ships_today: { type: 'string', description: 'what actually works now (services implemented + tested)' },
    open_gaps: { type: 'array', items: { type: 'string' }, description: 'the real v0.2+ gaps' },
    early_model_assumptions: { type: 'array', items: { type: 'string' }, description: 'places where the architecture/plan is shaped by the builder being weak — small tasks, limited context, conservative autonomy, manual orchestration' },
    immovable_constraints: { type: 'array', items: { type: 'string' }, description: 'what must NOT move: deterministic safety, no-cloud runtime, solo-dev buildability' },
  },
  required: ['ships_today', 'open_gaps', 'early_model_assumptions', 'immovable_constraints'],
}

const LENS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    now_unlocked: { type: 'array', items: { type: 'string' }, description: 'concrete capabilities that are now cheap/possible because the builder is Opus 4.8 1M' },
    reconsider: { type: 'array', items: { type: 'string' }, description: 'design/plan choices worth revisiting given the leap' },
    cautions: { type: 'array', items: { type: 'string' }, description: 'what NOT to do from this lens (esp. safety / over-automation / scope)' },
    top_pick: { type: 'string', description: 'the single highest-leverage move from this lens' },
  },
  required: ['lens', 'now_unlocked', 'reconsider', 'cautions', 'top_pick'],
}

const CONVERGE_SCHEMA = {
  type: 'object',
  properties: {
    headline: { type: 'string', description: 'one-sentence verdict: what NIGHTWATCH can now become' },
    agreements: { type: 'array', items: { type: 'string' } },
    tensions: { type: 'array', items: { type: 'string' }, description: 'where the lenses disagree, stated honestly' },
    ranked_roadmap: { type: 'array', items: { type: 'string' }, description: 'leverage-ordered moves, each with a rough effort tag (S/M/L) and why-now' },
    do_not_do: { type: 'array', items: { type: 'string' } },
    next_three: { type: 'array', items: { type: 'string' }, description: 'the three things to start first' },
  },
  required: ['headline', 'agreements', 'tensions', 'ranked_roadmap', 'do_not_do', 'next_three'],
}

phase('Ground')
const brief = await agent(`${GUARD}\n\n${CONTEXT}\n\nGROUND THE PANEL. Read the NIGHTWATCH codebase (nightwatch/, services/, voice/), ROADMAP.md, CLAUDE.md, and the modernization plan at ${PLAN}. Produce a tight grounding brief: (a) what actually ships today vs the open gaps; (b) the EARLY-MODEL ASSUMPTIONS baked into the architecture/plan — places where the design is shaped by the builder being weak; (c) the hard constraints that must NOT move. Return the schema.`,
  { label: 'ground:brief', phase: 'Ground', schema: BRIEF_SCHEMA })
const briefBlob = JSON.stringify(brief, null, 1).slice(0, 8000)
log(`Ground: ${brief.open_gaps.length} open gaps, ${brief.early_model_assumptions.length} early-model assumptions identified`)

phase('Panel')
const LENSES = [
  { key: 'autonomy', persona: 'Dr. Vega — Observatory Autonomy Architect', focus: 'whole-session autonomy now that a builder model holds the entire codebase: end-to-end "plan and run tonight" orchestration, the scheduler, cross-service coherence, failure recovery / replanning. What conservative-autonomy choices were made because the old builder could not reason across the whole system?' },
  { key: 'imaging', persona: 'Kepler — Astro-Imaging & Acquisition Scientist', focus: 'the v0.2 acquisition gaps — plate-solving, autoguiding, autofocus, all-sky, meteor tracking, the image pipeline — which are now cheap to build well, and what new science (dim-target acquisition, transient response) that unlocks.' },
  { key: 'localai', persona: 'Sloan — Local-AI / Edge-Inference Engineer', focus: 'NIGHTWATCH stays no-cloud at RUNTIME (DGX Spark). How does the BUILDER leap change what we can implement, and should the runtime local-AI design evolve (stronger local models, hybrid offline planning, distillation of cloud-planned policies) — WITHOUT breaking the no-cloud principle? Be explicit about the builder/runtime split.' },
  { key: 'safety', persona: 'Sentinel — Safety & Reliability Engineer', focus: 'the safety state machines, watchdogs, fail-safes. Stronger models tempt putting AI in the safety loop — your job is to RESIST that and keep safety deterministic. But better builders can harden FMEA, advisory anomaly DETECTION, fault injection, and test coverage. Draw the bright line.' },
  { key: 'voice', persona: 'Echo — Voice/NLP & Operator Experience', focus: 'the voice pipeline + LLM tool registrations: richer multi-step natural commands, planning dialogs ("plan tonight around the weather window"), situational summaries, graceful clarification — what stronger reasoning makes conversational that used to be rigid command-matching.' },
]
const panelThunks = LENSES.map((L) => () =>
  agent(`${GUARD}\n\n${CONTEXT}\n\nYou are ${L.persona}, a specialist on the NIGHTWATCH review panel (POS method — your lens deliberates, then a convergence step reconciles all five). YOUR LENS: ${L.focus}\n\nGround your assessment in the brief below and in the real code you read. Give CONCRETE, NIGHTWATCH-specific findings (name services, files, gaps), not generic AI cheerleading. Hold the line on the immovable constraints. Return the schema with lens="${L.key}".\n\nGROUNDING BRIEF:\n${briefBlob}`,
    { label: `panel:${L.key}`, phase: 'Panel', schema: LENS_SCHEMA }))
const panel = (await parallel(panelThunks)).filter(Boolean)
log(`Panel: ${panel.length}/${LENSES.length} lenses reported`)

phase('Converge')
const converge = await agent(`${GUARD}\n\n${CONTEXT}\n\nYou are the CONVERGENCE chair (the Pragmatist) for the NIGHTWATCH Opus-4.8 POS review. Five specialist lenses have reported (below). Synthesize per the POS method: state the headline verdict, the genuine agreements, the honest tensions (don't paper over disagreement), then a LEVERAGE-RANKED roadmap (highest value-per-effort first, each tagged S/M/L effort + a why-now), a do-not-do list (protect deterministic safety, no-cloud runtime, solo-dev scope), and the next three things to start. Be decisive and concrete. Return the schema.\n\nBRIEF:\n${briefBlob}\n\nPANEL:\n${JSON.stringify(panel, null, 1).slice(0, 16000)}`,
  { label: 'converge:chair', phase: 'Converge', schema: CONVERGE_SCHEMA })

phase('Roadmap')
const ROADMAP_SCHEMA = {
  type: 'object',
  properties: {
    doc_path: { type: 'string' },
    summary: { type: 'string', description: '5-8 line plain summary for Tim' },
  },
  required: ['doc_path', 'summary'],
}
const written = await agent(`${GUARD}\n\nWrite the POS review into ${REPO}/pos/OPUS48_CAPABILITY_REVIEW.md using the Write tool. Structure: title + date-agnostic intro (the builder-leap pivot, builder-vs-runtime split, the immovable guardrails) → the headline verdict → per-lens highlights (5 specialists) → agreements → honest tensions → the leverage-ranked roadmap (table: move / effort S-M-L / why-now) → do-not-do → "start these three". Markdown, conventional, honest, no filler. Do NOT run git. Then return the schema.\n\nHEADLINE + CONVERGENCE:\n${JSON.stringify(converge, null, 1).slice(0, 14000)}\n\nPANEL DETAIL:\n${JSON.stringify(panel, null, 1).slice(0, 12000)}`,
  { label: 'roadmap:write', phase: 'Roadmap', schema: ROADMAP_SCHEMA })

return {
  review: 'NIGHTWATCH Opus 4.8 (1M) capability re-review',
  headline: converge.headline,
  next_three: converge.next_three,
  do_not_do: converge.do_not_do,
  doc: written.doc_path,
  summary_for_tim: written.summary,
}
