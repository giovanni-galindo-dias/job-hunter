/* ============================================================
   Job Hunter — app.js   v3 (pós-conselho)
   Novas funcionalidades:
     - Filtro geográfico "Brasil only"
     - Badge "NOVO < 48h" com animação pulse
     - Indicador 🇧🇷 para vagas brasileiras
     - Label "Verificar" para vagas 3-4 anos (negociáveis no Brasil)
     - Rastreamento de entrevistas no Kanban + stats por fonte
     - Ordenação "Brasil primeiro"
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
  if (label === "Júnior")   return "seniority-junior";
  if (label === "Verificar") return "seniority-verify";
  if (label === "Ambíguo")  return "seniority-ambiguous";
  return "seniority-senior";
}

function seniorityIcon(label) {
  if (label === "Júnior")   return "✅";
  if (label === "Verificar") return "🔍";
  if (label === "Ambíguo")  return "⚠️";
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
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
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
  const sortBy     = $("#sort-select").value;
  const showAmb    = $("#show-ambiguous-toggle").checked;
  const brazilOnly = $("#brazil-only-toggle").checked;

  const label = useCache
    ? "Carregando do cache…"
    : "Buscando vagas em todas as fontes (15-30 s)…";

  $("#jobs-grid").innerHTML = `
    <div class="loader" style="grid-column:1/-1">
      <div class="spinner"></div><span>${label}</span>
    </div>`;
  $("#jobs-stats").innerHTML = "";
  $("#source-stats").innerHTML = "";

  try {
    await loadKanbanIds();
    const endpoint = useCache ? "/api/jobs/cache" : "/api/jobs/search";
    const params = new URLSearchParams({
      sort: sortBy,
      show_ambiguous: showAmb,
      brazil_only: brazilOnly,
    });
    const data = await apiFetch(`${endpoint}?${params}`);
    allJobs = data.jobs || [];

    // Se cache vazio, dispara busca real automaticamente
    if (useCache && allJobs.length === 0 && data.message) {
      toast("Cache vazio — iniciando busca nas APIs…", "info");
      return searchJobs(false);
    }

    // Timestamp da última busca
    const now = new Date().toLocaleTimeString("pt-BR", {hour:"2-digit", minute:"2-digit"});
    const src = useCache ? "cache" : "APIs";
    const lbl = $("#last-search-label");
    if (lbl) lbl.textContent = `Última busca: ${now} via ${src} — ${allJobs.length} vagas`;

    renderJobs(allJobs, data.stats || {});
  } catch (_) {
    $("#jobs-grid").innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">⚠️</div>
      <strong>Não foi possível buscar as vagas.</strong>
      <p>Verifique sua conexão. Fontes gratuitas: Gupy, Arbeitnow, Remotive, RemoteOK não precisam de chave.</p>
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
      <p>Configure as chaves de API no .env ou desative o filtro "Brasil only".</p>
    </div>`;
    statsEl.innerHTML = "";
    sourceEl.innerHTML = "";
    return;
  }

  const { total=0, junior=0, ambiguous=0, verify=0, brazil=0, new_48h=0,
          total_collected="—", total_deduped="—", total_filtered=jobs.length,
          from_cache=false, source_stats={} } = stats;

  const cacheTag = from_cache ? " 📦" : "";
  statsEl.innerHTML = `
    <div class="stat-pill">Exibindo <b>${total}</b>${cacheTag}</div>
    <div class="stat-pill">✅ Júnior <b>${junior}</b></div>
    <div class="stat-pill">🔍 Verificar <b>${verify}</b></div>
    <div class="stat-pill">⚠️ Ambíguo <b>${ambiguous}</b></div>
    <div class="stat-pill">🇧🇷 Brasil <b>${brazil}</b></div>
    ${new_48h > 0 ? `<div class="stat-pill" style="border-color:var(--accent)">🆕 Novas &lt;48h <b>${new_48h}</b></div>` : ""}
    <div class="stat-pill" style="font-size:11px">Coletadas <b>${total_collected}</b> → dedup <b>${total_deduped}</b> → filtro <b>${total_filtered}</b></div>
  `;

  // Pills de fonte com indicador BR
  if (Object.keys(source_stats).length) {
    const pills = Object.entries(source_stats).map(([src, s]) => {
      const errClass = s.error ? " source-error" : "";
      const errTip   = s.error ? ` title="${escHtml(s.error)}"` : "";
      const icon     = s.error ? "⚠" : (s.is_br ? "🇧🇷" : "✓");
      return `<span class="source-pill${errClass}"${errTip}>${icon} ${escHtml(src)}: <b>${s.collected}</b></span>`;
    }).join("");
    sourceEl.innerHTML = `<div class="source-legend">Fontes: ${pills}</div>`;
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

  const skillsHTML = (job.matched_skills || []).slice(0, 7)
    .map(s => `<span class="skill-tag">${escHtml(s)}</span>`).join("");

  const signalsHTML = (job.level_signals || []).slice(0, 3)
    .map(s => `<span class="level-signal">🔍 ${escHtml(s)}</span>`).join("");

  const senClass = seniorityClass(job.seniority_label);
  const senIcon  = seniorityIcon(job.seniority_label);
  const newBadge = job.is_new
    ? `<span class="new-badge">🆕 NOVO</span>`
    : "";
  const brFlag   = job.is_br ? `<span class="br-badge" title="Vaga brasileira">🇧🇷</span>` : "";

  return `
  <div class="job-card">
    <div class="job-card-header">
      <div style="flex:1;min-width:0">
        <div class="job-title">${escHtml(job.title)}</div>
        <div class="job-company">${escHtml(job.company)}</div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
        <div style="display:flex;gap:4px;align-items:center">
          ${brFlag}${newBadge}
          <span class="job-source">${escHtml(job.source)}</span>
        </div>
      </div>
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
let conversionStatsVisible = false;

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

async function toggleConversionStats() {
  const bar = $("#conversion-bar");
  conversionStatsVisible = !conversionStatsVisible;
  if (!conversionStatsVisible) {
    bar.style.display = "none";
    return;
  }
  try {
    const data = await apiFetch("/api/kanban/stats");
    const bySource = Object.entries(data.by_source || {});
    const sourceRows = bySource.map(([src, s]) => {
      const rate = s.total > 0 ? Math.round(s.interviews / s.total * 100) : 0;
      const bar = `<div style="height:4px;background:var(--accent);width:${rate}%;border-radius:2px;margin-top:4px"></div>`;
      return `<div class="stat-pill" style="flex-direction:column;align-items:flex-start;padding:8px 12px">
        <span style="font-size:11px;font-weight:700">${escHtml(src)}</span>
        <span style="font-size:11px;color:var(--muted)">${s.interviews}/${s.total} entrevistas (${rate}%)${bar}</span>
      </div>`;
    }).join("");

    bar.innerHTML = `
      <div class="conversion-bar">
        <div class="conv-metric"><div class="val">${data.total}</div><div class="lbl">no Kanban</div></div>
        <div class="conv-metric"><div class="val" style="color:var(--accent2)">${data.interviews}</div><div class="lbl">entrevistas</div></div>
        <div class="conv-metric"><div class="val" style="color:var(--success)">${data.offers}</div><div class="lbl">ofertas</div></div>
        <div class="conv-metric"><div class="val">${data.conversion_rate}%</div><div class="lbl">taxa conversão</div></div>
        <div style="flex:1;display:flex;gap:8px;flex-wrap:wrap">${sourceRows}</div>
      </div>`;
    bar.style.display = "block";
  } catch (_) {}
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
  const intDot   = job.interview_scheduled
    ? `<span class="interview-dot" title="Entrevista marcada ✓"></span>`
    : "";
  const brFlag   = job.is_br ? "🇧🇷 " : "";

  return `
  <div class="kanban-card" draggable="true" data-id="${job.id}">
    <div class="kcard-title">${escHtml(job.title)}</div>
    <div class="kcard-company">${brFlag}${escHtml(job.company)}</div>
    <div class="kcard-footer">
      <div style="display:flex;gap:4px;align-items:center">
        ${intDot}
        <span class="seniority-badge ${senClass}" style="font-size:10px">
          ${seniorityIcon(senLabel)} ${job.seniority_score ?? "—"}
        </span>
        <span class="score-badge ${fitScoreClass(job.fit_score ?? 0)}" style="font-size:10px">
          ${job.fit_score ?? "—"}
        </span>
      </div>
      <div class="kcard-actions">
        ${job.url ? `<a href="${escHtml(job.url)}" target="_blank" rel="noopener" class="btn btn-ghost btn-sm btn-icon" title="Abrir">🔗</a>` : ""}
        <button class="btn btn-ghost btn-sm btn-icon kcard-interview-btn" data-id="${job.id}"
          title="${job.interview_scheduled ? "Desmarcar entrevista" : "Marcar entrevista ✓"}">
          ${job.interview_scheduled ? "📅✓" : "📅"}
        </button>
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
        if (col === "interview") toast("📅 Entrevista marcada automaticamente!", "info");
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
  $$(".kcard-interview-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await apiFetch(`/api/kanban/${btn.dataset.id}/interview`, {
          method: "PATCH",
          body: JSON.stringify({}),
        });
        toast("Status de entrevista atualizado!", "success");
        await loadKanban();
      } catch (_) {}
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
  } catch (_) { out.textContent = "Erro ao gerar a carta."; }
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
  $("#cache-btn").addEventListener("click",  () => searchJobs(true));
  $("#show-ambiguous-toggle").addEventListener("change", () => searchJobs(true));
  $("#brazil-only-toggle").addEventListener("change", () => searchJobs(true));
  $("#sort-select").addEventListener("change", () => searchJobs(true));

  $("#modal-save-btn").addEventListener("click", saveNotes);
  $("#modal-close-btn").addEventListener("click", closeModal);
  $("#modal-overlay").addEventListener("click", e => {
    if (e.target === $("#modal-overlay")) closeModal();
  });

  $("#cl-generate-btn").addEventListener("click", generateLetter);
  $("#cl-copy-btn").addEventListener("click", copyLetter);
  $("#cl-clear-btn").addEventListener("click", clearLetter);

  // Tenta cache primeiro (instantâneo); se vazio, não busca automaticamente
  // (economiza cota das APIs)
  searchJobs(true);
});
