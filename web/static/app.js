// Astroflo web control — vanilla JS, no external deps (works offline on the hotspot)
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
let state = null;
let activeTab = "live";

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2500);
}

async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: {} };
  if (opts.body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.body); }
  const r = await fetch(path, init);
  const data = r.headers.get("content-type")?.includes("json") ? await r.json() : null;
  if (!r.ok) {
    const d = data?.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => `${e.loc?.join(".")}: ${e.msg}`).join("; ") : r.statusText);
  }
  return data;
}
const run = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message); } };

// ---------- formatting ----------
function hms(raDeg) {
  const h = (raDeg / 15 + 24) % 24, hh = Math.floor(h), m = (h - hh) * 60, mm = Math.floor(m), ss = (m - mm) * 60;
  return `${hh}h ${String(mm).padStart(2, "0")}m ${ss.toFixed(1).padStart(4, "0")}s`;
}
function dms(dec) {
  const s = dec < 0 ? "-" : "+", a = Math.abs(dec), d = Math.floor(a), m = (a - d) * 60, mm = Math.floor(m), ss = (m - mm) * 60;
  return `${s}${d}° ${String(mm).padStart(2, "0")}' ${ss.toFixed(0).padStart(2, "0")}"`;
}
const num = (v, d = 2) => (v === null || v === undefined ? "—" : Number(v).toFixed(d));
function dl(el, rows) {
  el.innerHTML = rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
}

