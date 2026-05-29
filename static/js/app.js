/* ============================================================
   Job Hunter — app.js
   SPA com 4 seções: Vagas | Kanban | Respostas | Carta
   ============================================================ */

const API = "";

/* ===== Utilitários ===== */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function toast(msg, type = "info", duration = 3200) {
  const ct = $("#toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  const icons = { success: "✓", error: "✗", info: "ℹ" };
  el.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${msg}`;
  ct.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

function fitScoreClass(s) {
  if (s >= 55) return "score-high";
  if (s >= 28) return "score-medium";
  return "score-low";
}

function seniorityClass(label) {
  if (label === "Júnior")     return "seniority-junior";
  if (label === "Ambíguo")    return "seniority-ambiguous";
  return "seniority-senior";
}

function seniorityIcon(label) {
  if (label === "Júnior")  return "✅";
  if (label === "Ambíguo") return "⚠️";
  return "🚫";
}

function copyText(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = "✓ Copiado!";
    btn.classList.add("copy-success");
    setTimeout(() => { btn.textContent = orig; btn.classList.remove("copy-success"); }, 1800);
  });
}

async function apiFetch(path, opts = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  } catch (e) {
    toast("Erro de comunicação: " + e.message, "error");
    throw e;
  }
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}

/* ===== Navigation ===== */
function initNav() {
  $$(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".nav-btn").forEach(b => b.classList.remove("active"));
      $$(".page").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const target = btn.dataset.page;
      $(`#page-${target}`).classList.add("active");
      if (target === "kanban")  loadKanban();
      if (target === "answers") loadAnswers();
    });
  });
}

/* ================================================================
   PAGE 1 — VAGAS
   ================================================================ */
let allJobs = [];
let kanbanIds = new Set();

async function loadKanbanIds() {
  try {
    const data = await apiFetch("/api/kanban/");
    kanbanIds = new Set(data.jobs.map(j => j.external_id));
  } catch (_) {}
}

async function searchJobs(useCache = false) {
  const sortBy        = $("#sort-select").value;
  const showAmbiguous = $("#show-ambiguous-toggle").checked;

  const label = useCache ? "Carregando do cache…" : "Buscando vagas em todas as fontes (pode levar 15-30 s)…";
  $("#jobs-grid").innerHTML = `
    <div class="loader" style="grid-column:1/-1">
      <div class="spinner"></div>
      <span>${label}</span>
    </div>`;
  $("#jobs-stats").innerHTML = "";
  $("#source-stats").innerHTML = "";

  try {
    await loadKanbanIds();
    const endpoint = useCache ? "/api/jobs/cache" : "/api/jobs/search";
    const params = new URLSearchParams({ sort: sortBy, show_ambiguous: showAmbiguous });

    const data = await apiFetch(`${endpoint}?${params}`);
    allJobs = data.jobs || [];
    renderJobs(allJobs, data.stats || {});
  } catch (_) {
    $("#jobs-grid").innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">⚠️</div>
      <strong>Não foi possível buscar as vagas.</strong>
      <p>Verifique sua conexão ou as chaves de API no .env.</p>
    </div>`;
  }
}

function renderJobs(jobs, stats = {}) {
  const grid     = $("#jobs-grid");
  const statsEl  = $("#jobs-stats");
  const sourceEl = $("#source-stats");

  if (!jobs.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">🔍</div>
      <strong>Nenhuma vaga compatível encontrada.</strong>
      <p>Configure ao menos uma chave de API no .env (SerpAPI recomendado) e busque novamente.</p>
    </div>`;
    statsEl.innerHTML = "";
    sourceEl.innerHTML = "";
    return;
  }

  const junior    = stats.junior    ?? jobs.filter(j => j.seniority_score >= 70).length;
  const ambiguous = stats.ambiguous ?? jobs.filter(j => j.seniority_score >= 40 && j.seniority_score < 70).length;
  const collected = stats.total_collected ?? "—";
  const deduped   = stats.total_deduped   ?? "—";
  const filtered  = stats.total_filtered  ?? jobs.length;
  const cached    = stats.from_cache      ? " 📦 cache" : "";

  statsEl.innerHTML = `
    <div class="stat-pill">Exibindo <b>${jobs.length}</b>${cached}</div>
    <div class="stat-pill">✅ Júnior confirmado <b>${junior}</b></div>
    <div class="stat-pill">⚠️ Ambíguo <b>${ambiguous}</b></div>
    <div class="stat-pill">Coletadas <b>${collected}</b> → dedup <b>${deduped}</b> → filtro <b>${filtered}</b></div>
  `;

  // Estatísticas por fonte
  const sourceStats = stats.source_stats || {};
  if (Object.keys(sourceStats).length) {
    const pills = Object.entries(sourceStats).map(([src, s]) => {
      const errClass = s.error ? " source-error" : "";
      const errTip   = s.error ? ` title="${escHtml(s.error)}"` : "";
      const icon     = s.error ? "⚠" : "✓";
      return `<span class="source-pill${errClass}"${errTip}>${icon} ${escHtml(src)}: <b>${s.collected}</b></span>`;
    }).join("");
    sourceEl.innerHTML = `<div class="source-legend">Fontes: ${pills}</div>`;
  } else {
    sourceEl.innerHTML = "";
  }

  grid.innerHTML = jobs.map(job => jobCardHTML(job)).join("");

  $$(".add-kanban-btn", grid).forEach(btn => {
    btn.addEventListener("click", () => addToKanban(btn.dataset.id));
  });

  $$(".gen-letter-btn", grid).forEach(btn => {
    btn.addEventListener("click", () => {
      const job = allJobs.find(j => j.id === btn.dataset.id);
      if (job) openLetterFromJob(job);
    });
  });
}

