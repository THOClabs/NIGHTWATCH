<context>
Build a prototype of the NIGHTWATCH v0.1 demo frontend — a mission-control web application for a voice-controlled, autonomous astronomical observatory.

I'm building the first user interface for NIGHTWATCH, an open-source observatory control system for a remote dark-sky property in central Nevada (38.9°N, 117.4°W, 1,800 m elevation). The physical system is a hand-figured Russian Intes Micro MN76 Maksutov-Newtonian telescope riding a DIY harmonic-drive German Equatorial Mount inside a motorized roll-off-roof shed, run entirely by local AI (no cloud) with a voice-first control surface. The Python backend already exists — orchestrator, twenty-one services, seventy typed voice tools, safety interlocks, meteor tracking. What does not exist is any way to *see* it. This demo is for the observatory's owner-operator, who is often hundreds of miles from the site: they need to coordinate a night of observing from afar, trust that the safety system is protecting a five-figure instrument from rain and wind, and feel present at the telescope through a living picture of the machine. The demo must prove three things: that remote operation feels safe and legible, that a digital twin of the physical rig can show the machine actually moving, and that talking to an observatory is a natural way to run one.

Four things define this project's character, and the design should express all four:

1. **The high desert at night.** Central Nevada at 6,000 feet: near-black indigo sky, hard bright stars, sage and dust below the horizon line. The interface is a window kept dark so the sky stays visible.
2. **Instrument heritage.** The optics were hand-figured in Russia; the mount uses machined harmonic drives; the aesthetic ancestors are brass telescopes, engraved setting circles, and engineering drawings — precision instruments, not consumer dashboards.
3. **Safety-critical engineering culture.** Rain on an open primary mirror is unrecoverable. The backend enforces warning → park → emergency threshold tiers, dual-redundant rain sensors, a hardware watchdog, and a strict "cancel, then close" emergency ordering. The UI must treat safety state as the loudest voice in the room, always visible, never decorative.
4. **The Lexicon.** The meteor-tracking subsystem has its own quiet, mystical sub-brand: alerts written in a constructed language ("presa-nightwatch. velmu-sky. do-good-us."), prayers of finding and watching closed with the alchemical glyph 🜏, and expanding "Hopi circle" ground-search patterns for meteorite recovery. This reverent voice belongs only to the Meteor module — a hidden chapel inside the machine shop.

Audience: a single expert operator (the owner) plus the people they demo the project to. Density is a virtue; this is an instrument panel, not a marketing site. Desktop-first.
</context>

<design_system>
Theme name: **High Desert Brass**. Dark-first, engineered around night vision, with brass as the metal of interaction. These tokens are hard rules, not suggestions — define them as CSS variables at the root and use only them.

## Color tokens

```css
:root {
  /* Canvas — zenith sky, indigo-black, never neutral gray */
  --nw-bg:            #0A0E1A;  /* app background */
  --nw-surface:       #121A2C;  /* cards, panels */
  --nw-surface-hover: #182238;  /* raised/hover surfaces */
  --nw-hairline:      rgba(138, 147, 168, 0.16);  /* borders, dividers, gauge tracks */

  /* Text — moonlight on slate */
  --nw-text:          #E9ECF5;  /* primary */
  --nw-text-dim:      #8A93A8;  /* secondary, labels, units */

  /* Brand metal — hand-rubbed brass. Means "you can act": buttons,
     active nav, focus rings, links, selected states, the twin's fittings. */
  --nw-brass:         #C9A227;
  --nw-brass-bright:  #E0BC55;  /* hover/active */

  /* Grounding — Nevada terrain, used sparingly for landscape and neutral fills */
  --nw-sage:          #77876B;
  --nw-dust:          #B8A98E;

  /* Lexicon — ionized violet. ONLY inside the Meteor module. */
  --nw-lexicon:       #9A8FD0;
  --nw-lexicon-glow:  #C4BBEB;

  /* Safety semantics — reserved exclusively for safety/status meaning,
     never used decoratively. Amber means "nature is warning you";
     it is hotter and more saturated than brass so the two never read alike. */
  --nw-safe:          #3FB27F;
  --nw-marginal:      #F59E2D;
  --nw-unsafe:        #E4572E;
  --nw-emergency:     #FF3B4E;  /* the only color licensed to pulse */

  /* Data-viz sequential ramp — "airglow", low to high */
  --nw-viz-1:         #16233F;
  --nw-viz-2:         #2E7F8F;
  --nw-viz-3:         #7FD4C1;
  --nw-viz-4:         #E9ECF5;
  /* Categorical series order: brass, teal (#2E7F8F), sage, slate-blue (#5B6E9E), violet last */
}
```

**Rubylith night-vision mode.** A global toggle (moon icon in the top strip) swaps the token set to preserve the operator's dark adaptation at the telescope: `--nw-bg: #1A0505`, surfaces `#241010`, all text and icons remap to reds (`#FF6B5A` primary, `#B04438` dim), brass remaps to `#C25B4A`, all greens/ambers/blues remap to red luminance steps (safety tiers become increasingly bright red), charts render in the red ramp, and all imagery gets a `sepia + hue-rotate` red filter. Implement it purely as a `[data-theme="rubylith"]` token swap — same layout, same components, zero redesign.

## Typography

