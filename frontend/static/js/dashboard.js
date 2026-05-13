const API = "";

const SAMPLE_JD = `We are looking for a DevOps Engineer with 1–3 years of hands-on experience.

Requirements:
- Strong experience with AWS services: EC2, S3, VPC, IAM, EKS, CloudWatch, ELB, Auto Scaling
- Proficiency in Terraform for infrastructure as code
- Container orchestration using Kubernetes and Docker
- Building and maintaining CI/CD pipelines with Jenkins and GitHub Actions
- Linux administration and Bash scripting
- Monitoring and alerting using Prometheus and Grafana
- Understanding of WAF, Route53, and network security

Good to have:
- Python scripting
- Experience with Helm charts
- Knowledge of GitOps practices

Location: Remote / Hyderabad / Bangalore
Experience: 1–3 Years`;

async function fetchStats() {
  try {
    const res = await fetch(`${API}/api/dashboard/stats`);
    const d = await res.json();
    document.getElementById("total_jobs").textContent = d.total_jobs_scanned ?? "0";
    document.getElementById("jobs_applied").textContent = d.jobs_applied ?? "0";
    document.getElementById("interview_calls").textContent = d.interview_calls ?? "0";
    document.getElementById("rejected").textContent = d.rejected ?? "0";
    document.getElementById("pending").textContent = d.pending ?? "0";
    document.getElementById("avg_ats").textContent = d.avg_ats_score ? d.avg_ats_score + "%" : "0%";
    document.getElementById("recruiters_contacted").textContent = d.recruiters_contacted ?? "0";
    document.getElementById("recruiter_replies").textContent = d.recruiter_replies ?? "0";
  } catch (e) { console.error("Stats fetch failed", e); }
}

async function fetchRecentJobs() {
  try {
    const res = await fetch(`${API}/api/dashboard/recent-jobs`);
    const jobs = await res.json();
    const tbody = document.getElementById("jobs-tbody");
    if (!jobs.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">No jobs yet — click "Start Job Search" to begin</td></tr>`;
      return;
    }
    tbody.innerHTML = jobs.map(j => `
      <tr>
        <td><span class="platform-badge ${j.platform}">${j.platform}</span></td>
        <td><a href="${j.job_url || '#'}" target="_blank" style="color:var(--accent)">${j.title}</a></td>
        <td>${j.company || "—"}</td>
        <td>${j.location || "—"}</td>
        <td><span style="color:${j.ats_score >= 75 ? 'var(--green)' : j.ats_score >= 50 ? '#f0883e' : 'var(--red)'}">${j.ats_score ? j.ats_score.toFixed(1) + "%" : "—"}</span></td>
        <td><span class="badge ${j.status}">${j.status}</span></td>
      </tr>
    `).join("");
  } catch (e) { console.error("Jobs fetch failed", e); }
}

async function fetchOutreach() {
  try {
    const res = await fetch(`${API}/api/outreach/`);
    const rows = await res.json();
    const tbody = document.getElementById("outreach-tbody");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:24px">No outreach yet</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.name || "—"}</td>
        <td>${r.company || "—"}</td>
        <td style="color:${r.connection_sent ? 'var(--green)' : 'var(--muted)'}">${r.connection_sent ? "✓ Sent" : "—"}</td>
        <td style="color:${r.replied ? 'var(--green)' : 'var(--muted)'}">${r.replied ? "✓ Replied" : "—"}</td>
        <td>${r.replied ? "" : `<button onclick="markReplied(${r.id})" style="padding:4px 10px;font-size:0.75rem">Mark Replied</button>`}</td>
      </tr>
    `).join("");
  } catch (e) { console.error("Outreach fetch failed", e); }
}

async function markReplied(id) {
  await fetch(`${API}/api/outreach/${id}/replied`, { method: "PATCH" });
  fetchOutreach();
}

function setStatus(msg, ok = true) {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.style.color = ok ? "var(--green)" : "var(--red)";
  setTimeout(() => el.textContent = "", 5000);
}

async function triggerSearch() {
  setStatus("Job search started in background...");
  const res = await fetch(`${API}/api/jobs/trigger-search`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Started");
}

async function triggerApply() {
  setStatus("Auto-apply started in background...");
  const res = await fetch(`${API}/api/jobs/trigger-apply`, { method: "POST" });
  const d = await res.json();
  setStatus(d.message || "Started");
}

async function triggerOutreach() {
  setStatus("Recruiter outreach started...");
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
  if (!file) { setStatus("Select a PDF file first", false); return; }
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/api/resume/upload`, { method: "POST", body: form });
  const d = await res.json();
  const el = document.getElementById("upload-result");
  if (d.error) {
    el.textContent = "Error: " + d.error;
    el.style.color = "var(--red)";
    return;
  }
  el.style.color = "var(--green)";
  el.textContent = `Resume uploaded — ${d.skills_found?.length || 0} skills detected`;
  showResumeSkills(d.skills_found || []);
}

