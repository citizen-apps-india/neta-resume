"use strict";

const state = {
  sources: [],
  activity: { runs: [], requests: [] },
  selected: null,
  detail: null,
  history: "runs",
  toastTimer: null,
};

const elements = {
  sourceList: document.querySelector("#source-list"),
  search: document.querySelector("#source-search"),
  tape: document.querySelector("#tape-track"),
  tapeCaption: document.querySelector("#schedule-caption"),
  executionJournal: document.querySelector("#execution-journal"),
  drawer: document.querySelector("#source-drawer"),
  scrim: document.querySelector("#drawer-scrim"),
  toast: document.querySelector("#toast"),
};

function csrfToken() {
  const cookie = document.cookie.split("; ").find((item) => item.startsWith("neta_admin_csrf="));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers["X-CSRF-Token"] = csrfToken();
  if (options.body) headers["Content-Type"] = "application/json";
  const response = await fetch(`/admin/api${path}`, { credentials: "same-origin", ...options, method, headers });
  if (response.status === 401) {
    window.location.assign("/admin/login");
    throw new Error("Admin session expired");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function formatCadence(seconds) {
  if (seconds == null) return "Manual / event";
  if (seconds % 86400 === 0) return `Every ${seconds / 86400}d`;
  if (seconds % 3600 === 0) return `Every ${seconds / 3600}h`;
  if (seconds % 60 === 0) return `Every ${seconds / 60}m`;
  return `Every ${seconds}s`;
}

function formatTime(value, relative = false) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "Unknown";
  if (relative) {
    const minutes = Math.round((date.valueOf() - Date.now()) / 60000);
    if (Math.abs(minutes) < 1) return "Now";
    if (minutes > 0 && minutes < 60) return `in ${minutes}m`;
    if (minutes > 0 && minutes < 1440) return `in ${Math.round(minutes / 60)}h`;
    if (minutes < 0 && minutes > -60) return `${Math.abs(minutes)}m ago`;
    if (minutes < 0 && minutes > -1440) return `${Math.round(Math.abs(minutes) / 60)}h ago`;
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function sourceCondition(source) {
  if (!source.registered) return { label: "Not registered", className: "attention" };
  if (source.quarantined_at) return { label: "Quarantined", className: "attention" };
  if (!source.enabled) return { label: "Disabled", className: "held" };
  if (source.paused) return { label: "Paused", className: "held" };
  if (source.consecutive_failures > 0) return { label: `${source.consecutive_failures} failure${source.consecutive_failures === 1 ? "" : "s"}`, className: "attention" };
  return { label: "Running normally", className: "" };
}

async function loadSources({ quiet = false } = {}) {
  if (!quiet) elements.sourceList.innerHTML = '<div class="loading-row"><span></span><span></span><span></span></div>';
  try {
    const [sourcePayload, activityPayload] = await Promise.all([
      api("/sources"),
      api("/activity?limit=50"),
    ]);
    state.sources = sourcePayload.sources;
    state.activity = activityPayload;
    renderSummary();
    renderSchedule();
    renderExecutionJournal();
    renderSources();
  } catch (error) {
    elements.sourceList.innerHTML = `<p class="empty-ledger">${escapeHtml(error.message)}</p>`;
    elements.executionJournal.innerHTML = `<p class="empty-ledger">${escapeHtml(error.message)}</p>`;
    showToast(error.message, true);
  }
}

function renderSummary() {
  const registered = state.sources.filter((source) => source.registered).length;
  const active = state.sources.filter((source) => source.registered && source.enabled && !source.paused && !source.quarantined_at && source.consecutive_failures === 0).length;
  const held = state.sources.filter((source) => source.registered && (!source.enabled || source.paused)).length;
  const attention = state.sources.filter((source) => !source.registered || source.quarantined_at || source.consecutive_failures > 0).length;
  document.querySelector("#summary-registered").textContent = `${registered}/${state.sources.length}`;
  document.querySelector("#summary-active").textContent = active;
  document.querySelector("#summary-held").textContent = held;
  document.querySelector("#summary-attention").textContent = attention;
}

function renderSchedule() {
  const horizon = 24 * 60 * 60 * 1000;
  const upcoming = state.sources
    .filter((source) => source.next_run_at && source.enabled && !source.paused && !source.quarantined_at)
    .map((source) => ({ source, offset: new Date(source.next_run_at).valueOf() - Date.now() }))
    .filter(({ offset }) => offset <= horizon)
    .sort((a, b) => a.offset - b.offset);
  const due = upcoming.filter(({ offset }) => offset <= 10 * 60 * 1000);
  const visible = upcoming.filter(({ offset }) => offset > 10 * 60 * 1000).slice(0, 6);
  let lastPosition = 0;
  const futureMarkers = visible.map(({ source, offset }, index) => {
    const actualPosition = Math.max(2, Math.min(98, (offset / horizon) * 100));
    const position = Math.min(96, Math.max(actualPosition, lastPosition + 11));
    lastPosition = position;
    const stagger = index % 2 ? 28 : 0;
    return `<button class="tape-marker" data-source="${escapeHtml(source.source_key)}" style="left:${position}%;top:${stagger - 6}px">
      ${escapeHtml(source.display_name.replace(/ (candidate|parliamentary|India).*/i, ""))}
      <small>${escapeHtml(formatTime(source.next_run_at, true))}</small>
    </button>`;
  }).join("");
  const dueMarker = due.length
    ? `<div class="tape-marker tape-cluster" style="left:0"><strong>${due.length} source${due.length === 1 ? "" : "s"} due</strong><small>awaiting dispatch</small></div>`
    : "";
  elements.tape.innerHTML = dueMarker + futureMarkers;
  const hidden = upcoming.length - due.length - visible.length;
  if (hidden > 0) elements.tape.insertAdjacentHTML("beforeend", `<span class="tape-more">+${hidden} more</span>`);
  elements.tapeCaption.textContent = upcoming.length ? `${upcoming.length} sources are due within the window.` : "No active source is due within this window.";
  elements.tape.querySelectorAll("[data-source]").forEach((button) => button.addEventListener("click", () => openSource(button.dataset.source)));
}

function renderExecutionJournal() {
  const requests = state.activity.requests || [];
  const runs = state.activity.runs || [];
  const queued = requests.filter((request) => request.status === "pending").length;
  const active = runs.filter((run) => ["pending", "running"].includes(run.status)).length;
  const complete = runs.filter((run) => ["succeeded", "failed", "cancelled"].includes(run.status)).length;
  document.querySelector("#activity-queued").textContent = queued;
  document.querySelector("#activity-active").textContent = active;
  document.querySelector("#activity-complete").textContent = complete;

  const items = [
    ...requests.map((request) => ({
      kind: "request",
      source_key: request.source_key,
      status: request.status,
      action: request.request_type,
      detail: request.request_reason,
      actor: request.requested_by,
      occurred_at: request.requested_at,
    })),
    ...runs.map((run) => ({
      kind: "run",
      source_key: run.source_key,
      status: run.status,
      action: run.trigger,
      detail: run.error_message || run.run_key,
      actor: `attempt ${run.attempt_count}/${run.retry_limit + 1}`,
      occurred_at: run.created_at,
    })),
  ].sort((left, right) => new Date(right.occurred_at) - new Date(left.occurred_at));

  if (!items.length) {
    elements.executionJournal.innerHTML = `<div class="journal-empty"><strong>No orchestrated executions yet.</strong><p>History begins when a run request is queued or Dagster claims a schedule; earlier CLI and GitHub Actions runs were not structured control-plane records.</p></div>`;
    return;
  }

  elements.executionJournal.innerHTML = items.slice(0, 20).map((item) => `
    <button class="journal-row" type="button" data-journal-source="${escapeHtml(item.source_key)}">
      <span class="journal-kind">${escapeHtml(item.kind)}</span>
      <span class="journal-source"><strong>${escapeHtml(item.source_key)}</strong><small>${escapeHtml(item.action.replaceAll("_", " "))}</small></span>
      <span><strong class="run-status status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</strong><small>${escapeHtml(item.actor)}</small></span>
      <span class="journal-detail">${escapeHtml(item.detail)}</span>
      <time>${escapeHtml(formatTime(item.occurred_at))}</time>
    </button>`).join("");
  elements.executionJournal.querySelectorAll("[data-journal-source]").forEach((row) => row.addEventListener("click", () => openSource(row.dataset.journalSource)));
}

function renderSources() {
  const query = elements.search.value.trim().toLowerCase();
  const sources = state.sources.filter((source) => [source.display_name, source.publisher, source.source_key, source.authority_role].join(" ").toLowerCase().includes(query));
  if (!sources.length) {
    elements.sourceList.innerHTML = '<p class="empty-ledger">No source matches this filter.</p>';
    return;
  }
  elements.sourceList.innerHTML = sources.map((source) => {
    const condition = sourceCondition(source);
    const latest = source.latest_run;
    return `<button class="source-row" type="button" data-source="${escapeHtml(source.source_key)}">
      <span class="source-name"><strong>${escapeHtml(source.display_name)}</strong><span>${escapeHtml(source.publisher)} · <span class="source-key">${escapeHtml(source.source_key)}</span></span></span>
      <span><span class="authority-pill ${escapeHtml(source.authority_role)}">${escapeHtml(source.authority_role)}</span><span class="cell-secondary"> Tier ${source.trust_tier}</span></span>
      <span><span class="status-line"><i class="status-dot ${condition.className}"></i>${escapeHtml(condition.label)}</span><span class="cell-secondary">${escapeHtml(formatCadence(source.effective_config.frequency_seconds))}</span></span>
      <span><strong>${escapeHtml(formatTime(source.next_run_at, true))}</strong><span class="cell-secondary">${escapeHtml(source.next_run_at ? formatTime(source.next_run_at) : "No schedule")}</span></span>
      <span><strong class="run-status">${escapeHtml(latest?.status || "NO RUN")}</strong><span class="cell-secondary">${escapeHtml(latest ? formatTime(latest.created_at, true) : "No history")}</span></span>
    </button>`;
  }).join("");
  elements.sourceList.querySelectorAll("[data-source]").forEach((row) => row.addEventListener("click", () => openSource(row.dataset.source)));
}

async function openSource(sourceKey) {
  state.selected = sourceKey;
  elements.scrim.hidden = false;
  elements.drawer.classList.add("open");
  elements.drawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  document.querySelector("#drawer-title").textContent = "Loading source…";
  try {
    state.detail = await api(`/sources/${encodeURIComponent(sourceKey)}`);
    renderDrawer();
    document.querySelector("#drawer-close").focus();
  } catch (error) {
    showToast(error.message, true);
    closeDrawer();
  }
}

function closeDrawer() {
  elements.drawer.classList.remove("open");
  elements.drawer.setAttribute("aria-hidden", "true");
  elements.scrim.hidden = true;
  document.body.style.overflow = "";
}

function renderDrawer() {
  const { source, manifest } = state.detail;
  const config = source.effective_config;
  const guardrails = source.guardrails;
  const condition = sourceCondition(source);
  document.querySelector("#drawer-key").textContent = source.source_key;
  document.querySelector("#drawer-title").textContent = source.display_name;
  document.querySelector("#drawer-publisher").textContent = `${source.publisher} · ${source.adapter} · ${source.license}`;
  document.querySelector("#drawer-status").innerHTML = `
    <div><span>Condition</span><strong>${escapeHtml(condition.label)}</strong></div>
    <div><span>Next run</span><strong>${escapeHtml(formatTime(source.next_run_at, true))}</strong></div>
    <div><span>Definition</span><strong>rev ${source.active_revision} / ${escapeHtml((source.git_commit_sha || "unregistered").slice(0, 8))}</strong></div>`;
  document.querySelector("#runtime-enabled").checked = config.enabled;
  document.querySelector("#runtime-frequency").value = config.frequency_seconds ?? "";
  document.querySelector("#runtime-concurrency").value = config.concurrency_limit;
  document.querySelector("#runtime-rate").value = config.rate_limit_per_minute;
  document.querySelector("#runtime-retries").value = config.retry_limit;
  document.querySelector("#runtime-reason").value = "";
  document.querySelector("#guardrail-note").textContent = `frequency ${formatCadence(guardrails.min_frequency_seconds)} — ${formatCadence(guardrails.max_frequency_seconds)} · concurrency ≤ ${guardrails.max_concurrency} · rate ≤ ${guardrails.max_rate_limit_per_minute}/min · retries ≤ ${guardrails.max_retry_limit}`;
  const pause = document.querySelector("#pause-button");
  pause.textContent = source.paused ? "Resume source" : "Pause source";
  pause.disabled = !source.registered;
  const quarantine = document.querySelector("#quarantine-button");
  quarantine.textContent = source.quarantined_at ? "Release quarantine" : "Quarantine source";
  quarantine.classList.toggle("button-danger", !source.quarantined_at);
  quarantine.classList.toggle("button-secondary", Boolean(source.quarantined_at));
  quarantine.disabled = !source.registered;
  document.querySelector("#runtime-form").querySelectorAll("input, textarea, button").forEach((input) => { if (input.id !== "reset-button") input.disabled = !source.registered; });
  document.querySelector("#reset-button").disabled = !source.registered || !Object.keys(source.admin_overrides).length;
  document.querySelector("#run-form").querySelectorAll("input, textarea, select, button").forEach((input) => { input.disabled = !source.registered || Boolean(source.quarantined_at); });
  renderHistory();
  document.querySelector("#runtime-form").dataset.original = JSON.stringify(config);
  document.querySelector("#runtime-form").dataset.manifest = JSON.stringify(manifest);
}

function renderHistory() {
  const items = state.history === "runs" ? state.detail.runs : state.detail.revisions;
  const target = document.querySelector("#history-list");
  document.querySelector("#runs-tab").classList.toggle("active", state.history === "runs");
  document.querySelector("#revisions-tab").classList.toggle("active", state.history === "revisions");
  if (!items.length) {
    target.innerHTML = `<p class="empty-ledger">No ${state.history === "runs" ? "pipeline executions" : "runtime changes"} recorded yet.</p>`;
    return;
  }
  target.innerHTML = items.map((item) => state.history === "runs"
    ? `<article class="history-item"><span class="run-status">${escapeHtml(item.status)}</span><div><strong>${escapeHtml(item.trigger)} · attempt ${item.attempt_count}/${item.retry_limit + 1}</strong><p>${escapeHtml(item.error_message || item.run_key)}</p></div><time>${escapeHtml(formatTime(item.created_at))}</time></article>`
    : `<article class="history-item"><span class="run-status">REV ${item.revision}</span><div><strong>${escapeHtml(item.operation)} by ${escapeHtml(item.changed_by)}</strong><p>${escapeHtml(item.change_reason)}</p></div><time>${escapeHtml(formatTime(item.created_at))}</time></article>`
  ).join("");
}

async function mutate(path, method, body, successMessage) {
  const payload = await api(path, { method, body: JSON.stringify(body) });
  showToast(successMessage);
  await loadSources({ quiet: true });
  if (state.selected) {
    state.detail = await api(`/sources/${encodeURIComponent(state.selected)}`);
    renderDrawer();
  }
  return payload;
}

function requireReason(elementId) {
  const value = document.querySelector(elementId).value.trim();
  if (value.length < 3) throw new Error("Add a reason of at least three characters for the audit record.");
  return value;
}

function showToast(message, error = false) {
  clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.toggle("error", error);
  elements.toast.hidden = false;
  state.toastTimer = setTimeout(() => { elements.toast.hidden = true; }, 4200);
}

elements.search.addEventListener("input", renderSources);
document.querySelector("#refresh-button").addEventListener("click", () => loadSources());
document.querySelector("#drawer-close").addEventListener("click", closeDrawer);
elements.scrim.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && elements.drawer.classList.contains("open")) closeDrawer(); });

