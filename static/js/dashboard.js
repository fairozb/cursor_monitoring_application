/* Live dashboard: poll authenticated metrics API every 10s (Chart.js). */
(function () {
  const cfg = window.INFRA_MONITOR || {};
  const REFRESH_MS = cfg.refreshMs || 10000;
  const metricsUrl = cfg.metricsUrl || "/api/servers/metrics";

  let inFlight = false;
  let charts = {};
  let history = {
    labels: [],
    cpu: [],
    mem: [],
    disk: [],
    up: [],
    down: [],
  };
  const MAX_POINTS = 12;

  function thresholdClass(percent) {
    if (percent == null || Number.isNaN(percent)) return "threshold-unknown";
    if (percent >= 85) return "threshold-red";
    if (percent >= 70) return "threshold-orange";
    return "threshold-green";
  }

  function thresholdLabel(percent) {
    if (percent == null || Number.isNaN(percent)) return "n/a";
    if (percent >= 85) return "High";
    if (percent >= 70) return "Warn";
    return "OK";
  }

  function lineColor(percent) {
    if (percent >= 85) return "#e35d6a";
    if (percent >= 70) return "#f2cc0c";
    return "#3dd68c";
  }

  function ensureCharts() {
    const common = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: "#7f8a9a", maxRotation: 0, autoSkip: true, maxTicksLimit: 6 },
          grid: { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          min: 0,
          ticks: { color: "#7f8a9a" },
          grid: { color: "rgba(255,255,255,0.06)" },
        },
      },
    };

    if (!charts.cpu) {
      charts.cpu = new Chart(document.getElementById("chart-cpu"), {
        type: "line",
        data: {
          labels: history.labels,
          datasets: [
            {
              data: history.cpu,
              borderColor: "#3d7eff",
              backgroundColor: "rgba(61,126,255,0.15)",
              fill: true,
              tension: 0.35,
              pointRadius: 0,
            },
          ],
        },
        options: { ...common, scales: { ...common.scales, y: { ...common.scales.y, max: 100 } } },
      });
    }
    if (!charts.mem) {
      charts.mem = new Chart(document.getElementById("chart-mem"), {
        type: "line",
        data: {
          labels: history.labels,
          datasets: [
            {
              data: history.mem,
              borderColor: "#3dd68c",
              backgroundColor: "rgba(61,214,140,0.12)",
              fill: true,
              tension: 0.35,
              pointRadius: 0,
            },
          ],
        },
        options: { ...common, scales: { ...common.scales, y: { ...common.scales.y, max: 100 } } },
      });
    }
    if (!charts.disk) {
      charts.disk = new Chart(document.getElementById("chart-disk"), {
        type: "doughnut",
        data: {
          labels: ["Used", "Available"],
          datasets: [
            {
              data: [0, 1],
              backgroundColor: ["#3d7eff", "rgba(255,255,255,0.08)"],
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          cutout: "68%",
        },
      });
    }
    if (!charts.net) {
      charts.net = new Chart(document.getElementById("chart-net"), {
        type: "line",
        data: {
          labels: history.labels,
          datasets: [
            {
              label: "Up",
              data: history.up,
              borderColor: "#3d7eff",
              tension: 0.35,
              pointRadius: 0,
            },
            {
              label: "Down",
              data: history.down,
              borderColor: "#3dd68c",
              tension: 0.35,
              pointRadius: 0,
            },
          ],
        },
        options: {
          ...common,
          plugins: {
            legend: {
              display: true,
              labels: { color: "#7f8a9a", boxWidth: 10 },
            },
          },
        },
      });
    }
  }

  function pushHistory(label, metrics) {
    history.labels.push(label);
    history.cpu.push(metrics.cpu_percent ?? null);
    history.mem.push(metrics.memory ? metrics.memory.percent : null);
    history.disk.push(metrics.disk ? metrics.disk.percent : null);
    history.up.push(metrics.network ? metrics.network.bytes_sent_per_sec : null);
    history.down.push(metrics.network ? metrics.network.bytes_recv_per_sec : null);
    if (history.labels.length > MAX_POINTS) {
      Object.keys(history).forEach((k) => history[k].shift());
    }
  }

  function updateThreshold(elId, percent) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = thresholdLabel(percent);
    el.className = "threshold-pill " + thresholdClass(percent);
  }

  function renderPorts(ports) {
    const body = document.getElementById("ports-body");
    const count = document.getElementById("ports-count");
    if (!body) return;
    count.textContent = String((ports || []).length);
    if (!ports || !ports.length) {
      body.innerHTML = '<tr><td colspan="3" class="text-muted">No listening ports visible</td></tr>';
      return;
    }
    body.innerHTML = ports
      .slice(0, 40)
      .map(
        (p) =>
          `<tr><td>${p.port}</td><td>${p.proto}</td><td>${p.status || "LISTEN"}</td></tr>`
      )
      .join("");
  }

  function renderServersTable(servers) {
    const body = document.getElementById("servers-body");
    if (!body) return;
    if (!servers.length) {
      body.innerHTML = '<tr><td colspan="5" class="text-muted">No servers</td></tr>';
      return;
    }
    const esc = (value) =>
      String(value ?? "").replace(/[&<>"']/g, (ch) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
      );
    body.innerHTML = servers
      .map((s) => {
        const statusClass =
          s.status === "online" ? "status-pill--online" : "status-pill--offline";
        const cpu = s.cpu_percent != null ? s.cpu_percent + "%" : "—";
        const mem = s.memory ? s.memory.percent + "%" : "—";
        const sim = s.simulated ? ' <span class="metric-card__tag">Simulated</span>' : "";
        const err = s.error ? `<div class="metric-card__hint">${esc(s.error)}</div>` : "";
        const href = s.server_id ? `/servers/${s.server_id}` : "#";
        return `<tr>
          <td><a class="server-link" href="${href}">${esc(s.name || "—")}</a>${sim}${err}</td>
          <td>${esc(s.server_type || "—")}</td>
          <td><span class="status-pill ${statusClass}">${esc(s.status || "—")}</span></td>
          <td>${cpu}</td>
          <td>${mem}</td>
        </tr>`;
      })
      .join("");
  }

  function applyMetrics(payload) {
    const servers = payload.servers || (payload.server_id ? [payload] : []);
    const local =
      (cfg.focusId && servers.find((s) => s.server_id === cfg.focusId)) ||
      servers.find((s) => s.server_type === "local") ||
      servers[0] ||
      null;
    if (!local) return;

    const online = local.status === "online";
    const pill = document.getElementById("status-pill");
    const dot = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");
    pill.textContent = online ? "Online" : "Offline";
    pill.className = "status-pill " + (online ? "status-pill--online" : "status-pill--offline");
    dot.className = "status-dot " + (online ? "status-dot--online" : "status-dot--offline");
    statusText.textContent = online ? "Online" : "Offline";
    const simBadge = document.getElementById("sim-badge");
    if (simBadge) simBadge.hidden = !local.simulated;

    document.getElementById("meta-name").textContent = local.name || "—";
    document.getElementById("meta-hostname").textContent = local.hostname || "—";
    document.getElementById("meta-ip").textContent = local.ip_address || "—";
    document.getElementById("meta-os").textContent =
      (local.os && local.os.pretty) || "—";
    document.getElementById("meta-uptime").textContent = local.uptime_human || "—";
    document.getElementById("meta-cores").textContent =
      local.cpu_count != null ? String(local.cpu_count) : "—";
    if (local.load_average) {
      document.getElementById("meta-load").textContent = [
        local.load_average["1m"],
        local.load_average["5m"],
        local.load_average["15m"],
      ].join(" / ");
    } else {
      document.getElementById("meta-load").textContent = "—";
    }

    const err = document.getElementById("meta-error");
    if (local.error) {
      err.hidden = false;
      err.textContent = local.error;
    } else {
      err.hidden = true;
      err.textContent = "";
    }

    const cpu = local.cpu_percent;
    document.getElementById("cpu-value").textContent =
      cpu != null ? cpu.toFixed(1) + "%" : "—";
    document.getElementById("cpu-hint").textContent =
      local.cpu_count != null ? local.cpu_count + " logical cores" : "Utilization";
    updateThreshold("cpu-threshold", cpu);

    if (local.memory) {
      document.getElementById("mem-value").textContent = local.memory.percent.toFixed(1) + "%";
      document.getElementById("mem-hint").textContent =
        local.memory.used_human +
        " used · " +
        local.memory.available_human +
        " avail · " +
        local.memory.total_human +
        " total";
      updateThreshold("mem-threshold", local.memory.percent);
    }

    if (local.disk) {
      document.getElementById("disk-value").textContent = local.disk.percent.toFixed(1) + "%";
      document.getElementById("disk-hint").textContent =
        local.disk.used_human +
        " used · " +
        local.disk.available_human +
        " avail · " +
        local.disk.total_human +
        " total";
      updateThreshold("disk-threshold", local.disk.percent);
      if (charts.disk) {
        charts.disk.data.datasets[0].data = [local.disk.used, local.disk.available];
        charts.disk.data.datasets[0].backgroundColor = [
          lineColor(local.disk.percent),
          "rgba(255,255,255,0.08)",
        ];
        charts.disk.update("none");
      }
    }

    if (local.network) {
      document.getElementById("net-value").textContent =
        "↑ " + local.network.upload + "  ↓ " + local.network.download;
      document.getElementById("net-hint").textContent =
        "Total sent " +
        (local.network.bytes_sent || 0).toLocaleString() +
        " B · recv " +
        (local.network.bytes_recv || 0).toLocaleString() +
        " B";
    }

    const label = new Date().toLocaleTimeString();
    pushHistory(label, local);
    ensureCharts();
    charts.cpu.data.labels = history.labels;
    charts.cpu.data.datasets[0].data = history.cpu;
    charts.cpu.data.datasets[0].borderColor = lineColor(cpu || 0);
    charts.cpu.update("none");
    charts.mem.data.labels = history.labels;
    charts.mem.data.datasets[0].data = history.mem;
    charts.mem.data.datasets[0].borderColor = lineColor(
      local.memory ? local.memory.percent : 0
    );
    charts.mem.update("none");
    charts.net.data.labels = history.labels;
    charts.net.data.datasets[0].data = history.up;
    charts.net.data.datasets[1].data = history.down;
    charts.net.update("none");

    renderPorts(local.listening_ports || []);
    renderServersTable(servers);

    document.getElementById("last-updated").textContent =
      "Last updated: " + (local.collected_at || label);
  }

  async function refresh() {
    if (inFlight) return;
    inFlight = true;
    try {
      const res = await fetch(metricsUrl, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (res.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("metrics request failed");
      const data = await res.json();
      applyMetrics(data);
    } catch (err) {
      const errEl = document.getElementById("meta-error");
      if (errEl) {
        errEl.hidden = false;
        errEl.textContent = "Unable to refresh metrics";
      }
    } finally {
      inFlight = false;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    ensureCharts();
    const label = document.getElementById("refresh-interval-label");
    if (label) label.textContent = String(REFRESH_MS / 1000);
    const btn = document.getElementById("btn-refresh");
    if (btn) btn.addEventListener("click", refresh);
    refresh();
    setInterval(refresh, REFRESH_MS);
  });

  // Exported for simple unit-style checks in docs/tests
  window.__INFRA_REFRESH_MS = REFRESH_MS;
})();