- **Space Grotesk** — UI text, navigation, buttons, body. Do not use Inter, Roboto, or Arial.
- **JetBrains Mono** — every telemetry number: coordinates, timestamps, temperatures, RMS values, step counts. Always with tabular figures so ticking values don't jitter. Coordinates render in astronomical notation (`21h 32m 43s`, `+30° 14′ 09″`).
- **Fraunces** (or a similar high-contrast display serif) — module display headings only, like an engraved brass plaque: the word "MISSION CONTROL" atop the dashboard, "THE RIG" atop the twin. Never for body text.
- Load from Google Fonts if the environment allows; otherwise fall back to `ui-sans-serif` / `ui-monospace` / `Georgia` — but never substitute Inter.

## Space, shape, depth, motion

- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 px. Dense but breathing — instrument panel, not spreadsheet.
- Radius: 6 px cards, 4 px controls, 999 px pills/chips. No heavy rounding.
- Elevation: hairline borders first, shadows second (`0 1px 0 rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.35)` max). Dark UIs live and die by borders, not shadows.
- Iconography: thin-stroke (1.5 px), geometric, engineering-drawing character. Inline SVG only.
- Motion: physical elements (twin, gauges, progress) move at simulation-truth speeds; UI chrome uses 150–200 ms ease-out. One orchestrated page-load reveal (staggered 40 ms per panel, rising 8 px) rather than scattered micro-interactions. Only `--nw-emergency` elements may pulse (1.2 s breathing glow). Animate `transform`/`opacity` only.

## Do / Don't

- Do commit to the dark indigo canvas everywhere; there is no light mode — Rubylith is the only alternate theme.
- Do give every numeric readout its unit in `--nw-text-dim` small caps (`mph`, `″ RMS`, `°C`).
- Don't use safety colors for anything but safety meaning (no green "success" toasts for mundane actions; use brass).
- Don't use purple/violet anywhere outside the Meteor module.
- Don't use gradients except: the airglow viz ramp, a subtle horizon glow in the twin's sky, and the Lexicon panel's violet aura.
- Don't use placeholder text anywhere — every string in this demo is real domain content (real object names, real thresholds, real Lexicon vocabulary).
</design_system>

<data_model>
This is the ground truth. Every displayed value binds to these types, which are transcribed from the real Python backend. Implement this model exactly — do not invent fields, and do not contradict the physics constants.

