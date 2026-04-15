const backendMode = document.querySelector("#backend-mode");
const healthStatus = document.querySelector("#health-status");
const form = document.querySelector("#run-form");
const promptInput = document.querySelector("#prompt-input");
const userInput = document.querySelector("#user-input");
const formStatus = document.querySelector("#form-status");
const submitButton = document.querySelector("#submit-button");
const refreshButton = document.querySelector("#refresh-button");
const runsList = document.querySelector("#runs-list");
const emptyState = document.querySelector("#empty-state");
const runTemplate = document.querySelector("#run-template");

let refreshTimer = null;

boot();

async function boot() {
  await Promise.all([loadConfig(), loadRuns()]);
  refreshTimer = window.setInterval(loadRuns, 4000);
}

async function loadConfig() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    backendMode.textContent = payload.storage;
    healthStatus.textContent = payload.status;
  } catch (error) {
    backendMode.textContent = "Unavailable";
    healthStatus.textContent = "Offline";
  }
}

async function loadRuns() {
  try {
    const response = await fetch("/api/runs");
    const payload = await response.json();
    renderRuns(payload.runs ?? []);
  } catch (error) {
    formStatus.textContent = "Unable to load runs right now.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setSubmitting(true);
  formStatus.textContent = "Starting run...";

  try {
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: promptInput.value.trim(),
        user: userInput.value.trim() || "demo-user",
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Run creation failed");
    }

    form.reset();
    formStatus.textContent = `Run ${payload.run.id.slice(0, 8)} started.`;
    await loadRuns();
  } catch (error) {
    formStatus.textContent = error.message;
  } finally {
    setSubmitting(false);
  }
});

refreshButton.addEventListener("click", async () => {
  formStatus.textContent = "Refreshing runs...";
  await loadRuns();
  formStatus.textContent = "Runs updated.";
});

function renderRuns(runs) {
  runsList.replaceChildren();
  emptyState.hidden = runs.length > 0;

  runs.forEach((run) => {
    const fragment = runTemplate.content.cloneNode(true);
    fragment.querySelector(".run-title").textContent = run.result?.title || "Agent run";
    fragment.querySelector(".run-meta").textContent = [
      run.user,
      new Date(run.createdAt).toLocaleString(),
    ].join(" • ");
    fragment.querySelector(".run-badge").textContent = formatStatus(run.status);
    fragment.querySelector(".run-prompt").textContent = run.prompt;
    fragment.querySelector(".run-output").innerHTML = renderOutput(run);
    runsList.append(fragment);
  });
}

function renderOutput(run) {
  if (run.status === "queued" || run.status === "running") {
    return `<p class="output-copy">The backend is working on this run now.</p>`;
  }

  if (run.status === "failed") {
    return `<p class="output-copy error-copy">${escapeHtml(
      run.error || "The run failed."
    )}</p>`;
  }

  const bullets = (run.result?.bullets ?? [])
    .map((bullet) => `<li>${escapeHtml(bullet)}</li>`)
    .join("");

  return `
    <p class="output-copy">${escapeHtml(run.result?.summary || "Completed.")}</p>
    <ul class="output-list">${bullets}</ul>
  `;
}

function formatStatus(status) {
  const labels = {
    queued: "Queued",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
  };

  return labels[status] ?? status;
}

function setSubmitting(isSubmitting) {
  submitButton.disabled = isSubmitting;
  submitButton.textContent = isSubmitting ? "Starting..." : "Start agent run";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

window.addEventListener("beforeunload", () => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer);
  }
});