function jobCardHTML(job) {
  const inKanban = kanbanIds.has(job.id);
  const addLabel = inKanban ? "✓ No Kanban" : "+ Kanban";

  // Skills
  const skillsHTML = (job.matched_skills || []).slice(0, 7).map(
    s => `<span class="skill-tag">${escHtml(s)}</span>`
  ).join("");

  // Level signals
  const signalsHTML = (job.level_signals || []).slice(0, 3).map(
    s => `<span class="level-signal">🔍 ${escHtml(s)}</span>`
  ).join("");

  const senClass = seniorityClass(job.seniority_label);
  const senIcon  = seniorityIcon(job.seniority_label);

  return `
  <div class="job-card">
    <div class="job-card-header">
      <div style="flex:1;min-width:0">
        <div class="job-title">${escHtml(job.title)}</div>
        <div class="job-company">${escHtml(job.company)}</div>
      </div>
      <span class="job-source">${escHtml(job.source)}</span>
    </div>

    <div class="score-row">
      <span class="score-label">Nível</span>
      <span class="seniority-badge ${senClass}">${senIcon} ${escHtml(job.seniority_label)} ${job.seniority_score}</span>
      <span class="score-label" style="margin-left:4px">Fit</span>
      <span class="score-badge ${fitScoreClass(job.fit_score)}">${job.fit_score}</span>
    </div>

    <div class="job-meta">
      <span>📍 ${escHtml(job.location || "—")}</span>
      <span>📅 ${escHtml(job.posted_at || "—")}</span>
    </div>

    ${signalsHTML ? `<div class="level-signals">${signalsHTML}</div>` : ""}
    ${skillsHTML  ? `<div class="skills-tags">${skillsHTML}</div>` : ""}

    <div class="job-card-actions">
      <a href="${escHtml(job.url)}" target="_blank" rel="noopener" class="btn btn-primary btn-sm">🔗 Abrir vaga</a>
      <button class="btn btn-secondary btn-sm add-kanban-btn" data-id="${escHtml(job.id)}"
        ${inKanban ? "disabled" : ""}>${addLabel}</button>
      <button class="btn btn-ghost btn-sm gen-letter-btn" data-id="${escHtml(job.id)}">✉ Carta</button>
    </div>
  </div>`;
}

async function addToKanban(jobId) {
  const job = allJobs.find(j => j.id === jobId);
  if (!job) return;
  try {
    const data = await apiFetch("/api/kanban/add", {
      method: "POST",
      body: JSON.stringify({ ...job, external_id: job.id }),
    });
    if (data.message === "already_exists") {
      toast("Vaga já está no Kanban.", "info");
    } else {
      toast("Adicionado ao Kanban! ✓", "success");
      kanbanIds.add(jobId);
      const btn = $(`.add-kanban-btn[data-id="${jobId}"]`);
      if (btn) { btn.textContent = "✓ No Kanban"; btn.disabled = true; }
    }
  } catch (_) {}
}

function openLetterFromJob(job) {
  $$(".nav-btn").forEach(b => b.classList.remove("active"));
  $$(".page").forEach(p => p.classList.remove("active"));
  $(`.nav-btn[data-page="letter"]`).classList.add("active");
  $("#page-letter").classList.add("active");
  $("#cl-title").value = job.title || "";
  $("#cl-company").value = job.company || "";
  $("#cl-description").value = job.description || "";
  toast("Vaga carregada — clique em 'Gerar Carta'!", "info");
}

