const API = "";

async function fetchStats() {
  const res = await fetch(`${API}/api/dashboard/stats`);
  const d = await res.json();
  document.getElementById("total_jobs").textContent = d.total_jobs_scanned ?? "—";
  document.getElementById("jobs_applied").textContent = d.jobs_applied ?? "—";
  document.getElementById("interview_calls").textContent = d.interview_calls ?? "—";
  document.getElementById("rejected").textContent = d.rejected ?? "—";
  document.getElementById("pending").textContent = d.pending ?? "—";
  document.getElementById("avg_ats").textContent = d.avg_ats_score ? d.avg_ats_score + "%" : "—";
  document.getElementById("recruiters_contacted").textContent = d.recruiters_contacted ?? "—";
  document.getElementById("recruiter_replies").textContent = d.recruiter_replies ?? "—";
}

async function fetchRecentJobs() {
  const res = await fetch(`${API}/api/dashboard/recent-jobs`);
  const jobs = await res.json();
  const tbody = document.getElementById("jobs-tbody");
  tbody.innerHTML = jobs.map(j => `
    <tr>
      <td><span class="platform-badge ${j.platform}">${j.platform}</span></td>
      <td><a href="${j.job_url || '#'}" target="_blank" style="color:var(--accent)">${j.title}</a></td>
      <td>${j.company || "—"}</td>
      <td>${j.location || "—"}</td>
      <td>${j.ats_score ? j.ats_score.toFixed(1) + "%" : "—"}</td>
      <td><span class="badge ${j.status}">${j.status}</span></td>
    </tr>
  `).join("");
}

async function fetchOutreach() {
  const res = await fetch(`${API}/api/outreach/`);
  const rows = await res.json();
  const tbody = document.getElementById("outreach-tbody");
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.name || "—"}</td>
      <td>${r.company || "—"}</td>
      <td>${r.connection_sent ? "✓" : "—"}</td>
      <td>${r.replied ? "✓" : "—"}</td>
      <td>${r.replied ? "" : `<button onclick="markReplied(${r.id})" style="padding:4px 10px;font-size:0.75rem">Mark Replied</button>`}</td>
    </tr>
  `).join("");
}

async function markReplied(id) {
  await fetch(`${API}/api/outreach/${id}/replied`, { method: "PATCH" });
  fetchOutreach();
}

function setStatus(msg, ok = true) {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.style.color = ok ? "var(--green)" : "var(--red)";
  setTimeout(() => el.textContent = "", 4000);
}

async function triggerSearch() {
  setStatus("Starting job search...");
  const res = await fetch(`${API}/api/jobs/trigger-search`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Started");
}

async function triggerApply() {
  setStatus("Starting auto-apply...");
  const res = await fetch(`${API}/api/jobs/trigger-apply`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Started");
}

async function triggerOutreach() {
  setStatus("Starting recruiter outreach...");
  const res = await fetch(`${API}/api/outreach/trigger`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Started");
}

async function generateReport() {
  const res = await fetch(`${API}/api/reports/generate`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Report generated");
}

async function uploadResume() {
  const file = document.getElementById("resume-file").files[0];
  if (!file) { setStatus("Select a PDF first", false); return; }
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/api/resume/upload`, { method: "POST", body: form });
  const d = await res.json();
  document.getElementById("upload-result").textContent =
    d.message ? `${d.message} — Skills: ${(d.skills_found || []).join(", ")}` : d.error;
}

async function checkATS() {
  const jd = document.getElementById("jd-text").value.trim();
  if (!jd) return;
  const res = await fetch(`${API}/api/resume/ats-score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jd }),
  });
  const d = await res.json();
  const el = document.getElementById("ats-result");
  el.textContent = `ATS Score: ${d.ats_score}% — ${d.pass ? "PASS ✓ (above threshold)" : "FAIL ✗ (below threshold)"}`;
  el.style.color = d.pass ? "var(--green)" : "var(--red)";
}

function refreshAll() {
  fetchStats();
  fetchRecentJobs();
  fetchOutreach();
}

refreshAll();
setInterval(refreshAll, 30000);
