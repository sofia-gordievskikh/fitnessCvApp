const apiBaseUrl = window.appConfig?.apiBaseUrl || "http://127.0.0.1:8000";

const fileInput = document.getElementById("fileInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const clearBtn = document.getElementById("clearBtn");
const statusEl = document.getElementById("status");
const preview = document.getElementById("preview");
const overlay = document.getElementById("overlay");
const modelName = document.getElementById("modelName");
const partsEl = document.getElementById("parts");
const scoreEl = document.getElementById("score");
const jsonOut = document.getElementById("jsonOut");

let selectedFile = null;

fileInput.addEventListener("change", () => {
  selectedFile = fileInput.files?.[0] || null;
  if (!selectedFile) return;

  preview.src = URL.createObjectURL(selectedFile);
  analyzeBtn.disabled = false;
  clearBtn.disabled = false;
  statusEl.textContent = "кадр выбран";
});

clearBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  preview.removeAttribute("src");
  clearOverlay();
  analyzeBtn.disabled = true;
  clearBtn.disabled = true;
  modelName.textContent = "-";
  partsEl.textContent = "-";
  scoreEl.textContent = "-";
  jsonOut.textContent = "{}";
  statusEl.textContent = "backend: ожидает кадр";
});

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  const form = new FormData();
  form.append("image", selectedFile);
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
  } finally {
    analyzeBtn.disabled = false;
  }
});

function clearOverlay() {
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
}

function renderResult(data) {
  modelName.textContent = data.model || "-";
  partsEl.textContent = (data.parts || []).map((p) => p.label).join(", ") || "-";
  scoreEl.textContent = data.form_score?.toFixed?.(2) ?? "-";
  jsonOut.textContent = JSON.stringify(data, null, 2);

  overlay.width = overlay.clientWidth;
  overlay.height = overlay.clientHeight;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  ctx.lineWidth = 2;
  ctx.font = "13px system-ui";

  for (const part of data.parts || []) {
    const [x, y, w, h] = part.box;
    ctx.strokeStyle = part.color || "#2447ff";
    ctx.fillStyle = part.color || "#2447ff";
    ctx.strokeRect(x * overlay.width, y * overlay.height, w * overlay.width, h * overlay.height);
    ctx.fillText(part.label, x * overlay.width + 4, y * overlay.height + 16);
  }
}