```ts
// ——— Enums (verbatim from the backend) ———
type SafetyLevel   = 'safe' | 'marginal' | 'unsafe' | 'emergency';
type SafetyAction  = 'safe_to_observe' | 'park_and_wait' | 'park_for_daylight'
                   | 'emergency_close' | 'dew_warning' | 'cold_warning'
                   | 'low_battery_warning' | 'low_battery_park' | 'low_battery_shutdown'
                   | 'network_failure' | 'power_failure' | 'safety_veto';
type AlertLevel    = 'info' | 'warning' | 'critical' | 'emergency';
type MountState    = 'parked' | 'unparking' | 'idle' | 'slewing' | 'tracking' | 'parking' | 'error';
type PierSide      = 'east' | 'west';
type TrackingRate  = 'sidereal' | 'lunar' | 'solar' | 'king' | 'stopped';
type RoofState     = 'open' | 'closed' | 'opening' | 'closing' | 'unknown' | 'error';
type PowerState    = 'online' | 'on_battery' | 'low_battery' | 'charging';
type PipelineState = 'idle' | 'listening' | 'transcribing' | 'processing' | 'executing' | 'speaking' | 'error';
type FrameGrade    = 'excellent' | 'good' | 'acceptable' | 'marginal' | 'reject';
type RejectionReason = 'none' | 'high_fwhm' | 'elongated_stars' | 'low_star_count'
                     | 'high_background' | 'saturated' | 'low_snr' | 'trailing' | 'gradient';
type SuggestionType  = 'target' | 'action' | 'warning' | 'optimization' | 'info';
type SuggestionPriority = 1 | 2 | 3 | 4;  // low, medium, high, urgent
type ScheduleQuality = 'excellent' | 'good' | 'fair' | 'marginal' | 'poor';
type ScheduleReason  = 'optimal_altitude' | 'moon_avoidance' | 'weather_window'
                     | 'user_preference' | 'historical_success' | 'time_constraint' | 'meridian_transit';
type SessionPhase  = 'planning' | 'starting' | 'observing' | 'transitioning' | 'paused' | 'ending' | 'complete';

type EventType =
  | 'mount_position_changed' | 'mount_slew_started' | 'mount_slew_complete'
  | 'mount_parked' | 'mount_unparked'
  | 'weather_changed' | 'weather_safe' | 'weather_unsafe'
  | 'safety_state_changed' | 'safety_alert' | 'safety_veto'
  | 'guiding_state_changed' | 'guiding_started' | 'guiding_stopped'
  | 'guiding_lost' | 'guiding_settled' | 'guiding_dither'
  | 'session_started' | 'session_ended' | 'image_captured'
  | 'service_started' | 'service_stopped' | 'service_error' | 'shutdown_initiated';

// ——— Live state ———
interface MountStatus {
  state: MountState;
  raHours: number;          // 0..24
  decDegrees: number;       // -90..+90
  altDegrees: number;       // horizon = 0
  azDegrees: number;        // N=0 E=90
  pierSide: PierSide;
  trackingRate: TrackingRate;
  hourAngleDeg: number;     // -180..+180, negative = east of meridian
  target?: { name: string; raHours: number; decDegrees: number };
  slewProgress?: number;    // 0..1 while state === 'slewing'
  pointingErrorArcsec: number;
}

interface RoofStatus {
  state: RoofState;
  positionPercent: number;      // 0 = closed, 100 = open — animate this
  motorRunning: boolean;
  motorCurrentA: number;        // cutoff at 5.0 A (obstruction)
  canOpen: boolean; canClose: boolean;
  interlockReasons: string[];   // e.g. ['telescope_not_parked', 'rain_holdoff']
  rainHoldoffRemainingMin: number | null;   // 30-min holdoff after rain stops
}

interface Conditions {
  temperatureC: number; humidityPercent: number; dewPointC: number;
  windSpeedMph: number; windGustMph: number; windDirectionDeg: number;
  pressureHpa: number;
  isRaining: boolean;
  rainPrimary: boolean; rainSecondary: boolean;   // dual-redundant sensors, 1-of-2 votes closes the roof
  skyTempC: number; skyAmbientDiffC: number;      // < -25 clear · -25..-15 partly · > -15 cloudy
  cloudCondition: 'clear' | 'partly_cloudy' | 'cloudy';
  sunAltitudeDeg: number;                          // above -12° = daylight, telescope parks
  estimatedSeeingArcsec: number;                   // 0.8 excellent … 4+ poor
  seeingCategory: 'excellent' | 'good' | 'average' | 'poor';
}

interface SafetyStatus {
  level: SafetyLevel;
  action: SafetyAction;
  isSafe: boolean;
  alertLevel: AlertLevel;
  reasons: string[];
  subsystems: {   // drives the twin's component coloring and the interlock matrix
    weather: boolean; clouds: boolean; daylight: boolean; mount: boolean;
    power: boolean; enclosure: boolean; altitude: boolean; meridian: boolean; network: boolean;
  };
}

interface GuideStats {
  state: 'stopped' | 'calibrating' | 'guiding' | 'settling' | 'lost';
  rmsTotalArcsec: number; rmsRaArcsec: number; rmsDecArcsec: number;
  peakRaArcsec: number; peakDecArcsec: number;
  snr: number; starMass: number; frameNumber: number;
  history: Array<{ t: number; raErr: number; decErr: number }>;  // for strip + scatter charts
  calibration?: { raRateArcsecPerSec: number; decRateArcsecPerSec: number; orthogonalityDeg: number };
}

interface Almanac {
  lstHours: number;                         // local sidereal time, ticking
  sunAltitudeDeg: number;
  astronomicalDarkStart: string; astronomicalDarkEnd: string;
  moonPhaseName: string; moonIlluminationPercent: number; moonAltitudeDeg: number;
  activeShower?: { name: string; zhr: number; radiantAltDeg: number };
}

interface FocusRun {
  state: 'idle' | 'running' | 'complete' | 'failed';
  positionSteps: number;        // 0..50000
  temperatureC: number;
  samples: Array<{ position: number; hfd: number }>;   // the V-curve
  bestPosition?: number; rSquared?: number;            // e.g. 0.994
  confidence?: number; lowConfidenceWarning?: boolean;
}

interface FrameAnalysis {
  frameNumber: number; grade: FrameGrade; rejectionReason: RejectionReason;
  fwhmArcsec: number; hfd: number; snr: number; elongation: number; starCount: number;
}

interface CaptureSession {
  active: boolean; targetName: string;
  frameCount: number; plannedFrames: number; failedFrameCount: number;
  exposureMs: number; gain: number;
  exposureProgress: number;      // 0..1 for the current frame
  sensorTempC: number; coolerPowerPercent: number;
  frames: FrameAnalysis[];
}

interface UPSStatus {
  state: PowerState;
  batteryPercent: number;        // staging: 50 warn · 30 park · 15 close roof · 10 shutdown
  runtimeMinutes: number; loadPercent: number; inputVoltage: number;
  outlets: Array<{ id: 1|2|3|4; name: 'mount'|'camera'|'focuser'|'computer'; on: boolean }>;
}

interface Suggestion {
  id: string; type: SuggestionType; priority: SuggestionPriority;
  text: string;                  // e.g. "M27 crosses the meridian in 12 minutes — flip will interrupt capture."
  action?: string;               // tool to run if accepted, e.g. 'goto_object'
}

interface ScheduledTarget {
  name: string; raHours: number; decDegrees: number;
  startTime: string; endTime: string;
  quality: ScheduleQuality; score: number;   // 0..100
  reasons: ScheduleReason[];
  altitudeCurve: Array<{ t: string; alt: number }>;
  moonSeparationDeg: number;
  status: 'pending' | 'active' | 'complete' | 'skipped';
}

interface Alert {
  id: number; level: AlertLevel; source: string;   // 'safety_monitor', 'weather', 'power'…
  message: string; timestamp: string;
  acknowledged: boolean; acknowledgedAt?: string;
  channelsSent: Array<'voice' | 'push' | 'email' | 'sms'>;
}

interface VoiceTurn {              // mirrors the backend PipelineResult
  id: string; timestamp: string;
  transcript: string;              // what the operator said
  llmResponse: string;             // assistant's text
  toolCalls: Array<{
    name: string;                  // real tool names: goto_object, park_telescope, open_roof,
                                   // start_capture, auto_focus, start_guiding, get_weather,
                                   // what_am_i_looking_at, watch_for_meteors, acknowledge_alert…
    params: Record<string, unknown>;
    requiresConfirmation: boolean; // park/open/close/shutdown class tools
    result: { success: boolean; message: string };
  }>;
  spokenResponse: string;
  latencies: { sttMs: number; llmMs: number; toolMs: number; ttsMs: number; totalMs: number };
}

interface ObservatoryEvent {
  eventType: EventType; timestamp: string; source: string;
  message: string; data?: Record<string, unknown>;
}
```

