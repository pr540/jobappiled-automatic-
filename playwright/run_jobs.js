/**
 * Job Bot — Playwright Runner
 * CMD: node run_jobs.js
 *
 * LinkedIn → 40 jobs | Naukri → 35 jobs | Glassdoor → 25 jobs  = 100 total
 */
const path = require('path');
const fs = require('fs');
const config = require('./config');

const LinkedIn = require('./platforms/linkedin');
const Naukri = require('./platforms/naukri');
const Glassdoor = require('./platforms/glassdoor');
const { sendNotification } = require('./notify');

function checkAuth() {
  const missing = ['linkedin', 'naukri', 'glassdoor'].filter(
    p => !fs.existsSync(path.join(config.authDir, `${p}_state.json`))
  );
  if (missing.length) {
    console.error('\n[ERROR] Missing auth sessions for:', missing.join(', '));
    console.error('→ Run first: node auth_setup.js\n');
    process.exit(1);
  }
}

function printBanner() {
  const line = '═'.repeat(52);
  console.log(`\n╔${line}╗`);
  console.log('║          JOB BOT — PLAYWRIGHT RUNNER              ║');
  console.log(`╠${line}╣`);
  console.log(`║  Candidate : ${config.name.padEnd(38)}║`);
  console.log(`║  Email     : ${config.email.padEnd(38)}║`);
  console.log(`║  Target    : ${String(config.dailyTarget).padEnd(38)}║`);
  console.log(`║  Started   : ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }).padEnd(38)}║`);
  console.log(`╚${line}╝\n`);
}

function printExpBreakdown(expCounts) {
  const entries = Object.entries(expCounts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return;

  console.log('\n┌─────────────────────────────────────────────────┐');
  console.log('│     EXPERIENCE REQUIRED (all jobs viewed)        │');
  console.log('├───────────────────────────┬─────────────────────┤');
  for (const [exp, count] of entries) {
    const bar = '█'.repeat(Math.min(count, 20));
    const label = exp.padEnd(26);
    console.log(`│ ${label}│ ${bar} ${count}`);
  }
  console.log('└───────────────────────────┴─────────────────────┘');
}

function printSummary(results) {
  const line = '─'.repeat(52);
  console.log(`\n╔${line}╗`);
  console.log('║                    FINAL SUMMARY                  ║');
  console.log(`╠${line}╣`);
  console.log(`║  LinkedIn   : ${String(results.linkedin.applied + ' applied').padEnd(15)} | ${String(results.linkedin.skipped + ' skipped').padEnd(20)}║`);
  console.log(`║  Naukri     : ${String(results.naukri.applied + ' applied').padEnd(15)} | ${String(results.naukri.skipped + ' skipped').padEnd(20)}║`);
  console.log(`║  Glassdoor  : ${String(results.glassdoor.applied + ' applied').padEnd(15)} | ${String(results.glassdoor.skipped + ' skipped').padEnd(20)}║`);
  console.log(`╠${line}╣`);
  console.log(`║  TOTAL      : ${String(results.total_applied + ' jobs applied').padEnd(36)}║`);
  const duration = Math.round((Date.now() - results._startMs) / 60000);
  console.log(`║  Duration   : ${String(duration + ' minutes').padEnd(36)}║`);
  console.log(`╚${line}╝`);

  // Experience breakdown
  const allExp = {};
  for (const p of ['linkedin', 'naukri', 'glassdoor']) {
    for (const [k, v] of Object.entries(results[p].experience_counts || {})) {
      allExp[k] = (allExp[k] || 0) + v;
    }
  }
  printExpBreakdown(allExp);
}

async function main() {
  checkAuth();
  printBanner();

  const results = {
    linkedin: { applied: 0, skipped: 0, failed: 0, experience_counts: {}, jobs: [] },
    naukri: { applied: 0, skipped: 0, failed: 0, experience_counts: {}, jobs: [] },
    glassdoor: { applied: 0, skipped: 0, failed: 0, experience_counts: {}, jobs: [] },
    total_applied: 0,
    _startMs: Date.now(),
  };

  const target = Math.min(config.dailyTarget, 100);
  const liTarget = Math.ceil(target * 0.40);   // 40 jobs from LinkedIn
  const nkTarget = Math.ceil(target * 0.35);   // 35 jobs from Naukri
  const gdTarget = target - liTarget - nkTarget; // remainder from Glassdoor

  // ── LinkedIn ─────────────────────────────────────────────────
  console.log(`\n[1/3] LinkedIn  (target: ${liTarget})`);
  console.log('─'.repeat(52));
  try {
    results.linkedin = await new LinkedIn().run(liTarget);
    results.total_applied += results.linkedin.applied;
  } catch (e) {
    console.error(`[LinkedIn] Fatal: ${e.message}`);
  }

  // ── Naukri ───────────────────────────────────────────────────
  console.log(`\n[2/3] Naukri    (target: ${nkTarget})`);
  console.log('─'.repeat(52));
  try {
    results.naukri = await new Naukri().run(nkTarget);
    results.total_applied += results.naukri.applied;
  } catch (e) {
    console.error(`[Naukri] Fatal: ${e.message}`);
  }

  // ── Glassdoor ────────────────────────────────────────────────
  const remaining = target - results.total_applied;
  if (remaining > 0) {
    const gdRun = Math.max(gdTarget, remaining);
    console.log(`\n[3/3] Glassdoor (target: ${gdRun})`);
    console.log('─'.repeat(52));
    try {
      results.glassdoor = await new Glassdoor().run(gdRun);
      results.total_applied += results.glassdoor.applied;
    } catch (e) {
      console.error(`[Glassdoor] Fatal: ${e.message}`);
    }
  } else {
    console.log('\n[3/3] Glassdoor — skipped (target already reached)');
  }

  printSummary(results);

  console.log('\n→ Sending notifications...');
  await sendNotification(results);

  console.log('\n✓ Done! Check your email for the full report.\n');
}

main().catch(err => {
  console.error('\nFatal error:', err.message);
  process.exit(1);
});
