const grid = document.getElementById("grid");
const panels = document.querySelectorAll(".tool-panel");
const toast = document.getElementById("toast");

function showPanel(tool) {
  panels.forEach((p) => (p.hidden = p.dataset.tool !== tool));
  document.querySelectorAll(".tool-card").forEach((c) => c.classList.toggle("active", c.dataset.tool === tool));
  const panel = document.querySelector(`.tool-panel[data-tool="${tool}"]`);
  if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

grid.addEventListener("click", (e) => {
  const card = e.target.closest(".tool-card");
  if (!card) return;
  showPanel(card.dataset.tool);
});

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => (toast.hidden = true), 4500);
}

function filenameFromDisposition(disposition, fallback) {
  if (!disposition) return fallback;
  const match = /filename="?([^";]+)"?/.exec(disposition);
  return match ? match[1] : fallback;
}

panels.forEach((form) => {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const endpoint = form.dataset.endpoint;
    const fallbackName = form.dataset.output;
    const button = form.querySelector('button[type="submit"]');
    const resultNote = form.querySelector(".result-note");
    button.disabled = true;
    const originalLabel = button.textContent;
    button.textContent = "Processing...";

    try {
      const formData = new FormData(form);
      const response = await fetch(endpoint, { method: "POST", body: formData });

      if (!response.ok) {
        let message = "Something went wrong.";
        try {
          const data = await response.json();
          message = data.error || message;
        } catch (_) {
          /* ignore */
        }
        showToast(message, true);
        return;
      }

      if (resultNote && response.headers.get("X-Compressed-Bytes")) {
        const original = Number(response.headers.get("X-Original-Bytes"));
        const compressed = Number(response.headers.get("X-Compressed-Bytes"));
        const met = response.headers.get("X-Met-Target") === "True";
        const pct = original ? Math.round((1 - compressed / original) * 100) : 0;
        resultNote.textContent =
          `${(original / 1024).toFixed(0)} KB -> ${(compressed / 1024).toFixed(0)} KB ` +
          `(${pct}% smaller)` + (met ? "" : " — could not fully reach target");
      }

      const blob = await response.blob();
      const filename = filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackName);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("Done — your file is downloading.");
    } catch (err) {
      showToast("Network error: " + err.message, true);
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  });
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}