/* ================================================================
   PAGE 2 — KANBAN
   ================================================================ */
const COL_LABELS = {
  apply:     "📋 Para Aplicar",
  ongoing:   "🚀 Em Andamento",
  interview: "💬 Teste / Entrevista",
  closed:    "🏁 Encerrado",
};

let kanbanJobs = [];
let draggedJobId = null;

async function loadKanban() {
  const board = $("#kanban-board");
  board.innerHTML = `<div class="loader" style="grid-column:1/-1"><div class="spinner"></div><span>Carregando…</span></div>`;
  try {
    const data = await apiFetch("/api/kanban/");
    kanbanJobs = data.jobs || [];
    renderBoard();
  } catch (_) {
    board.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">⚠️</div><strong>Erro ao carregar o Kanban.</strong></div>`;
  }
}

function renderBoard() {
  const board = $("#kanban-board");
  board.innerHTML = Object.entries(COL_LABELS).map(([col, label]) => {
    const cards = kanbanJobs.filter(j => j.column === col);
    return `
    <div class="kanban-col" data-col="${col}">
      <div class="kanban-col-header">
        <span>${label}</span>
        <span class="col-count">${cards.length}</span>
      </div>
      <div class="kanban-cards" data-col="${col}">
        ${cards.map(j => kanbanCardHTML(j)).join("")}
      </div>
    </div>`;
  }).join("");

  initDragDrop();
  initKanbanActions();
}

function kanbanCardHTML(job) {
  const senLabel = job.seniority_label || "Ambíguo";
  const senClass = seniorityClass(senLabel);
  return `
  <div class="kanban-card" draggable="true" data-id="${job.id}">
    <div class="kcard-title">${escHtml(job.title)}</div>
    <div class="kcard-company">${escHtml(job.company)}</div>
    <div class="kcard-footer">
      <div style="display:flex;gap:4px;align-items:center">
        <span class="seniority-badge ${senClass}" style="font-size:10px">
          ${seniorityIcon(senLabel)} ${job.seniority_score ?? "—"}
        </span>
        <span class="score-badge ${fitScoreClass(job.fit_score ?? 0)}" style="font-size:10px">
          Fit ${job.fit_score ?? "—"}
        </span>
      </div>
      <div class="kcard-actions">
        ${job.url ? `<a href="${escHtml(job.url)}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm btn-icon" title="Abrir">🔗</a>` : ""}
        <button class="btn btn-ghost btn-sm btn-icon kcard-notes-btn" data-id="${job.id}" title="Notas">📝</button>
        <button class="btn btn-ghost btn-sm btn-icon kcard-del-btn" data-id="${job.id}" title="Remover">🗑</button>
      </div>
    </div>
    ${job.notes ? `<div style="margin-top:6px;font-size:11px;color:var(--muted);font-style:italic">${escHtml(job.notes)}</div>` : ""}
  </div>`;
}

function initDragDrop() {
  $$(".kanban-card").forEach(card => {
    card.addEventListener("dragstart", e => {
      draggedJobId = parseInt(card.dataset.id);
      setTimeout(() => card.classList.add("dragging"), 0);
      e.dataTransfer.effectAllowed = "move";
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      $$(".kanban-cards").forEach(z => z.classList.remove("drag-over"));
      draggedJobId = null;
    });
  });

  $$(".kanban-cards").forEach(zone => {
    zone.addEventListener("dragover", e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", async e => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const col = zone.dataset.col;
      if (!draggedJobId || !col) return;
      try {
        await apiFetch(`/api/kanban/${draggedJobId}/move`, {
          method: "PATCH",
          body: JSON.stringify({ column: col }),
        });
        await loadKanban();
        toast(`Movido para ${COL_LABELS[col]}`, "success");
      } catch (_) {}
    });
  });
}

function initKanbanActions() {
  $$(".kcard-del-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Remover esta vaga do Kanban?")) return;
      try {
        await apiFetch(`/api/kanban/${btn.dataset.id}`, { method: "DELETE" });
        toast("Removido.", "info");
        await loadKanban();
      } catch (_) {}
    });
  });

  $$(".kcard-notes-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const job = kanbanJobs.find(j => j.id === parseInt(btn.dataset.id));
      if (job) openNotesModal(job);
    });
  });
}

function openNotesModal(job) {
  $("#modal-title").textContent = "Notas — " + job.title;
  $("#modal-notes-ta").value = job.notes || "";
  $("#modal-notes-id").value = job.id;
  $("#modal-overlay").classList.add("open");
}

