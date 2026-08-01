const state = {
  points: [],
  thresholdPsi: 120,
  pipeBurstPsi: 150,
  frames: [],
  filter: "all",
};

const $ = (id) => document.getElementById(id);

const statusPill = $("status-pill");
const statusLabel = $("status-label");

function setStatus(mode, text) {
  statusPill.classList.remove("armed", "alert");
  if (mode) statusPill.classList.add(mode);
  statusLabel.textContent = text;
}

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request to ${path} failed (${res.status})`);
  }
  return data;
}

/* ---------------- Physics chart ---------------- */

let chart;

async function loadCurve() {
  const data = await api("/api/physics/curve?max_rpm=6000");
  state.points = data.points;
  state.thresholdPsi = data.threshold_psi;
  state.pipeBurstPsi = data.pipe_burst_psi;

  const ctx = $("pressure-chart").getContext("2d");
  const labels = data.points.map((p) => p.rpm);
  const values = data.points.map((p) => p.predicted_psi);
  const thresholdLine = data.points.map(() => data.threshold_psi);

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Predicted pressure (psi)",
          data: values,
          borderColor: "#34d1c4",
          backgroundColor: "rgba(52,209,196,0.08)",
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Safety threshold",
          data: thresholdLine,
          borderColor: "#f5a623",
          borderDash: [6, 4],
          pointRadius: 0,
          borderWidth: 1.5,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#7f9195", font: { family: "IBM Plex Mono", size: 11 } },
        },
        tooltip: {
          titleFont: { family: "IBM Plex Mono" },
          bodyFont: { family: "IBM Plex Mono" },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "RPM", color: "#7f9195", font: { family: "IBM Plex Mono", size: 11 } },
          ticks: { color: "#7f9195", maxTicksLimit: 8, font: { family: "IBM Plex Mono", size: 10 } },
          grid: { color: "#1a2427" },
        },
        y: {
          title: { display: true, text: "PSI", color: "#7f9195", font: { family: "IBM Plex Mono", size: 11 } },
          ticks: { color: "#7f9195", font: { family: "IBM Plex Mono", size: 10 } },
          grid: { color: "#1a2427" },
        },
      },
    },
  });
}

/* ---------------- Gauge + live tester ---------------- */

const GAUGE_ARC_LENGTH = 267; // matches the SVG path's approximate length

function updateGauge(predictedPsi, verdict) {
  const maxGaugePsi = state.pipeBurstPsi * 1.3;
  const clamped = Math.max(0, Math.min(predictedPsi, maxGaugePsi));
  const fraction = clamped / maxGaugePsi;

  const offset = GAUGE_ARC_LENGTH * (1 - fraction);
  $("gauge-fill").style.strokeDashoffset = offset;
  $("gauge-fill").style.stroke = verdict === "CATASTROPHIC" ? "#ff4d4f" : "#34d1c4";

  const angle = -90 + fraction * 180;
  $("gauge-needle").style.transform = `rotate(${angle}deg)`;

  $("gauge-psi").textContent = predictedPsi.toFixed(1);

  const badge = $("verdict-badge");
  badge.classList.remove("safe", "catastrophic");
  if (verdict === "SAFE") {
    badge.textContent = "✓ SAFE — within physical limits";
    badge.classList.add("safe");
  } else if (verdict === "CATASTROPHIC") {
    badge.textContent = "✕ CATASTROPHIC — packet would be dropped";
    badge.classList.add("catastrophic");
  } else {
    badge.textContent = "—";
  }
}

async function testCommand(rpm) {
  try {
    const result = await api("/api/physics/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rpm }),
    });
    updateGauge(result.predicted_pressure_psi, result.verdict);
  } catch (err) {
    console.error(err);
  }
}

const rpmSlider = $("rpm-slider");
const rpmNumber = $("rpm-number");

rpmSlider.addEventListener("input", () => {
  rpmNumber.value = rpmSlider.value;
});
rpmNumber.addEventListener("input", () => {
  const v = Math.max(0, Math.min(70000, Number(rpmNumber.value) || 0));
  rpmSlider.value = v;
});

$("btn-test").addEventListener("click", () => {
  testCommand(Number(rpmNumber.value));
});

/* ---------------- Traffic generation ---------------- */

$("btn-generate").addEventListener("click", async () => {
  const btn = $("btn-generate");
  const numNormal = Number($("input-normal").value) || 0;
  const numMalicious = Number($("input-malicious").value) || 0;

  btn.disabled = true;
  btn.textContent = "Generating…";
  try {
    const data = await api("/api/traffic/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ num_normal: numNormal, num_malicious: numMalicious }),
    });
    $("generate-hint").textContent =
      `Loaded ${data.frame_count} frame(s), ${data.byte_count} bytes ` +
      `(${data.normal} normal / ${data.malicious} malicious).`;
    $("btn-bridge").disabled = false;
    setStatus(null, "TRAFFIC LOADED — RUN BRIDGE");
    resetTable();
  } catch (err) {
    $("generate-hint").textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Traffic";
  }
});

/* ---------------- Bridge run ---------------- */

$("btn-bridge").addEventListener("click", async () => {
  const btn = $("btn-bridge");
  btn.disabled = true;
  btn.textContent = "Running…";
  try {
    const data = await api("/api/bridge/run", { method: "POST" });
    state.frames = data.frames;
    renderSummary(data.summary);
    renderTable();

    if (data.summary.catastrophic > 0) {
      setStatus("alert", `${data.summary.catastrophic} CATASTROPHIC COMMAND(S) FLAGGED`);
    } else {
      setStatus("armed", "ALL CLEAR — PHYSICS FIREWALL ARMED");
    }
  } catch (err) {
    $("generate-hint").textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Bridge → Physics Engine";
  }
});

function renderSummary(summary) {
  $("sum-total").textContent = summary.total;
  $("sum-safe").textContent = summary.safe;
  $("sum-catastrophic").textContent = summary.catastrophic;
}

function resetTable() {
  state.frames = [];
  renderSummary({ total: "–", safe: "–", catastrophic: "–" });
  $("sum-total").textContent = "–";
  $("sum-safe").textContent = "–";
  $("sum-catastrophic").textContent = "–";
  $("report-tbody").innerHTML =
    '<tr class="empty-row"><td colspan="7">Run the bridge to see parsed frames here.</td></tr>';
}

/* ---------------- Table + filters ---------------- */

document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.filter = btn.dataset.filter;
    renderTable();
  });
});

function renderTable() {
  const tbody = $("report-tbody");
  const rows = state.filter === "all"
    ? state.frames
    : state.frames.filter((f) => f.verdict === state.filter);

  if (rows.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No frames match this filter.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map((f) => `
    <tr class="verdict-${f.verdict}">
      <td>${f.frame}</td>
      <td>${f.transaction_id}</td>
      <td>${f.register_name ?? "-"}</td>
      <td>${f.register_value ?? "-"}</td>
      <td>${f.predicted_pressure_psi ?? "-"}</td>
      <td>${f.safety_threshold_psi ?? "-"}</td>
      <td>${f.verdict}</td>
    </tr>
  `).join("");
}

/* ---------------- Init ---------------- */

(async function init() {
  await loadCurve();
  updateGauge(0, null);
})();
