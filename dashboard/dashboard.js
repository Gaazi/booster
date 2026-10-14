// Dashboard interaction script for go_fast

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("statHitRatio").textContent = data.hit_ratio_percent + "%";
    document.getElementById("statSavedBytes").textContent =
      formatBytes(data.bandwidth_saved_bytes) + ` (${data.bandwidth_saved_percent}%)`;
    document.getElementById("statRequests").textContent = data.total_requests;
    document.getElementById("statCacheCount").textContent = data.cache_count;
    document.getElementById("targetBadge").textContent = "Boosting: " + data.target_url;

    const tbody = document.getElementById("logsTableBody");
    if (data.recent_logs && data.recent_logs.length > 0) {
      tbody.innerHTML = data.recent_logs.map(log => `
        <tr>
          <td>${log.time}</td>
          <td><b>${log.method}</b></td>
          <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${log.path}</td>
          <td><span style="color: ${log.status_code < 400 ? 'var(--green)' : '#f87171'}">${log.status_code}</span></td>
          <td style="color: var(--accent); font-weight: bold;">${log.duration_ms} ms</td>
          <td><span class="badge ${log.cached ? 'badge-hit' : 'badge-miss'}">${log.cached ? '⚡ HIT' : 'MISS'}</span></td>
          <td>${formatBytes(log.size_bytes)}</td>
          <td>${log.compression}</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to fetch stats:", err);
  }
}

async function applyTarget() {
  const url = document.getElementById("targetUrl").value.trim();
  if (!url) return alert("Please enter a valid URL");
  try {
    const res = await fetch("/api/set-target", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url })
    });
    const data = await res.json();
    alert("🚀 Speed Accelerator is now boosting: " + data.target_url);
    fetchStats();
  } catch (err) {
    alert("Error updating target: " + err);
  }
}

async function autoDetect() {
  const btn = event.target;
  btn.textContent = "Scanning ports...";
  try {
    const res = await fetch("/api/detect-local");
    const data = await res.json();
    if (data.found_url) {
      document.getElementById("targetUrl").value = data.found_url;
      alert("✨ Auto-detected running local server: " + data.found_url);
      applyTarget();
    } else {
      alert("No running server found on ports 8000, 3000, 8080, 5000. Please enter your URL manually.");
    }
  } catch (err) {
    alert("Auto-detect failed: " + err);
  } finally {
    btn.textContent = "🔍 Auto-Detect Local Port";
  }
}

async function clearCache() {
  try {
    await fetch("/api/clear-cache", { method: "POST" });
    alert("🗑️ In-memory cache cleared successfully!");
    fetchStats();
  } catch (err) {
    alert("Failed to clear cache: " + err);
  }
}

// Start auto-refresh
setInterval(fetchStats, 1500);
fetchStats();
