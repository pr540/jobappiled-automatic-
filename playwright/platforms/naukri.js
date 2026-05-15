const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const config = require('../config');

const DELAY = (min, max) => new Promise(r => setTimeout(r, min + Math.random() * (max - min)));
const BASE = 'https://www.naukri.com';

// Extract minimum years from strings like "9-14 Yrs", "1-3 Yrs", "2 Years"
function parseExpMin(expStr) {
  if (!expStr) return 0;
  const m = expStr.match(/(\d+)/);
  return m ? parseInt(m[1]) : 0;
}

class Naukri {
  constructor() {
    this.authFile = path.join(config.authDir, 'naukri_state.json');
    this.browser = null;
    this.context = null;
    this.page = null;
  }

  async init() {
    const storageState = fs.existsSync(this.authFile) ? this.authFile : undefined;
    this.browser = await chromium.launch({
      headless: config.headless,
      slowMo: 40,
      args: ['--disable-blink-features=AutomationControlled'],
    });
    this.context = await this.browser.newContext({
      storageState,
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    this.page = await this.context.newPage();
  }

  async isLoggedIn() {
    try {
      await this.page.goto(BASE, { timeout: 20000, waitUntil: 'domcontentloaded' });
      await DELAY(2000, 3000);
      await this.page.waitForSelector(
        '.nI-gNb-drawer__icon, .nI-gNb-info, .user-name, [data-ga-track="user_icon"]',
        { timeout: 6000 }
      );
      return true;
    } catch {
      try {
        const url = this.page.url();
        return url.includes('naukri.com') && !url.includes('login') && !url.includes('nlogin');
      } catch {
        return false;
      }
    }
  }

  async searchJobs(role, location) {
    const roleSlug = role.toLowerCase().replace(/\s+/g, '-');
    const locSlug = location.toLowerCase().replace(/\s+/g, '-');
    const url = `${BASE}/${roleSlug}-jobs-in-${locSlug}?experience=0,${config.maxExpYears}&jobAge=7&jobtype=1`;

    try {
      await this.page.goto(url, { timeout: 30000, waitUntil: 'domcontentloaded' });
      await DELAY(2500, 4000);
    } catch {
      return [];
    }

    const content = await this.page.content();
    if (content.includes('no jobs') || content.includes('0 jobs found')) {
      const fallback = `${BASE}/jobs?q=${encodeURIComponent(role)}&l=${encodeURIComponent(location)}&experience=1,3`;
      try {
        await this.page.goto(fallback, { timeout: 30000, waitUntil: 'domcontentloaded' });
        await DELAY(2500, 4000);
      } catch {
        return [];
      }
    }

    // Scroll to load cards
    for (let i = 0; i < 5; i++) {
      await this.page.evaluate('window.scrollBy(0, 700)');
      await DELAY(400, 700);
    }

    const cards = await this.page.$$('article.jobTuple, div.srp-jobtuple-wrapper, div[class*="jobTuple"], .cust-job-tuple');
    const jobs = [];

    for (const card of cards.slice(0, 50)) {
      try {
        const titleEl = await card.$('a.title, a[class*="title"], .jobTitle a');
        if (!titleEl) continue;

        const title = (await titleEl.textContent() || '').trim();
        const href = (await titleEl.getAttribute('href') || '').split('?')[0];
        if (!title || !href) continue;

        const company = await card.$eval(
          '.companyInfo .company-name, span[class*="comp-name"], a[class*="comp-name"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const location = await card.$eval(
          '.locWdth, span[class*="location"], li[class*="loc"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const exp = await card.$eval(
          '.expwdth, span[class*="exp"], li[class*="exp"]',
          el => el.textContent.trim()
        ).catch(() => '');

        jobs.push({ title, company, location, experience: exp, url: href });
      } catch {}
    }

    return jobs;
  }

  async applyToJob(job) {
    try {
      await this.page.goto(job.url, { timeout: 30000, waitUntil: 'domcontentloaded' });
      await DELAY(2000, 3500);

      const content = await this.page.content();
      if (
        content.includes('already applied') ||
        content.includes('Already Applied') ||
        content.includes('application submitted')
      ) return false;

      // Skip external apply links (company site redirects)
      if (
        content.includes('Apply on company site') ||
        content.includes('Apply on employer site')
      ) return false;

      // Find apply button
      let applyBtn = null;
      for (const sel of [
        '#apply-button',
        'button.apply-button',
        'button[class*="apply"]',
        'a[class*="apply"]',
      ]) {
        applyBtn = await this.page.$(sel);
        if (applyBtn && await applyBtn.isVisible()) break;
        applyBtn = null;
      }

      if (!applyBtn) {
        // XPATH fallback
        applyBtn = await this.page.$('button:has-text("Apply"), a:has-text("Apply")');
      }
      if (!applyBtn || !await applyBtn.isVisible()) return false;

      const mainUrl = this.page.url();
      await applyBtn.click();
      await DELAY(2000, 3500);

      // If a new tab opened it's external — close it
      const pages = this.context.pages();
      if (pages.length > 1) {
        for (const p of pages) {
          if (p !== this.page) await p.close();
        }
        return false;
      }

      // If redirected to login, session expired
      const nowUrl = this.page.url();
      if (nowUrl.includes('login') || nowUrl.includes('nlogin')) return false;

      // Handle questionnaire/modal
      await this._handleQuestionnaire();

      const finalContent = await this.page.content();
      if (
        finalContent.includes('application submitted') ||
        finalContent.includes('successfully applied') ||
        finalContent.includes('already applied')
      ) return true;

      return true; // Assume applied if no error
    } catch {
      return false;
    }
  }

  async _handleQuestionnaire() {
    await DELAY(800, 1500);

    // Close modal if present
    for (const sel of ['button[aria-label="close"]', 'button[class*="close"]', '.crossIcon', 'button.modal__close']) {
      try {
        const btn = await this.page.$(sel);
        if (btn && await btn.isVisible()) { await btn.click(); await DELAY(400, 800); return; }
      } catch {}
    }

    // Answer yes/no radios
    try {
      const radios = await this.page.$$('input[type="radio"]:not(:checked)');
      if (radios.length) { await radios[0].check().catch(() => {}); await DELAY(300, 600); }
    } catch {}

    // Click confirm/submit
    for (const label of ['Confirm', 'Submit', 'OK', 'Yes', 'Continue']) {
      try {
        const btn = await this.page.$(`button:has-text("${label}")`);
        if (btn && await btn.isVisible()) { await btn.click(); await DELAY(800, 1500); return; }
      } catch {}
    }
  }

  async run(target) {
    const result = { applied: 0, failed: 0, skipped: 0, experience_counts: {}, jobs: [] };

    await this.init();

    if (!await this.isLoggedIn()) {
      console.log('[Naukri] Not logged in. Run: node auth_setup.js first');
      await this.browser.close();
      return result;
    }
    console.log('[Naukri] Logged in ✓');

    outer: for (const role of config.roles) {
      for (const location of config.locations) {
        if (result.applied >= target) break outer;

        process.stdout.write(`[Naukri] ${role} @ ${location} → `);
        const jobs = await this.searchJobs(role, location);
        console.log(`${jobs.length} found`);

        for (const job of jobs) {
          if (result.applied >= target) break outer;

          const exp = job.experience || 'N/A';
          result.experience_counts[exp] = (result.experience_counts[exp] || 0) + 1;

          // Skip jobs requiring more experience than user has
          if (parseExpMin(exp) > config.maxExpYears) {
            console.log(`  ↳ [${exp}] ${job.title} @ ${job.company} ... skip (over-experienced)`);
            result.skipped++;
            continue;
          }

          process.stdout.write(`  ↳ [${exp}] ${job.title} @ ${job.company} ... `);
          const ok = await this.applyToJob(job);

          if (ok) {
            result.applied++;
            result.jobs.push({ ...job, status: 'applied', platform: 'naukri' });
            console.log('✓ Applied');
          } else {
            result.skipped++;
            console.log('skip');
          }

          await DELAY(1500, 2800);
        }
      }
    }

    await this.context.storageState({ path: this.authFile });
    await this.browser.close();
    return result;
  }
}

module.exports = Naukri;
