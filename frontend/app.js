const apiBaseUrl = window.appConfig?.apiBaseUrl || "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);
const fileInput = $("fileInput");
const analyzeBtn = $("analyzeBtn");
const clearBtn = $("clearBtn");
const statusEl = $("status");
const preview = $("preview");
const overlay = $("overlay");
const progress = $("progress");
const offlineBanner = $("offlineBanner");
const exerciseSelect = $("exerciseSelect");

let selectedFile = null;

$("apiUrl").textContent = apiBaseUrl;

// ------------------------------------------------------------------ backend up?
async function checkBackend() {
  try {
    const r = await fetch(`${apiBaseUrl}/health`, { cache: "no-store" });
    if (!r.ok) throw new Error();
    const data = await r.json();
    offlineBanner.classList.add("hidden");
    statusEl.textContent = `backend: ok (${data.model || "?"})`;
    return true;
  } catch {
    offlineBanner.classList.remove("hidden");
    statusEl.textContent = "backend: недоступен";
    return false;
  }
}
$("retryBtn").addEventListener("click", checkBackend);
checkBackend();

// ---------------------------------------------------------------------- tabs
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const isHistory = tab.dataset.tab === "history";
    $("analyzeView").classList.toggle("hidden", isHistory);
    $("historyView").classList.toggle("hidden", !isHistory);
    $("analyzeControls").classList.toggle("hidden", isHistory);
    if (isHistory) loadHistory();
  });
});

// -------------------------------------------------------------------- analyze
fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files?.[0] || null;
  if (!selectedFile) return;
  preview.src = URL.createObjectURL(selectedFile);
  analyzeBtn.disabled = false;
  clearBtn.disabled = false;
  statusEl.textContent = "кадр выбран";
});

clearBtn.addEventListener("click", resetView);

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  const form = new FormData();
  form.append("image", selectedFile);
  form.append("exercise", exerciseSelect.value);

  showProgress(true);
  statusEl.textContent = "анализ...";
  analyzeBtn.disabled = true;

  try {
    const resp = await fetch(`${apiBaseUrl}/analyze`, { method: "POST", body: form });
    if (!resp.ok) throw new Error(`http ${resp.status}`);
    const data = await resp.json();
    renderResult(data);
    statusEl.textContent = "готово";
  } catch (err) {
    statusEl.textContent = `ошибка backend: ${err.message}`;
    checkBackend();
  } finally {
    analyzeBtn.disabled = false;
    showProgress(false);
  }
});

function showProgress(on) {
  progress.classList.toggle("hidden", !on);
  progress.classList.toggle("indeterminate", on);
}

function resetView() {
  selectedFile = null;
  fileInput.value = "";
  preview.removeAttribute("src");
  clearOverlay();
  analyzeBtn.disabled = true;
  clearBtn.disabled = true;
  $("modelName").textContent = "-";
  $("exType").textContent = "-";
  $("score").textContent = "-";
  $("depth").textContent = "-";
  $("partsList").innerHTML = '<li class="muted">-</li>';
  $("anglesList").innerHTML = '<li class="muted">-</li>';
  $("feedbackList").innerHTML = '<li class="muted">-</li>';
  $("jsonOut").textContent = "{}";
  statusEl.textContent = "backend: ожидает кадр";
}

function clearOverlay() {
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
}

function renderResult(data) {
  $("modelName").textContent = data.model || "-";
  $("exType").textContent = data.exercise_type || "-";
  $("score").textContent = data.form_score?.toFixed?.(2) ?? "-";
  $("depth").textContent = data.depth != null ? data.depth.toFixed(2) : "-";
  $("jsonOut").textContent = JSON.stringify(data, null, 2);

  // detected body parts
  $("partsList").innerHTML =
    (data.parts || [])
      .map(
        (p) =>
          `<li><span class="dot" style="background:${p.color}"></span>${p.label}
           <span class="conf">${(p.confidence * 100).toFixed(0)}%</span></li>`,
      )
      .join("") || '<li class="muted">частей не найдено</li>';

  // joint angles
  const angles = data.joint_angles || {};
  $("anglesList").innerHTML =
    Object.keys(angles)
      .map((k) => `<li>${k}<span class="conf">${angles[k]}°</span></li>`)
      .join("") || '<li class="muted">-</li>';

  // coach feedback + warnings
  const warns = (data.warnings || []).map((w) => `<li class="warn">⚠ ${w.message}</li>`);
  const tips = (data.feedback || []).map((t) => `<li>💡 ${t}</li>`);
  $("feedbackList").innerHTML = [...warns, ...tips].join("") || '<li class="muted">-</li>';

  drawOverlay(data.parts || []);
}

function drawOverlay(parts) {
  overlay.width = overlay.clientWidth;
  overlay.height = overlay.clientHeight;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.lineWidth = 2;
  ctx.font = "13px system-ui";
  for (const part of parts) {
    const [x, y, w, h] = part.box;
    ctx.strokeStyle = part.color || "#2447ff";
    ctx.fillStyle = part.color || "#2447ff";
    ctx.strokeRect(x * overlay.width, y * overlay.height, w * overlay.width, h * overlay.height);
    ctx.fillText(part.label, x * overlay.width + 4, y * overlay.height + 16);
  }
}

// -------------------------------------------------------------------- history
$("refreshHistory").addEventListener("click", loadHistory);

async function loadHistory() {
  const body = $("historyBody");
  body.innerHTML = '<tr><td colspan="6" class="muted">загрузка...</td></tr>';
  try {
    const resp = await fetch(`${apiBaseUrl}/sessions`);
    if (!resp.ok) throw new Error(`http ${resp.status}`);
    const sessions = await resp.json();
    if (!sessions.length) {
      body.innerHTML = '<tr><td colspan="6" class="muted">пока пусто</td></tr>';
      return;
    }
    body.innerHTML = sessions
      .map((s) => {
        const date = (s.started_at || "").replace("T", " ").slice(0, 16);
        const url = `${apiBaseUrl}/sessions/${s.session_id}/export?format=csv`;
        return `<tr>
          <td>${date}</td><td>${s.exercise}</td><td>${s.rep_count}</td>
          <td>${s.frames}</td><td>${s.avg_form_score}</td>
          <td><a href="${url}" target="_blank">csv</a></td>
        </tr>`;
      })
      .join("");
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="warn">не удалось загрузить историю: ${err.message}</td></tr>`;
  }
}
