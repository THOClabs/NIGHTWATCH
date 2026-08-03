const PROMPTS = [
  "Slew to M31",
  "What's the weather like?",
  "Schedule tonight",
  "Go to the nebula",
  "Slew to Andromeda",
  "Nightwatch, watch for meteors",
  "Park the telescope",
];

const feed = document.getElementById("chat-feed");
const form = document.getElementById("command-form");
const input = document.getElementById("command-input");
const chips = document.getElementById("prompt-chips");

function fmtMinutes(mins) {
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  if (h <= 0) return `${m}m`;
  return `${h}h ${m}m`;
}

function addMessage({ role, text, meta, actions }) {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  el.appendChild(bubble);

  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.textContent = meta;
    el.appendChild(m);
  }

  if (actions?.length) {
    const row = document.createElement("div");
    row.className = "actions";
    for (const action of actions) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = action.label;
      btn.addEventListener("click", () =>
        sendCommand(action.command || action.label)
      );
      row.appendChild(btn);
    }
    el.appendChild(row);
  }

  feed.appendChild(el);
  feed.scrollTop = feed.scrollHeight;
}

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

async function sendCommand(text) {
  const value = text.trim();
  if (!value) return;
  addMessage({ role: "user", text: value });
  input.value = "";
  try {
    const data = await api("/api/command", {
      method: "POST",
      body: JSON.stringify({ text: value }),
    });
    addMessage({
      role: "assistant",
      text: data.response,
      meta: `intent ${data.intent} · normalized “${data.normalized}”`,
      actions: data.actions,
    });
    if (data.wake_status) {
      document.getElementById("wake-count").textContent =
        data.wake_status.total_detections ?? 0;
    }
    if (data.vocab_stats) {
      const terms =
        data.vocab_stats.total_terms ??
        data.vocab_stats.terms_count ??
        "—";
      document.getElementById("vocab-count").textContent = terms;
    }
    // Refresh schedule / favorites lightly after observing commands
    if (data.intent === "schedule" || data.intent === "slew") {
      loadSchedule();
    }
  } catch (err) {
    addMessage({
      role: "assistant",
      text: `Console error: ${err.message}`,
      meta: "error",
    });
  }
}

function renderTargets(evaluations) {
  const board = document.getElementById("target-board");
  board.innerHTML = "";
  for (const item of evaluations) {
    const t = item.target;
    const scores = item.condition_scores || {};
    const quality = String(
      item.evaluation?.quality || item.evaluation?.rating || "n/a"
    ).toLowerCase();
    const card = document.createElement("article");
    card.className = "target-card";
    card.tabIndex = 0;
    card.innerHTML = `
      <div class="id">${t.id}</div>
      <h3>${t.name}</h3>
      <p class="type">${t.object_type} · mag ${t.magnitude}</p>
      <div class="score-row"></div>
      <div class="quality ${quality}">${quality}</div>
    `;
    const scoreRow = card.querySelector(".score-row");
    const entries = Object.entries(scores).slice(0, 4);
    for (const [key, val] of entries) {
      const pct = Math.max(0, Math.min(100, Number(val) * 100));
      const row = document.createElement("div");
      row.className = "bar-wrap";
      row.innerHTML = `
        <span>${key.replace(/_score$/, "")}</span>
        <div class="bar"><i style="width:0%"></i></div>
        <span>${pct.toFixed(0)}</span>
      `;
      scoreRow.appendChild(row);
      requestAnimationFrame(() => {
        row.querySelector("i").style.width = `${pct}%`;
      });
    }
    card.addEventListener("click", () =>
      sendCommand(`Slew to ${t.name}`)
    );
    board.appendChild(card);
  }
}

async function loadSchedule() {
  const data = await api("/api/schedule");
  document.getElementById("schedule-narration").textContent = data.narration;
  document.getElementById("schedule-meta").innerHTML = `
    <span>${data.target_count} targets scheduled</span>
    <span>${fmtMinutes(data.total_minutes)} observing window</span>
  `;
  renderTargets(data.evaluations || []);
}

async function loadSky() {
  const data = await api("/api/sky");
  document.getElementById("sky-quote").textContent = data.description;
  const row = document.getElementById("visible-row");
  row.innerHTML = "";
  for (const obj of data.visible || []) {
    const span = document.createElement("span");
    span.textContent = `${obj.name} · ${obj.constellation || obj.object_type}`;
    row.appendChild(span);
  }
}

async function loadHealth() {
  const data = await api("/api/health");
  const summary = data.summary || {};
  document.getElementById("health-summary").innerHTML = `
    <span>Overall <strong>${summary.overall_status || "ready"}</strong></span>
    <span>Ready <strong>${summary.services_ready ?? "—"}</strong></span>
    <span>Commands <strong>${data.commands_processed ?? 0}</strong></span>
    <span>Uptime <strong>${Math.round(data.uptime_seconds || 0)}s</strong></span>
  `;
  const grid = document.getElementById("health-grid");
  grid.innerHTML = "";
  for (const [name, info] of Object.entries(data.health || {})) {
    const item = document.createElement("div");
    item.className = "health-item";
    const status = info.status || "unknown";
    const cls =
      status === "ready" ? "" : status.includes("error") ? "error" : "warn";
    item.innerHTML = `<span class="dot ${cls}"></span><span>${name}</span>`;
    grid.appendChild(item);
  }
}

