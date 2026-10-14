// Dashboard interaction script for booster

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = String(value);
  return element.innerHTML;
}

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
    if (data.update) renderUpdateBanner(data.update);


    const tbody = document.getElementById("logsTableBody");
    if (data.recent_logs && data.recent_logs.length > 0) {
      tbody.innerHTML = data.recent_logs.map(log => `
        <tr>
          <td>${escapeHtml(log.time)}</td>
          <td><b>${escapeHtml(log.method)}</b></td>
          <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(log.path)}</td>
          <td><span style="color: ${log.status_code < 400 ? 'var(--green)' : '#f87171'}">${log.status_code}</span></td>
          <td style="color: var(--accent); font-weight: bold;">${log.duration_ms} ms</td>
          <td><span class="badge ${log.cached ? 'badge-hit' : 'badge-miss'}">${log.cached ? '⚡ HIT' : 'MISS'}</span></td>
          <td>${formatBytes(log.size_bytes)}</td>
          <td>${escapeHtml(log.compression)}</td>
        </tr>
      `).join("");
    } else {
      tbody.replaceChildren();
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
      headers: { "Content-Type": "application/json", "X-Go-Fast-Admin": "1" },
      body: JSON.stringify({ url: url })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Update failed");
    alert("🚀 Speed Accelerator is now boosting: " + data.target_url);
    fetchStats();
  } catch (err) {
    alert("Error updating target: " + err);
  }
}

async function autoDetect() {
  const btn = document.querySelector('[onclick="autoDetect()"]');
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
    const res = await fetch("/api/clear-cache", { method: "POST", headers: { "X-Go-Fast-Admin": "1" } });
    if (!res.ok) throw new Error("Cache clear failed");
    alert("🗑️ In-memory cache cleared successfully!");
    fetchStats();
  } catch (err) {
    alert("Failed to clear cache: " + err);
  }
}

function renderUpdateBanner(info) {
  const banner = document.getElementById("updateBanner");
  if (!banner || !info || info.update_type === "none") {
    if (banner) banner.style.display = "none";
    return;
  }
  banner.style.display = "block";
  const title = document.getElementById("updateTitle");
  const desc = document.getElementById("updateDesc");
  const action = document.getElementById("updateAction");

  if (info.update_type === "patch") {
    if (info.auto_applied) {
      title.textContent = "✅ Bugfix Patch Auto-Applied";
      desc.textContent = `Version ${info.latest_version} bug fixes were automatically installed.`;
      action.innerHTML = "";
    } else {
      title.textContent = "⚡ Bugfix Patch Available";
      desc.textContent = `A quick patch ${info.latest_version} is available.`;
      action.innerHTML = `<button onclick="applyUpdate()" style="padding: 6px 12px; font-size: 12px;">Update Now</button>`;
    }
  } else {
    title.textContent = `🚀 Upgrade Available: v${info.latest_version}`;
    desc.textContent = `Run 'pip install --upgrade booster' or view release notes.`;
    action.innerHTML = info.release_url ? `<a href="${escapeHtml(info.release_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent); font-size: 13px; text-decoration: underline;">View Release</a>` : "";
  }
}

async function applyUpdate() {
  try {
    const res = await fetch("/api/apply-update", {
      method: "POST",
      headers: { "X-Go-Fast-Admin": "1" }
    });
    const data = await res.json();
    if (data.success) {
      alert("Update successfully installed!");
      fetchStats();
    } else {
      alert("Please update manually: pip install --upgrade booster");
    }
  } catch (err) {
    alert("Update request failed: " + err);
  }
}

// Start auto-refresh
setInterval(fetchStats, 1500);
fetchStats();