async function checkResumeStatus() {
  const res = await fetch(`${API}/api/resume/parse`);
  const d = await res.json();
  const el = document.getElementById("upload-result");
  if (d.error || !d.skills || !d.skills.length) {
    el.textContent = "No resume loaded — please upload your PDF.";
    el.style.color = "var(--red)";
    return;
  }
  el.style.color = "var(--green)";
  el.textContent = `Resume active: ${d.name} | ${d.skills.length} skills found | ${d.text_length} chars`;
  showResumeSkills(d.skills);
}

function showResumeSkills(skills) {
  const box = document.getElementById("resume-skills-box");
  const chips = document.getElementById("resume-skill-chips");
  if (!skills.length) { box.style.display = "none"; return; }
  box.style.display = "block";
  chips.innerHTML = skills.map(s => `<span class="chip chip-blue">${s}</span>`).join("");
}

function loadSampleJD() {
  document.getElementById("jd-text").value = SAMPLE_JD;
  document.getElementById("ats-error").textContent = "";
}

async function checkATS() {
  const jd = document.getElementById("jd-text").value.trim();
  const errEl = document.getElementById("ats-error");
  const resBox = document.getElementById("ats-result-box");
  errEl.textContent = "";
  resBox.style.display = "none";

  if (!jd) {
    errEl.textContent = "Please paste a job description first. Use \"Try Sample JD\" to test.";
    return;
  }
  if (jd.length < 80) {
    errEl.textContent = `Too short (${jd.length} chars). Paste the full job description — at least 3–4 lines.`;
    return;
  }

  const btn = document.querySelector(".ats-controls button");
  btn.textContent = "Checking...";
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/resume/ats-score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_description: jd }),
    });
    const d = await res.json();

    if (!res.ok) {
      errEl.textContent = d.error || "Error checking score.";
      if (d.resume_missing) errEl.textContent += " Upload your resume PDF above first.";
      return;
    }

    const score = d.ats_score;
    const pass = d.pass;
    const color = score >= 75 ? "var(--green)" : score >= 50 ? "#f0883e" : "var(--red)";

    // Score bar
    const bar = document.getElementById("ats-score-bar");
    bar.style.width = score + "%";
    bar.style.background = color;

    // Label
    const label = document.getElementById("ats-score-label");
    label.innerHTML = `<strong style="color:${color};font-size:1.5rem">${score}%</strong>
      &nbsp;—&nbsp;
      <span style="color:${color}">${pass ? "PASS ✓ You will be shortlisted" : score >= 50 ? "BORDERLINE — optimize resume" : "FAIL ✗ Below threshold"}</span>
      &nbsp;&nbsp;<small style="color:var(--muted)">Threshold: ${d.threshold}%</small>`;

    // Matched chips
    const matched = d.matched_skills || [];
    const missing = d.missing_skills || [];
    document.getElementById("matched-chips").innerHTML =
      matched.length ? matched.map(s => `<span class="chip chip-green">${s}</span>`).join("") : `<span style="color:var(--muted);font-size:0.8rem">None matched</span>`;
    document.getElementById("missing-chips").innerHTML =
      missing.length ? missing.map(s => `<span class="chip chip-red">${s}</span>`).join("") : `<span style="color:var(--green);font-size:0.8rem">All skills present!</span>`;

    resBox.style.display = "block";

  } catch (e) {
    errEl.textContent = "Request failed: " + e.message;
  } finally {
    btn.textContent = "📊 Check ATS Score";
    btn.disabled = false;
  }
}

function refreshAll() {
  fetchStats();
  fetchRecentJobs();
  fetchOutreach();
}

refreshAll();
setInterval(refreshAll, 30000);