function showIdentify(title, lines) {
  const box = document.getElementById("identify-result");
  box.hidden = false;
  box.textContent = [`▸ ${title}`, ...lines].join("\n");
}

async function bootstrap() {
  PROMPTS.forEach((text) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = text;
    btn.addEventListener("click", () => sendCommand(text));
    chips.appendChild(btn);
  });

  addMessage({
    role: "assistant",
    text: "NIGHTWATCH online. Local AI services are warm — issue a voice-style command whenever you're ready.",
    meta: "system · simulator mode",
  });

  const data = await api("/api/bootstrap");
  document.getElementById("site-line").textContent =
    `${data.site.name} · ${data.site.latitude_deg.toFixed(1)}°N ${Math.abs(data.site.longitude_deg).toFixed(1)}°W`;
  document.getElementById("wake-word").textContent = data.wake_word || "nightwatch";
  document.getElementById("hero-meta").textContent =
    `${data.summary.services_ready} AI services ready · v${data.version} · ${data.mode}`;

  await Promise.all([loadSchedule(), loadSky(), loadHealth()]);
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendCommand(input.value);
});

document.getElementById("btn-sky-brief").addEventListener("click", async () => {
  await loadSky();
  document.getElementById("sky").scrollIntoView({ behavior: "smooth" });
});

document.getElementById("coord-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = await api("/api/identify", {
    method: "POST",
    body: JSON.stringify({
      ra_hours: Number(fd.get("ra")),
      dec_degrees: Number(fd.get("dec")),
    }),
  });
  const matches = data.matches || [];
  if (!matches.length) {
    showIdentify("Coordinate search", ["No matches within search radius."]);
    return;
  }
  const best = matches[0];
  showIdentify("Coordinate match", [
    `${best.object_id} — ${best.object_name}`,
    `confidence ${best.confidence_level} · via ${best.method}`,
  ]);
});

document.getElementById("catalog-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const data = await api("/api/identify", {
    method: "POST",
    body: JSON.stringify({ object_id: fd.get("object_id") }),
  });
  const m = data.match;
  if (!m) {
    showIdentify("Catalog lookup", ["Object not found in offline catalog."]);
    return;
  }
  showIdentify("Catalog object", [
    `${m.object_id} — ${m.object_name}`,
    `type ${m.object_type} · ${m.constellation}`,
    `mag ${m.magnitude} · size ${m.size_arcmin}′`,
  ]);
});

document.getElementById("pattern-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const stars = String(fd.get("stars"))
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const data = await api("/api/identify", {
    method: "POST",
    body: JSON.stringify({ stars }),
  });
  const matches = data.matches || [];
  if (!matches.length) {
    showIdentify("Asterism match", ["No pattern matches for those stars."]);
    return;
  }
  showIdentify(
    "Asterism match",
    matches.slice(0, 3).map(
      (m) =>
        `${m.pattern_name}: ${m.description} (${Math.round((m.confidence || 0) * 100)}%)`
    )
  );
});

function tickClock() {
  const el = document.getElementById("footer-clock");
  const now = new Date();
  el.textContent = now.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}
tickClock();
setInterval(tickClock, 1000);

/* -------- Animated starfield -------- */
(function starfield() {
  const canvas = document.getElementById("sky-canvas");
  const ctx = canvas.getContext("2d");
  let stars = [];
  let w = 0;
  let h = 0;
  let t = 0;

  function resize() {
    w = canvas.width = window.innerWidth * devicePixelRatio;
    h = canvas.height = window.innerHeight * devicePixelRatio;
    canvas.style.width = `${window.innerWidth}px`;
    canvas.style.height = `${window.innerHeight}px`;
    const count = Math.floor((window.innerWidth * window.innerHeight) / 4500);
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: (Math.random() * 1.4 + 0.3) * devicePixelRatio,
      a: Math.random(),
      s: Math.random() * 0.6 + 0.2,
      tw: Math.random() * Math.PI * 2,
    }));
  }

  function frame() {
    t += 0.016;
    ctx.clearRect(0, 0, w, h);

    // subtle milky band
    const grad = ctx.createLinearGradient(0, h * 0.2, w, h * 0.85);
    grad.addColorStop(0, "rgba(90, 130, 170, 0)");
    grad.addColorStop(0.45, "rgba(90, 130, 170, 0.05)");
    grad.addColorStop(1, "rgba(90, 130, 170, 0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    for (const star of stars) {
      star.x += star.s * 0.08;
      if (star.x > w) star.x = 0;
      const twinkle = 0.45 + 0.55 * Math.sin(t * 1.4 + star.tw);
      ctx.beginPath();
      ctx.fillStyle = `rgba(232, 238, 248, ${star.a * twinkle})`;
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);
})();

bootstrap().catch((err) => {
  document.getElementById("hero-meta").textContent =
    `Failed to start demo: ${err.message}`;
  addMessage({
    role: "assistant",
    text: `Bootstrap failed: ${err.message}`,
    meta: "error",
  });
});