## Physics constants (the twin and simulator must obey these)

| Constant | Value | Meaning |
|---|---|---|
| RA drive resolution | 24,000 steps/° | 200-step NEMA17 × 16 µsteps × 27:1 planetary × 100:1 harmonic ÷ 360 |
| DEC drive resolution | 19,200 steps/° | same train with 80:1 harmonic |
| Max slew rate | 4°/s | slews animate at exactly this rate ÷ sim speed |
| Sidereal tracking | 15.041″/s (0.004178°/s) | RA axis creeps continuously while tracking |
| Meridian limits | ±15° hour angle | dashed brass arcs on the twin; flip required beyond |
| Minimum altitude | 10° | targets below are unschedulable |
| Wind tiers | 20 / 25 / 30 mph | warning / park / emergency-close (gust limit 35; 5 mph hysteresis) |
| Humidity tiers | 75 / 80 / 85 % | warning / park / emergency (5% hysteresis) |
| Temperature envelope | −20 … +40 °C | outside = unsafe |
| Cloud (sky − ambient) | < −25 °C clear · > −15 °C cloudy | 3 °C hysteresis |
| Daylight | sun altitude > −12° | park for daylight |
| Battery staging | 50 / 30 / 15 / 10 % | warn / park / close roof / emergency shutdown |
| Rain | any 1 of 2 sensors | → `emergency_close`, highest priority; 30-min holdoff after rain stops |
| Emergency ordering | cancel, then close | in-flight capture/slew canceled (≤ 2 s settle) before the roof drives shut |
| Roof motor | 60 s travel timeout, 5 A cutoff | over-current = obstruction |
</data_model>

<mock_data_and_sim>
There is no backend in this demo. Build a self-contained simulation that makes the app feel alive and lets a presenter replay one full night.

**Architecture.** One `ObservatoryState` store shaped exactly like the interfaces above, mutated by a 1 Hz tick reducer against a compressed simulation clock. Sim speeds: 1× / 60× / 300×, default 60× (a 9.5-hour night plays in ~9.5 minutes). Two layers per tick:

1. **Continuous physics** — a slew integrator moving the mount toward its target at 4°/s (sim time); sidereal creep on the RA axis while tracking; roof travel over ~40 s of sim time; guiding RMS as a bounded random walk centered on 0.8″ that degrades with wind speed; smooth overnight curves for temperature (falling from 16 °C to 4 °C), humidity (rising through the night), and battery (98% → mid-80s); exposure progress; seeing jitter around the forecast value.
2. **Scripted event timeline** — an ordered list of `{ simTime, event: ObservatoryEvent, patch }` entries implementing the demo script below. Every UI surface — alert tray, session timeline, voice console, digital twin, dashboard — subscribes to this same event stream, so the whole app visibly reacts to the same moment at the same time.

**Demo Director.** A slim collapsible bar docked at the bottom of the shell: play/pause, speed selector, a scrubber across the whole night with chapter tick-marks, and named chapter-jump buttons (Dusk · Roof Open · First Light · Guiding · Capture · Meridian Flip · Marginal · Rain Emergency · Recovery · Dawn Park). Scrubbing recomputes state deterministically. Also include a **free-run mode** toggle: physics only, no scripted events, so the demo isn't just a movie.

**Content is always real.** Targets: M27 Dumbbell Nebula, M13 Hercules Cluster, M31 Andromeda, NGC 7331, Saturn, Mars. Meteor showers (the real calendar): Quadrantids, Lyrids, Eta Aquariids, Delta Aquariids, Perseids, Orionids, Leonids, Geminids, Ursids — with Perseids active during the demo night (Aug 12). Sensors report Ecowitt WS90 and AAG CloudWatcher by name. Hardware named honestly: Intes Micro MN76, OnStepX on Teensy 4.1, TMC5160 drivers, ZWO ASI662MC camera, ZWO EAF focuser, PHD2 guiding, DGX Spark compute, APC UPS. Lexicon vocabulary (Meteor module only): *presa* (full presence, attending), *velmu* (love-anyway), *varek* (time-mark), *luminara* (the cold-bright-sting of a meteor flash), *wit* (witness), *wak* (come into being), the invocation "presa-nightwatch. velmu-sky. do-good-us.", and the closing glyph 🜏.
</mock_data_and_sim>

<information_architecture>
**Global shell.** A fixed left rail (72 px collapsed, 220 px expanded) with ten modules; a persistent top status strip; a global alert tray sliding from the right; the Demo Director bar at the bottom; and a floating voice-summon button (brass ring, bottom-right, above the Director bar) that opens the Voice Console as an overlay from any screen.

