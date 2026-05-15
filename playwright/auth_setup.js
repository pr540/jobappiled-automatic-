/**
 * One-time Google login setup.
 * Run: node auth_setup.js
 * Browser opens, sign in with Google, press ENTER to save session.
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const readline = require('readline');
const config = require('./config');

function waitForEnter(prompt) {
  return new Promise(resolve => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, () => { rl.close(); resolve(); });
  });
}

async function setupPlatform(name, loginUrl, loggedInSelector, waitMs = 90000) {
  console.log(`\n${'='.repeat(50)}`);
  console.log(`[${name}] Opening browser...`);
  console.log(`  → Sign in with Google: ${config.email}`);
  console.log(`  → Then press ENTER here to save session`);

  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  await page.goto(loginUrl, { timeout: 30000 });

  // Wait for user to log in manually, or detect it automatically
  try {
    await page.waitForSelector(loggedInSelector, { timeout: waitMs });
    console.log(`[${name}] Login detected automatically ✓`);
  } catch {
    // Manual confirmation fallback
    await waitForEnter(`[${name}] Press ENTER once you are logged in... `);
  }

  fs.mkdirSync(config.authDir, { recursive: true });
  const authFile = path.join(config.authDir, `${name.toLowerCase()}_state.json`);
  await context.storageState({ path: authFile });
  console.log(`[${name}] Session saved → ${authFile}`);

  await browser.close();
}

async function main() {
  console.log('╔══════════════════════════════════════════════════╗');
  console.log('║         JOB BOT — ONE-TIME AUTH SETUP            ║');
  console.log('╠══════════════════════════════════════════════════╣');
  console.log(`║  Email: ${config.email.padEnd(41)}║`);
  console.log('║  Sign in with Google on each platform below.     ║');
  console.log('╚══════════════════════════════════════════════════╝');

  await setupPlatform(
    'LinkedIn',
    'https://www.linkedin.com/login',
    '.global-nav__me-photo, .feed-identity-module, nav.global-nav'
  );

  await setupPlatform(
    'Naukri',
    'https://www.naukri.com/nlogin/login',
    '.nI-gNb-drawer__icon, .nI-gNb-info, .user-name'
  );

  await setupPlatform(
    'Glassdoor',
    'https://www.glassdoor.co.in/profile/login_input.htm',
    '[data-test="user-menu"], .dropdown-avatar, .userMenu'
  );

  console.log('\n✓ All platforms authenticated!');
  console.log('→ Now run: node run_jobs.js\n');
}

main().catch(err => {
  console.error('Auth setup failed:', err.message);
  process.exit(1);
});