// ---------- tabs ----------
$$("#tabs button").forEach((b) => b.addEventListener("click", () => {
  activeTab = b.dataset.tab;
  $$("#tabs button").forEach((x) => x.classList.toggle("active", x === b));
  $$(".tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${activeTab}`));
  try { localStorage.setItem("tab", activeTab); } catch {}
  onTab(activeTab);
}));
function onTab(tab) {
  if (tab === "targets") loadTargets();
  if (tab === "captures") loadCaptures();
  if (tab === "settings") loadSettings();
  if (tab === "imaging") loadImaging();
  if (tab === "live") refreshStarfield();
}

// night mode
function setNight(on) { document.documentElement.dataset.night = on ? "1" : "0"; try { localStorage.setItem("night", on ? "1" : "0"); } catch {} }
$("#night").addEventListener("click", () => setNight(document.documentElement.dataset.night !== "1"));

// ---------- live state over websocket (falls back to polling) ----------
let wsOpen = false;
function setConn(on) { $("#conn").textContent = on ? "online" : "offline"; $("#conn").classList.toggle("ok", on); }
function connectWS() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/state`);
  ws.onopen = () => { wsOpen = true; setConn(true); };
  ws.onmessage = (e) => { state = JSON.parse(e.data); render(); };
  ws.onclose = () => { wsOpen = false; setTimeout(connectWS, 5000); };
}
// Polling fallback whenever the websocket is down
setInterval(async () => {
  if (wsOpen || document.hidden) return;
  try { state = await api("/api/state"); setConn(true); render(); } catch { setConn(false); }
}, 1000);

let finderInit = false;
function render() {
  const s = state; if (!s) return;
  const p = s.position;
  dl($("#pos"), p ? [
    ["RA", hms(p.ra)], ["Dec", dms(p.dec)], ["Alt / Az", `${num(p.alt, 1)}° / ${num(p.az, 1)}°`], ["Roll", `${num(p.roll, 1)}°`],
    ["Solve age", `${num(s.last_solved_age, 1)} s`],
  ] : [["Status", "Unsolved"], ["Solve age", `${num(s.last_solved_age, 1)} s`]]);
  const t = s.target;
  dl($("#tgt"), t ? [
    ["Name", t.name], ["RA / Dec", `${hms(t.ra)} ${dms(t.dec)}`], ["Alt / Az", `${num(t.alt, 1)}° / ${num(t.az, 1)}°`],
    ["Offset", t.distance_deg !== undefined ? `N ${num(t.north_deg)}° · E ${num(t.east_deg)}°` : "—"],
  ] : [["Target", "None"]]);
  if (t && t.distance_deg !== undefined) {
    const ang = Math.atan2(t.east_deg, t.north_deg) * 180 / Math.PI;
    $("#arrow").style.transform = `rotate(${ang - 90}deg)`;
    $("#arrow-wrap").style.display = "flex";
    $("#arrow-dist").textContent = `${num(t.distance_deg)}° away`;
  } else $("#arrow-wrap").style.display = "none";

  const fb = s.feedback, fbEl = $("#feedback");
  const warn = fb && fb.id !== "ok";
  fbEl.hidden = !warn;
  if (warn) { fbEl.textContent = fb.message; fbEl.className = `banner ${fb.severity === "error" ? "error" : "warning"}`; }

  const f = s.focus;
  $("#focus").textContent = f ? `FWHM ${num(f.fwhm)} px · best ${num(f.min_fwhm)} px` : "—";
  drawSpark($("#fwhm"), f?.history || []);

  if (!finderInit && s.finder_camera) {
    finderInit = true;
    $("#finder-exp").value = (s.finder_camera.exposure_us / 1000).toFixed(1);
    $("#finder-gain").value = s.finder_camera.gain;
  }
  renderImagingStatus(s.imaging_camera);
  if (s.target_pixel && !alignPx) $("#align-px").textContent = `row ${s.target_pixel[0]}, col ${s.target_pixel[1]}`;
}

function drawSpark(c, v) {
  const g = c.getContext("2d"); g.clearRect(0, 0, c.width, c.height);
  if (v.length < 2) return;
  const mn = Math.min(...v), mx = Math.max(...v), r = mx - mn || 1;
  g.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--accent"); g.lineWidth = 2; g.beginPath();
  v.forEach((y, i) => { const X = i / (v.length - 1) * c.width, Y = c.height - 4 - (y - mn) / r * (c.height - 8); i ? g.lineTo(X, Y) : g.moveTo(X, Y); });
  g.stroke();
}

// ---------- image polling (lighter than MJPEG on the Pi) ----------
function pollImg(img, url, active) {
  const tick = () => {
    if (!active() || document.hidden) return setTimeout(tick, 500);
    const next = new Image();
    next.onload = () => { img.src = next.src; setTimeout(tick, 700); };
    next.onerror = () => setTimeout(tick, 1500);
    next.src = `${url()}${url().includes("?") ? "&" : "?"}t=${Date.now()}`;
  };
  tick();
}
pollImg($("#finder-img"), () => `/api/finder/frame.jpg?overlay=${$("#finder-overlay").checked ? 1 : 0}`, () => activeTab === "live");
pollImg($("#align-img"), () => `/api/finder/frame.jpg?overlay=1`, () => activeTab === "align");
pollImg($("#img-frame"), () => `/api/imaging/frame.jpg`, () => activeTab === "imaging" && state?.imaging_camera?.connected);

function refreshStarfield() { $("#starfield").src = `/api/starfield.png?t=${Date.now()}`; }
$("#starfield").addEventListener("error", () => { $("#starfield").closest(".card").style.display = "none"; });
$("#starfield").addEventListener("load", () => { $("#starfield").closest(".card").style.display = ""; });
$("#starfield-refresh").addEventListener("click", refreshStarfield);

// ---------- finder camera ----------
$("#finder-capture").addEventListener("click", run(async () => { const m = await api("/api/finder/capture", { method: "POST" }); toast(`Saved ${m.id}`); }));
$("#finder-apply").addEventListener("click", run(async () => {
  await api("/api/finder/camera", { method: "POST", body: { exposure_us: Math.round(+$("#finder-exp").value * 1000), gain: +$("#finder-gain").value } });
  toast("Finder camera updated");
}));

// ---------- targets ----------
let tTimer;
async function loadTargets() {
  const type = $("#t-type").value, mag = $("#t-mag").value, q = encodeURIComponent($("#t-q").value);
  $("#t-mag").disabled = type === "solar";
  $("#t-list").innerHTML = `<li class="muted">Loading…</li>`;
  try {
    const r = await api(`/api/targets?type=${type}&mag=${mag}&q=${q}`);
    $("#t-list").innerHTML = r.items.length ? "" : `<li class="muted">No visible targets</li>`;
    for (const t of r.items) {
      const li = document.createElement("li");
      li.innerHTML = `<span>${t.name}</span><span class="muted">mag ${num(t.mag, 1)} · ${hms(t.ra)} ${dms(t.dec)}</span>`;
      li.addEventListener("click", run(async () => {
        await api("/api/target", { method: "POST", body: { name: t.name, ra: t.ra, dec: t.dec } });
        toast(`Target: ${t.name}`);
      }));
      $("#t-list").appendChild(li);
    }
  } catch (e) { $("#t-list").innerHTML = `<li class="error">${e.message}</li>`; }
}
["#t-type", "#t-mag"].forEach((s) => $(s).addEventListener("change", loadTargets));
$("#t-q").addEventListener("input", () => { clearTimeout(tTimer); tTimer = setTimeout(loadTargets, 300); });
$("#t-set").addEventListener("click", run(async () => {
  const t = await api("/api/target", { method: "POST", body: { ra: +$("#t-ra").value, dec: +$("#t-dec").value, name: $("#t-name").value || null } });
  toast(`Target: ${t.name}`);
}));
$("#t-clear").addEventListener("click", run(async () => { await api("/api/target", { method: "DELETE" }); toast("Target cleared"); }));

// ---------- imaging camera ----------
async function loadImaging() {
  const r = await api("/api/imaging").catch(() => null); if (!r) return;
  $("#img-exp").value = r.settings.exposure_s; $("#img-gain").value = r.settings.gain; $("#img-bin").value = r.settings.binning;
  renderImagingStatus(r.status);
}
function renderImagingStatus(st) {
  if (!st) return;
  const pill = $("#img-state");
  pill.textContent = st.exposing ? `exposing ${st.frame}${st.frames ? "/" + st.frames : ""}` : st.connected ? "connected" : "disconnected";
  pill.classList.toggle("ok", st.connected);
  const i = st.info || {};
  $("#img-info").textContent = st.connected ? [i.name || i.backend, i.width && `${i.width}×${i.height}`, i.temperature !== undefined && `${num(i.temperature, 1)}°C`].filter(Boolean).join(" · ") : "";
  $("#img-error").textContent = st.error || "";
  $("#img-progress").value = st.progress ?? 0;
  $("#img-expose").disabled = $("#img-loop").disabled = !st.connected || st.exposing;
  $("#img-abort").disabled = !st.exposing;
}
const exposeBody = (loop) => ({ exposure_s: +$("#img-exp").value, gain: +$("#img-gain").value, binning: +$("#img-bin").value,
  count: +$("#img-count").value, loop, save: loop ? false : $("#img-save").checked });
$("#img-connect").addEventListener("click", run(async () => { renderImagingStatus(await api("/api/imaging/connect", { method: "POST" })); toast("Camera connected"); }));
$("#img-disconnect").addEventListener("click", run(async () => renderImagingStatus(await api("/api/imaging/disconnect", { method: "POST" }))));
$("#img-expose").addEventListener("click", run(async () => renderImagingStatus(await api("/api/imaging/expose", { method: "POST", body: exposeBody(false) }))));
$("#img-loop").addEventListener("click", run(async () => renderImagingStatus(await api("/api/imaging/expose", { method: "POST", body: exposeBody(true) }))));
$("#img-abort").addEventListener("click", run(async () => renderImagingStatus(await api("/api/imaging/abort", { method: "POST" }))));

// ---------- captures ----------
let current = null;
async function loadCaptures() {
  const src = $("#c-source").value;
  const r = await api(`/api/captures${src ? "?source=" + src : ""}`).catch((e) => (toast(e.message), null)); if (!r) return;
  $("#c-info").textContent = `${r.items.length} shown · keeping newest ${r.max_kept}`;
  $("#c-grid").innerHTML = "";
  for (const c of r.items) {
    const f = document.createElement("figure");
    f.innerHTML = `<img loading="lazy" src="/api/captures/${c.id}/image.jpg" alt=""><figcaption>${c.source === "imaging" ? "🔭" : "🎯"} ${new Date(c.timestamp * 1000).toLocaleTimeString()} · ${num(c.exposure_s, 2)}s${c.target ? " · " + c.target : ""}</figcaption>`;
    f.addEventListener("click", () => openCapture(c));
    $("#c-grid").appendChild(f);
  }
}
function openCapture(c) {
  current = c;
  $("#c-full").src = `/api/captures/${c.id}/image.jpg`;
  $("#c-meta").textContent = JSON.stringify(c, null, 2);
  $("#c-dl").href = `/api/captures/${c.id}/image.jpg?download=1`;
  $("#c-fits").href = `/api/captures/${c.id}/image.fits`;
  $("#c-fits").style.display = c.fits ? "" : "none";
  $("#c-dialog").showModal();
}
$("#c-close").addEventListener("click", () => $("#c-dialog").close());
$("#c-del").addEventListener("click", run(async () => {
  if (!current || !confirm("Delete this capture?")) return;
  await api(`/api/captures/${current.id}`, { method: "DELETE" }); $("#c-dialog").close(); loadCaptures();
}));
$("#c-source").addEventListener("change", loadCaptures);
$("#c-refresh").addEventListener("click", loadCaptures);

// ---------- alignment ----------
let alignPx = null;
$("#align-img").addEventListener("click", (e) => {
  const img = e.currentTarget, rect = img.getBoundingClientRect();
  const shape = state?.finder_camera?.shape; if (!shape) return;
  // image is object-fit: contain -> compute displayed area
  const scale = Math.min(rect.width / shape[1], rect.height / shape[0]);
  const ox = (rect.width - shape[1] * scale) / 2, oy = (rect.height - shape[0] * scale) / 2;
  const col = Math.round((e.clientX - rect.left - ox) / scale), row = Math.round((e.clientY - rect.top - oy) / scale);
  if (row < 0 || col < 0 || row >= shape[0] || col >= shape[1]) return;
  alignPx = [row, col]; $("#align-px").textContent = `row ${row}, col ${col} (unsaved)`;
});
$$("[data-nudge]").forEach((b) => b.addEventListener("click", () => {
  const [dr, dc] = b.dataset.nudge.split(",").map(Number);
  alignPx = alignPx || state?.target_pixel || null; if (!alignPx) return;
  alignPx = [alignPx[0] + dr, alignPx[1] + dc]; $("#align-px").textContent = `row ${alignPx[0]}, col ${alignPx[1]} (unsaved)`;
}));
$("#align-save").addEventListener("click", run(async () => {
  if (!alignPx) return toast("Tap the image first");
  await api("/api/alignment", { method: "POST", body: { row: alignPx[0], col: alignPx[1] } });
  alignPx = null; toast("Alignment saved");
}));

// ---------- settings (form generated from the server's JSON schema) ----------
let schema = null, saved = null;
const resolve = (p) => (p.$ref ? schema.$defs[p.$ref.split("/").pop()] : p);
const title = (k) => k.replace(/_/g, " ");
async function loadSettings() {
  try {
    [schema, saved] = await Promise.all([api("/api/settings/schema"), api("/api/settings")]);
    buildForm(saved);
  } catch (e) { toast(e.message); }
  loadDisplay();
}
function buildForm(values) {
  const form = $("#settings-form"); form.innerHTML = "";
  for (const [group, gp] of Object.entries(schema.properties)) {
    if (group === "display") continue; // handled live above
    const def = resolve(gp), fs = document.createElement("fieldset");
    fs.innerHTML = `<legend>${title(group)}</legend>`;
    for (const [key, p] of Object.entries(def.properties)) {
      const v = values[group][key], id = `s-${group}-${key}`, lab = document.createElement("label");
      let input;
      if (p.enum) {
        input = document.createElement("select");
        input.innerHTML = p.enum.map((o) => `<option ${o === v ? "selected" : ""}>${o}</option>`).join("");
      } else if (p.type === "boolean") {
        input = document.createElement("input"); input.type = "checkbox"; input.checked = !!v;
      } else {
        input = document.createElement("input");
        input.type = p.type === "string" ? "text" : "number";
        if (p.type !== "string") {
          input.step = p.type === "integer" ? "1" : "any";
          if (p.minimum !== undefined) input.min = p.minimum; if (p.maximum !== undefined) input.max = p.maximum;
        }
        input.value = v;
      }
      input.id = id; input.dataset.group = group; input.dataset.key = key; input.dataset.type = p.type || "string";
      lab.textContent = title(key); lab.appendChild(input); fs.appendChild(lab);
    }
    form.appendChild(fs);
  }
}
function collect() {
  const out = {};
  $$("#settings-form [data-group]").forEach((el) => {
    const { group, key, type } = el.dataset;
    let v = el.type === "checkbox" ? el.checked : el.value;
    if (type === "number") v = parseFloat(v); else if (type === "integer") v = parseInt(v, 10);
    if (v !== saved[group][key]) (out[group] ||= {})[key] = v;
  });
  return out;
}
$("#s-save").addEventListener("click", run(async () => {
  const diff = collect();
  if (!Object.keys(diff).length) return toast("No changes");
  saved = await api("/api/settings", { method: "PUT", body: diff });
  buildForm(saved); finderInit = false;
  $("#s-msg").textContent = `Saved ${new Date().toLocaleTimeString()}` + (diff.web || diff.integrations?.stellarium_port ? " · restart app to apply web/Stellarium port" : "");
}));
$("#s-revert").addEventListener("click", () => saved && buildForm(saved));
$$("[data-sys]").forEach((b) => b.addEventListener("click", run(async () => {
  if (!confirm(`${b.textContent}?`)) return;
  await api(`/api/system/${b.dataset.sys}`, { method: "POST" }); toast(`${b.textContent}…`);
})));

// ---------- Pi display ----------
async function loadDisplay() {
  try {
    const d = await api("/api/display");
    $("#d-enabled").checked = d.enabled; $("#d-bright").value = d.brightness;
    $("#d-screen").innerHTML = d.screens.map((s) => `<option ${s === d.screen ? "selected" : ""}>${s}</option>`).join("");
  } catch (e) { $("#d-enabled").disabled = $("#d-bright").disabled = $("#d-screen").disabled = true; }
}
const putDisplay = run(async (body) => { await api("/api/display", { method: "PUT", body }); });
$("#d-enabled").addEventListener("change", (e) => putDisplay({ enabled: e.target.checked }));
$("#d-bright").addEventListener("change", (e) => putDisplay({ brightness: +e.target.value }));
$("#d-screen").addEventListener("change", (e) => putDisplay({ screen: e.target.value }));

// ---------- boot ----------
try { setNight(localStorage.getItem("night") === "1"); const t = localStorage.getItem("tab"); if (t) $(`#tabs [data-tab="${t}"]`)?.click(); } catch {}
connectWS();
onTab(activeTab);