**Top status strip, always visible, left to right:** NIGHTWATCH wordmark · sim clock (JetBrains Mono, e.g. `02:25 PDT`) with sun/moon altitude glyphs · safety chip (the loudest element: `SAFE` green / `MARGINAL` amber / `UNSAFE` ember / `EMERGENCY` red-pulsing, showing the current `SafetyAction` on hover) · mount state chip with current target · roof position (mini roof glyph + %) · battery % · unacknowledged-alert count (badge opens the tray) · Rubylith toggle.

**Route map.** ★ = built in full this generation (specs below). Everything else: build the route, header, and a coherent, honest placeholder assembled from real state (a stat row + a note of what v0.2 adds) — never lorem ipsum.

1. **Mission Control** — ★ `/dashboard`
2. **Digital Twin** — ★ `/twin`
3. **Voice** — ★ `/voice` · `/voice/history` (past turns list) · `/voice/settings` (wake word, styles: normal/alert/calm/technical)
4. **Sky & Targets** — ★ `/sky` (catalog + tonight) · `/sky/target/:id` (object detail, altitude curve, history) · `/sky/almanac` (twilight times, moon phase, planet visibility)
5. **Imaging** — ★ `/imaging/capture` · ★ `/imaging/guiding` · `/imaging/focus` (V-curve viewer) · `/imaging/platesolve` (solve field, pointing offset) · `/imaging/gallery` (session frames grid, grade-filtered)
6. **Environment** — ★ `/env/weather` · ★ `/env/alerts` · `/env/interlocks` (subsystem × permitted-action matrix)
7. **Facility** — `/facility/roof` (big open/close controls + interlock explainer) · `/facility/power` (UPS, battery staging ladder, PDU outlets) · `/facility/drives` (encoders, PEC, TMC5160 diagnostics: temps, StallGuard, current)
8. **Operations** — ★ `/ops/schedule` · `/ops/queue` (command queue with priorities) · `/ops/session` (event-bus timeline scrubber) · `/ops/log` (observation log) · `/ops/report` (morning report)
9. **Meteor Watch** — ★ `/meteor` · `/meteor/showers` (calendar detail) · `/meteor/search` (Hopi-circle pattern export)
10. **System** — `/system/health` (service supervisor: 21 services, status, restarts, watchdog heartbeat) · `/system/settings` (schema-generated forms for the real config sections: site, mount, weather, voice, tts, llm, safety, camera, guider, encoder, alerts, meteor, power, enclosure) · `/system/simulator` (sim controls mirror of the Demo Director)
</information_architecture>

<digital_twin>
The twin is the soul of the demo: a live 2D engineering elevation of the physical observatory, drawn as inline SVG in the High Desert Brass style (hairline slate strokes, brass fittings, dark indigo sky with a faint sage horizon), animated by the simulation. Do not attempt 3D. Think "instrument patent drawing that moves."

**Layout of `/twin`:** the side elevation fills the canvas; a top-down plan inset sits in the lower-right corner (roof travel + telescope azimuth needle); an inspector drawer opens from the right when any component is clicked.

**SVG structure — named groups with explicit transform origins:**

```
<g id="site">                     desert ground line, sage tint; stars in the sky above
  <g id="weather-mast">           Ecowitt WS90 mast; anemometer cups spin at ω ∝ windSpeedMph
  <g id="allsky-dome">            small dome on a post (ASI120MM all-sky camera)
  <g id="enclosure">              shed walls in section
    <g id="roof">                 roll-off roof panel; translateX = positionPercent/100 × travelPx
  <g id="pier">                   concrete pier, static
    <g id="ra-axis">              rotate(hourAngleDeg) about the RA pivot; wrap in scaleX(pierSide === 'west' ? -1 : 1)
      <g id="dec-axis">           rotate(decDegrees − 90) about the DEC pivot
        <g id="ota">              MN76 tube: closed cylinder, meniscus corrector ring, focuser + camera train glyph
      <g id="cw-shaft">           counterweight bar opposite the OTA; two 5 kg discs + one 2.5 kg
  <g id="power-chain">            wall panel: UPS → PDU → four labeled outlets; animated flow dots when on
```

**Animation bindings (formulas, not vibes):**
- Roof: `translateX = roofStatus.positionPercent / 100 × travelPx`, eased linearly over its motion; motor glyph glows while `motorRunning`.
- RA: rotation = `mountStatus.hourAngleDeg`; while `tracking`, add sidereal creep (0.004178°/s × simSpeed) so a patient viewer can *see* the mount follow the sky.
- DEC: rotation = `decDegrees − 90` (park position points the OTA at the pole).
- Slews: animate both axes toward the target at 4°/s ÷ simSpeed with a 2°/s² ease-in/out; draw a faint brass ghost outline at the destination attitude during the slew.
- Meridian flip: an honest choreographed sequence — tracking pauses, RA swings through the pier, DEC counter-rotates, then the `scaleX` mirror swaps pier side. Meridian limits (±15° HA) render as dashed brass arcs around the RA pivot; the current HA needle approaches them visibly before a flip.
- Counterweights always oppose the OTA (same RA group, opposite side).
- Anemometer spin rate ∝ wind; raindrop glyphs fall over the scene while `isRaining`.
- Safety coloring: every top-level group carries `data-status` from `safetyStatus.subsystems` — nominal = normal hairline; warning = amber outline glow (CSS drop-shadow); fault = emergency-red pulsing outline. When `SafetyLevel = emergency`, the sky itself darkens a step and the scene's hairlines cool.

