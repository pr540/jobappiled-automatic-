const config = require('./config');

/**
 * Email via Gmail SMTP (needs SMTP_PASS = Gmail App Password)
 * Mobile push via ntfy.sh (free, needs NTFY_TOPIC set)
 */

async function sendEmail(subject, html) {
  if (!config.smtpPass) return;

  try {
    const nodemailer = require('nodemailer');
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: { user: config.smtpUser, pass: config.smtpPass },
    });

    await transporter.sendMail({
      from: `Job Bot <${config.smtpUser}>`,
      to: config.notifyEmail,
      subject,
      html,
    });
    console.log(`\n📧 Email sent to ${config.notifyEmail}`);
  } catch (e) {
    console.log(`\n[Notify] Email failed: ${e.message}`);
  }
}

async function sendMobilePush(title, body) {
  if (!config.ntfyTopic) return;

  try {
    const https = require('https');
    const data = JSON.stringify({ topic: config.ntfyTopic, title, message: body, priority: 3 });
    await new Promise((resolve, reject) => {
      const req = https.request(
        { hostname: 'ntfy.sh', path: '/', method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } },
        res => { res.on('data', () => {}); res.on('end', resolve); }
      );
      req.on('error', reject);
      req.write(data);
      req.end();
    });
    console.log(`📱 Mobile push sent (ntfy topic: ${config.ntfyTopic})`);
  } catch (e) {
    console.log(`[Notify] Push failed: ${e.message}`);
  }
}

function buildEmailHtml(results) {
  const rows = [...results.linkedin.jobs, ...results.naukri.jobs, ...results.glassdoor.jobs]
    .map(j => `<tr>
      <td>${j.platform}</td>
      <td><a href="${j.url}">${j.title}</a></td>
      <td>${j.company}</td>
      <td>${j.location}</td>
      <td>${j.experience || '-'}</td>
    </tr>`)
    .join('');

  const expAll = mergeExpCounts(results);
  const expRows = Object.entries(expAll)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${k}</td><td>${v} jobs</td></tr>`)
    .join('');

  return `
<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
<h2>🤖 Job Bot Report — ${new Date().toLocaleDateString('en-IN')}</h2>
<table border="1" cellpadding="8" style="border-collapse:collapse;width:100%">
  <tr style="background:#2563eb;color:white">
    <th>Platform</th><th>Applied</th><th>Skipped</th>
  </tr>
  <tr><td>LinkedIn</td><td>${results.linkedin.applied}</td><td>${results.linkedin.skipped}</td></tr>
  <tr><td>Naukri</td><td>${results.naukri.applied}</td><td>${results.naukri.skipped}</td></tr>
  <tr><td>Glassdoor</td><td>${results.glassdoor.applied}</td><td>${results.glassdoor.skipped}</td></tr>
  <tr style="font-weight:bold;background:#f0fdf4">
    <td>TOTAL</td><td>${results.total_applied}</td><td>-</td>
  </tr>
</table>

<h3>Experience Required (jobs viewed)</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr style="background:#f3f4f6"><th>Experience</th><th>Count</th></tr>
  ${expRows || '<tr><td colspan="2">N/A</td></tr>'}
</table>

<h3>Applied Jobs</h3>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
  <tr style="background:#f3f4f6">
    <th>Platform</th><th>Title</th><th>Company</th><th>Location</th><th>Experience</th>
  </tr>
  ${rows || '<tr><td colspan="5">No applications this run</td></tr>'}
</table>
<p style="color:#6b7280;font-size:12px">Run at: ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST</p>
</body></html>`;
}

function mergeExpCounts(results) {
  const merged = {};
  for (const p of ['linkedin', 'naukri', 'glassdoor']) {
    for (const [k, v] of Object.entries(results[p].experience_counts || {})) {
      merged[k] = (merged[k] || 0) + v;
    }
  }
  return merged;
}

async function sendNotification(results) {
  const subject = `Job Bot: ${results.total_applied} applications sent — ${new Date().toLocaleDateString('en-IN')}`;
  const pushBody = [
    `Applied: ${results.total_applied} jobs`,
    `LinkedIn: ${results.linkedin.applied} | Naukri: ${results.naukri.applied} | Glassdoor: ${results.glassdoor.applied}`,
    `Time: ${new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' })} IST`,
  ].join('\n');

  await Promise.all([
    sendEmail(subject, buildEmailHtml(results)),
    sendMobilePush('Job Bot Done!', pushBody),
  ]);
}

module.exports = { sendNotification };