async function saveNotes() {
  const id    = $("#modal-notes-id").value;
  const notes = $("#modal-notes-ta").value;
  try {
    await apiFetch(`/api/kanban/${id}/notes`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
    toast("Notas salvas!", "success");
    closeModal();
    await loadKanban();
  } catch (_) {}
}

function closeModal() {
  $("#modal-overlay").classList.remove("open");
}

/* ================================================================
   PAGE 3 — RESPOSTAS
   ================================================================ */
let allAnswers = [];

async function loadAnswers() {
  if (allAnswers.length) return;
  try {
    const data = await apiFetch("/api/answers/");
    allAnswers = data.answers || [];
    renderAnswers(allAnswers);
    buildCatFilter();
  } catch (_) {}
}

function buildCatFilter() {
  const cats = ["Todos", ...new Set(allAnswers.map(a => a.category))];
  const filter = $("#cat-filter");
  filter.innerHTML = cats.map(c =>
    `<button class="cat-pill${c === "Todos" ? " active" : ""}" data-cat="${escHtml(c)}">${escHtml(c)}</button>`
  ).join("");

  $$(".cat-pill", filter).forEach(pill => {
    pill.addEventListener("click", () => {
      $$(".cat-pill", filter).forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      const cat = pill.dataset.cat;
      renderAnswers(cat === "Todos" ? allAnswers : allAnswers.filter(a => a.category === cat));
    });
  });
}

function renderAnswers(list) {
  const grid = $("#answers-grid");
  grid.innerHTML = list.map(a => `
  <div class="answer-card">
    <div class="answer-category">${escHtml(a.category)}</div>
    <div class="answer-question">${escHtml(a.question)}</div>
    <div class="answer-text">${escHtml(a.answer)}</div>
    <button class="btn btn-secondary btn-sm copy-btn" data-answer-id="${a.id}">📋 Copiar</button>
  </div>`).join("");

  $$(".copy-btn", grid).forEach(btn => {
    btn.addEventListener("click", () => {
      const ans = allAnswers.find(a => a.id === parseInt(btn.dataset.answerId));
      if (ans) copyText(ans.answer, btn);
    });
  });
}

/* ================================================================
   PAGE 4 — CARTA DE APRESENTAÇÃO
   ================================================================ */
async function generateLetter() {
  const title       = $("#cl-title").value.trim();
  const company     = $("#cl-company").value.trim();
  const description = $("#cl-description").value.trim();

  if (!description) { toast("Cole o texto da vaga antes de gerar!", "error"); return; }

  const out = $("#cl-output");
  out.textContent = "Gerando carta…";
  out.classList.remove("placeholder");

  try {
    const data = await apiFetch("/api/cover-letter/generate", {
      method: "POST",
      body: JSON.stringify({ title, company, description }),
    });
    out.textContent = data.letter || "(sem resultado)";
    toast("Carta gerada! ✓", "success");
  } catch (_) {
    out.textContent = "Erro ao gerar a carta.";
  }
}

function copyLetter() {
  const text = $("#cl-output").textContent;
  if (!text || text.includes("aparecerá aqui")) { toast("Gere a carta primeiro!", "error"); return; }
  navigator.clipboard.writeText(text).then(() => toast("Carta copiada! ✓", "success"));
}

function clearLetter() {
  $("#cl-title").value = "";
  $("#cl-company").value = "";
  $("#cl-description").value = "";
  const out = $("#cl-output");
  out.textContent = "A carta gerada aparecerá aqui…";
  out.classList.add("placeholder");
}

/* ================================================================
   INIT
   ================================================================ */
document.addEventListener("DOMContentLoaded", () => {
  initNav();

  $("#search-btn").addEventListener("click", () => searchJobs(false));
  $("#cache-btn").addEventListener("click", () => searchJobs(true));
  $("#show-ambiguous-toggle").addEventListener("change", () => searchJobs(true));

  $("#modal-save-btn").addEventListener("click", saveNotes);
  $("#modal-close-btn").addEventListener("click", closeModal);
  $("#modal-overlay").addEventListener("click", e => {
    if (e.target === $("#modal-overlay")) closeModal();
  });

  $("#cl-generate-btn").addEventListener("click", generateLetter);
  $("#cl-copy-btn").addEventListener("click", copyLetter);
  $("#cl-clear-btn").addEventListener("click", clearLetter);

  // Tenta o cache primeiro (instantâneo); se vazio, busca nas APIs
  searchJobs(true);
});