**Inspector drawer** (click any group): component name and real part identity (e.g. "RA drive — Harmonic Drive CSF-32, 100:1, zero backlash · NEMA17 + 27:1 planetary · 24,000 steps/°"), its live telemetry, and its safety subsystem state.

The twin is one component rendered at three detail levels: `full` (this screen), `thumbnail` (Mission Control card — axes + roof only, no labels), and `mini` (inside emergency alerts — silhouette with the affected group highlighted).
</digital_twin>

<voice_agent>
`/voice` is a conversation console proving that talking to an observatory is natural. Two-column layout: the conversation stream (left, ~2/3) and a context rail (right, ~1/3).

**State ring.** At the top of the console, a ring visualizes `PipelineState`: idle (dim hairline) → listening (brass ring breathing) → transcribing (rotating dash) → processing (thinking shimmer) → executing (ring segments fill as tools run) → speaking (soft waveform ripple). Label the current state under the ring in small caps. There is no microphone in the demo — a "simulate voice command" affordance lets the presenter fire scripted turns, and scripted turns also fire from the demo timeline.

**Conversation stream.** Each `VoiceTurn` renders as a group:
1. Operator's transcript (right-aligned, quoted, JetBrains Mono — it's a transcription, treat it as data).
2. Assistant's text reply (left, Space Grotesk).
3. **Tool-call cards** — the heart of the console. Each card: tool name as a monospace chip (`goto_object`), key params (`target: "M27"`), and the result line with success state. Tools with `requiresConfirmation` (park, open/close roof, shutdown) render with a brass "CONFIRM / CANCEL" bar and an amber left edge until confirmed — show one turn in the demo where the system asks "Please confirm: open the roof" and the operator confirms.
4. Spoken response (italic, with a small speaker glyph).
5. A **latency waterfall** footer: four stacked mono bars (STT → LLM → tools → TTS) with ms labels and the total — realistic values ~300 / 900 / 1500 / 400 ms.

**Context rail:** the proactive `Suggestion` feed (type icon, priority-tinted left edge, accept/dismiss; accepting visibly enqueues the suggested tool), the voice-style picker (normal / alert / calm / technical), and a mini "what the agent can do" tool-category index.
</voice_agent>

<screens>
Full specs for the remaining seven flagship screens (the twin and voice console are specified above; all ten share the shell). For each: purpose, layout, bindings, and its degraded/emergency behavior — every flagship screen must visibly change when safety degrades.