document.querySelector("#runtime-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const original = JSON.parse(event.currentTarget.dataset.original);
    const desired = {
      enabled: document.querySelector("#runtime-enabled").checked,
      frequency_seconds: document.querySelector("#runtime-frequency").value === "" ? null : Number(document.querySelector("#runtime-frequency").value),
      concurrency_limit: Number(document.querySelector("#runtime-concurrency").value),
      rate_limit_per_minute: Number(document.querySelector("#runtime-rate").value),
      retry_limit: Number(document.querySelector("#runtime-retries").value),
    };
    const patch = Object.fromEntries(Object.entries(desired).filter(([key, value]) => value !== original[key]));
    if (!Object.keys(patch).length) throw new Error("No runtime values have changed.");
    await mutate(`/sources/${encodeURIComponent(state.selected)}/runtime`, "PATCH", { patch, reason: requireReason("#runtime-reason") }, "Runtime configuration saved.");
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#pause-button").addEventListener("click", async () => {
  try {
    const pausing = !state.detail.source.paused;
    const reason = window.prompt(`${pausing ? "Pause" : "Resume"} reason (stored in audit history):`);
    if (reason == null) return;
    if (reason.trim().length < 3) throw new Error("The reason must contain at least three characters.");
    await mutate(`/sources/${encodeURIComponent(state.selected)}/runtime`, "PATCH", { patch: { paused: pausing }, reason: reason.trim() }, pausing ? "Source paused." : "Source resumed.");
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#reset-button").addEventListener("click", async () => {
  try {
    const reason = requireReason("#runtime-reason");
    await mutate(`/sources/${encodeURIComponent(state.selected)}/runtime/reset`, "POST", { reason }, "Runtime reset to Git-owned defaults.");
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#quarantine-button").addEventListener("click", async () => {
  try {
    const quarantined = !state.detail.source.quarantined_at;
    const reason = window.prompt(`${quarantined ? "Quarantine" : "Release"} reason (stored in audit history):`);
    if (reason == null) return;
    if (reason.trim().length < 3) throw new Error("The reason must contain at least three characters.");
    await mutate(`/sources/${encodeURIComponent(state.selected)}/quarantine`, "POST", { quarantined, reason: reason.trim() }, quarantined ? "Source quarantined." : "Source released from quarantine.");
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#run-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const raw = document.querySelector("#run-parameters").value.trim();
    const parameters = raw ? JSON.parse(raw) : {};
    if (!parameters || Array.isArray(parameters) || typeof parameters !== "object") throw new Error("Run parameters must be a JSON object.");
    const requestType = document.querySelector("#run-type").value;
    await mutate(`/sources/${encodeURIComponent(state.selected)}/runs`, "POST", {
      request_type: requestType,
      parameters,
      idempotency_key: `${state.selected}:${requestType}:${Date.now()}`,
      reason: requireReason("#run-reason"),
    }, "Pipeline run request queued.");
    event.currentTarget.reset();
  } catch (error) { showToast(error.message, true); }
});

document.querySelector("#runs-tab").addEventListener("click", () => { state.history = "runs"; renderHistory(); });
document.querySelector("#revisions-tab").addEventListener("click", () => { state.history = "revisions"; renderHistory(); });

document.querySelector("#logout-button").addEventListener("click", async () => {
  const response = await fetch("/admin/logout", { method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": csrfToken() } });
  window.location.assign(response.redirected ? response.url : "/admin/login");
});

loadSources();