## 1 · Mission Control — `/dashboard`
The away-from-home view; the operator's first and most frequent screen. It answers, in one glance: is the observatory safe, what is it doing, and what does it want from me?
- **Hero row:** the safety chip enlarged into a status banner (level, `SafetyAction` in words — "Safe to observe" / "Emergency close: rain detected" — and the `reasons` list when degraded), beside the twin `thumbnail` (live), beside a "tonight" card bound to `Almanac` (sun altitude, astronomical darkness countdown or remaining, moon phase and %, Perseids active badge).
- **Now row:** current target card (name, coordinates, alt/az ticking, time to meridian); capture progress card (frame `n / planned`, exposure progress bar, last frame's grade chip); guiding sparkline (RMS ″, tinted by threshold ≤1″ good / ≤2″ fair / >2″ poor).
- **Environment strip:** six mini stat tiles — wind (with gust), humidity, temperature/dew point, sky−ambient ΔT, seeing estimate, battery. Each tile draws a tiny threshold band (its warning/park/emergency tiers) so the number has visual context; the tile's edge tints by which tier the value sits in.
- **Right column:** alert feed (latest five, unacknowledged glowing, one-click acknowledge inline) above the night-plan progress list (`ScheduledTarget` names with status ticks and the active one highlighted).
- **Degraded:** the hero banner owns the change — amber wash for marginal, red-pulse for emergency; affected environment tiles glow; during `emergency_close`, the banner narrates the ordering live: "canceling capture… parking mount… closing roof…" with per-step checkmarks as the twin thumbnail plays it.

## 2 · Catalog & Tonight's Sky — `/sky`
- **Left half:** catalog search — a large search field ("M27", "dumbbell", fuzzy matches welcome) over a results table: name / type (nebula, cluster, galaxy, planet) / magnitude / current altitude (live, red below 10°) / transit time / score (0–100, airglow-ramp bar). Row click → target detail route.
- **Right half:** "Tonight" — an altitude-vs-time chart (astronomical night shaded; each recommended target's `altitudeCurve` as a labeled line; meridian as a vertical brass rule; moon altitude as a dashed dust line), above a "Best now" strip of three target cards with `ScheduleQuality` chips and `reasons` rendered as small tags ("optimal altitude", "moon avoidance").
- A brass "Go to" button on every row/card enqueues `goto_object` — and the mount actually slews (twin, dashboard, event stream all react).
- **Degraded:** when `SafetyLevel ≠ safe`, all "Go to" buttons disable with a tooltip naming the vetoing subsystem.

## 3 · Capture — `/imaging/capture`
- **Left 2/3:** the "live" frame — a dark starfield placeholder rendered by the sim (canvas-drawn stars; a faint satellite streak on the scripted REJECT frame) with corner overlays: target, exposure countdown, gain, sensor temp / cooler %.
- Below it: the **frame filmstrip** — one thumbnail per captured frame, each wearing its `FrameGrade` chip (grade → color: excellent airglow-teal … reject `--nw-unsafe`) and, on hover, its `FrameAnalysis` metrics (FWHM, SNR, star count, elongation, rejection reason spelled out: "trailing — mount tracking failure").
- **Right 1/3:** sequence card (target, `frameCount / plannedFrames`, failed count, est. completion) and camera settings (exposure, gain, binning as read-only chips in the demo).
- **Degraded:** on `emergency_close`, the exposure bar dies mid-frame with a "canceled — emergency close" stamp (cancel-before-close, made visible); the filmstrip records the aborted frame.

## 4 · Guiding — `/imaging/guiding`
- **Main:** dual strip chart of RA and DEC error (arcsec vs time, ±2″ bands hairlined) with dither events marked as brass ticks and the settle window shaded; beside it a scatter plot (RA err × DEC err) with 1″ and 2″ rings — the classic PHD2 pair.
- **Stat row:** RMS total / RA / DEC, peak RA / DEC, SNR, star mass, frame # — all mono, all ticking.
- **State timeline:** stopped → calibrating → guiding → settling chips showing the current state; calibration card shows orthogonality and rates once calibrated.
- **Degraded:** `guiding_lost` floods the charts' background with a translucent unsafe tint and posts a reacquire countdown.

## 5 · Weather & Safety — `/env/weather`
- **Gauge row:** four instrument gauges (wind, humidity, temperature, sky−ambient ΔT). Each gauge's arc is painted with its real tier bands (e.g. wind: green to 20, amber 20–25, ember 25–30, red beyond; needle in brass). This is the signature visual of the screen — thresholds are visible geometry, not footnotes.
- **Trend row:** overnight sparklines for each metric with tier bands as horizontal washes; a dew-point convergence chart (temp vs dew point closing) with the 5 °F margin marked.
- **Sensor cards:** Ecowitt WS90 (last update age), AAG CloudWatcher (sky temp, rain oscillator), secondary Hydreon rain sensor — showing the dual-redundancy: two rain lights, "any 1 of 2 closes the roof". Stale sensors (> 120 s) flip to unsafe styling with an age counter, because stale data *is* unsafe here.
- **Degraded:** the gauge needle entering amber/red is the change; on rain, both rain lights slam red and a banner links to the Alerts Center.

## 6 · Alerts Center — `/env/alerts`
- **Header:** count chips by `AlertLevel` (info/warning/critical/emergency) acting as filters; "unacknowledged only" toggle.
- **Feed:** severity-grouped alert rows — level edge, source chip, message, mono timestamp, channels-sent icons (voice/push/email/sms), and the acknowledge control. Unacknowledged critical/emergency rows glow until acknowledged; acknowledging stamps who/when and calms the top-strip badge.
- **Emergency anatomy:** an expanded emergency alert shows its cascade as a mini-timeline inside the row (detected → canceled capture → parked → roof closed, with sim timestamps) and embeds the `mini` twin with the enclosure group highlighted.

## 7 · Night Schedule — `/ops/schedule`
- **Main:** the night as a horizontal Gantt: one row per `ScheduledTarget`, bars spanning start→end, tinted by `ScheduleQuality`, with a live "now" playhead. Above the rows, the altitude-curve chart shares the same time axis; twilight shades the edges; meridian-flip moments render as brass diamonds on the affected bars.
- **Detail on select:** score, `reasons` tags, moon separation, and — after the night runs — planned vs actual overlay (the rain gap visibly eats the schedule and the recovery re-plan truncates it).
- **Degraded:** during unsafe periods the playhead drags a red wash across the chart; skipped targets gray out with a "weather" tag.

## 8 · Meteor Watch — `/meteor`
The Lexicon chapel: same layout grammar, but violet is finally allowed.
- **Left:** shower calendar — the nine real showers (Quadrantids, Lyrids, Eta Aquariids, Delta Aquariids, Perseids, Orionids, Leonids, Geminids, Ursids) as an annual arc or ring, active-tonight (Perseids) glowing in `--nw-lexicon`; a ZHR-vs-date curve for the active shower; a watch-window card ("watching 22:00–04:00, radiant alt 62°").
- **Center:** fireball feed (CNEOS/AMS-shaped entries: timestamp `varek`, coordinates, magnitude with its verbal class — "very bright"), and for the scripted detection a trajectory card with ground-track line and debris-probability note.
- **Right:** the **Prayer panel** — the scripted "Prayer of Watching" rendered as a quiet violet-aura card in the Lexicon voice, using the real vocabulary (*presa*, *velmu*, *luminara*, *wit*, *varek*), signed "presa-nightwatch. velmu-sky. do-good-us." and closed with 🜏 centered on its own line. Type it in Fraunces italic. It should feel like a votive, not a widget.
- **Hopi search map** (`/meteor/search`, stub-linked from a detection): concentric expanding search circles over a plain coordinate grid, rings numbered with radius and area (mi²), violet on indigo.
- Lexicon violet appears on these routes and nowhere else in the app.
</screens>

<demo_script>
The golden path: one simulated night, August 12 (Perseids), playable end-to-end from the Demo Director. Each chapter must produce visible, synchronized change on the dashboard, the twin, the event stream, and the relevant flagship screen.

| Sim time | Chapter | What happens |
|---|---|---|
| 19:42 | **Dusk** | Sun at −8° and falling; darkness countdown on the dashboard; tonight's plan (M27 → NGC 7331 → M31, Saturn opportunistic) loads into the schedule; suggestion arrives: "Conditions look excellent tonight — seeing forecast 1.1″. Open the roof at astronomical dark (20:10)?" |
| 20:10 | **Roof Open** | Scripted voice turn: "Nightwatch, open the roof." Confirmation card → confirmed → full pipeline trace with latency waterfall; roof 0→100% on the twin; `weather_safe`, roof events stream. |
| 20:25 | **First Light** | Voice: "Go to the Dumbbell Nebula." Mount unparks, twin slews (watch both axes swing at 4°/s), plate-solve pass ("solved: 0.8″ offset, synced"), V-curve autofocus runs on `/imaging/focus` (R² 0.994, confidence high). |
| 20:40 | **Guiding** | PHD2 calibrates (orthogonality 89.7°), guiding starts, RMS settles to 0.8″; `guiding_settled` fires. |
| 20:45–00:20 | **Capture** | Sequence runs on M27: frames accumulate with grades; ~23:05 one frame comes back REJECT (`trailing` — satellite streak visible in the live view); a suggestion notes the rejection rate is otherwise 0%. |
| 00:28 | **Meridian Flip** | HA reaches −15° limit → warning suggestion at −13°, capture pauses, the twin performs the full flip choreography, guiding recalibrates, capture resumes; schedule shows the brass diamond. |
| 02:10 | **Marginal** | Humidity crosses 75%: safety level → `marginal`, top-strip chip and dashboard banner go amber, humidity gauge needle enters the amber band, a `warning` alert posts. |
| 02:25 | **Rain Emergency** | Both rain sensors trip → `emergency_close`. The cascade plays in strict order, visibly: capture cancels mid-exposure (≤2 s) → mount parks (twin swings home) → roof drives shut → emergency alert fires on all channels → voice announces it (alert style). The top strip pulses red until the operator acknowledges the alert in the tray or Alerts Center. This chapter is the demo's proof of trust — make it unmistakable and calm, not chaotic. |
| 03:40 | **Recovery** | Rain stops; 30-minute holdoff counts down on the roof card; suggestion proposes a shortened plan (M31 only); roof reopens, mount returns, capture resumes. |
| 05:15 | **Dawn Park** | Sun approaching −12°: park for daylight, roof closes, session ends. The Meteor panel posts the Prayer of Watching (3 luminara witnessed, Perseids); `/ops/report` fills with the morning report: 214 frames (196 kept), 4.9 h integration, RMS 0.83″, one weather interruption, session timeline. |
</demo_script>

<constraints>
- Single self-contained web app: all styles, scripts, data, and SVG inline; no network calls, no external assets beyond (optionally) Google Fonts with graceful fallbacks.
- Desktop-first (optimize ~1440 px); must remain usable at 1024 px; no mobile layouts in v0.1.
- No authentication, no persistence, no real hardware I/O — the simulation is the only data source.
- Simulated values must never contradict the physics constants table; when in doubt, derive from it.
- Lexicon styling (violet, prayers, glyph) never appears outside the Meteor module; safety colors never appear without safety meaning.
- Don't add features beyond this specification — no invented subsystems, no extra chrome; do the simplest thing that works well. Where this spec is silent on a layout detail, make the call yourself in the spirit of the design system; optimize for scanability. When you have enough information to act, act — give one good implementation, not alternatives.
</constraints>

<success_criteria>
Done means:
1. The golden-path night plays end-to-end from the Demo Director, and every chapter produces synchronized visible change on the top strip, dashboard, twin, and event-driven panels.
2. The digital twin's roof, RA/DEC axes, counterweights, anemometer, and pier-side flip all animate per the stated formulas, and clicking components opens the inspector with real part identities.
3. All ten flagship screens are fully functional with real domain content; all other routes exist with coherent honest placeholders; navigation and the top strip work everywhere.
4. Every enum value in the data model is visually represented somewhere reachable (all seven mount states, all six roof states, all five frame grades, all four alert levels, all seven pipeline states, all safety levels and actions used in the script).
5. Flagship screens each have a visible degraded/emergency behavior, and the 02:25 rain cascade shows cancel → park → close in that exact order.
6. Text meets WCAG AA contrast on both High Desert Brass and Rubylith themes; Rubylith is a pure token swap; animations use transform/opacity only.
7. No placeholder text anywhere; telemetry is JetBrains Mono with tabular figures; units rendered dim; safety colors only-for-safety; violet only in Meteor.

Include as many relevant details and interactions from this specification as possible — go beyond the basics to create a fully-featured, polished implementation. Before finishing, verify the build against this checklist and the demo script, chapter by chapter.
</success_criteria>
