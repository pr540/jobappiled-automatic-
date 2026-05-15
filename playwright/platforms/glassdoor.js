const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const config = require('../config');

const DELAY = (min, max) => new Promise(r => setTimeout(r, min + Math.random() * (max - min)));
const BASE = 'https://www.glassdoor.co.in';

function parseExpMin(expStr) {
  if (!expStr) return 0;
  const m = expStr.match(/(\d+)/);
  return m ? parseInt(m[1]) : 0;
}

class Glassdoor {
  constructor() {
    this.authFile = path.join(config.authDir, 'glassdoor_state.json');
    this.browser = null;
    this.context = null;
    this.page = null;
  }

  async init() {
    const storageState = fs.existsSync(this.authFile) ? this.authFile : undefined;
    this.browser = await chromium.launch({
      headless: config.headless,
      slowMo: 50,
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
      await this.page.goto(`${BASE}/Job/index.htm`, { timeout: 20000, waitUntil: 'domcontentloaded' });
      await DELAY(2000, 3000);
      await this.page.waitForSelector(
        '[data-test="user-menu"], .dropdown-avatar, .userMenu, .SVGInline.avatar',
        { timeout: 6000 }
      );
      return true;
    } catch {
      try {
        const url = this.page.url();
        return url.includes('glassdoor') && !url.includes('login') && !url.includes('signin');
      } catch {
        return false;
      }
    }
  }

  async closeModal() {
    for (const sel of [
      '[alt="Close"]',
      'button.modal_closeIcon',
      'button[class*="close"]',
      '[data-test="close"]',
      'button[aria-label*="close" i]',
    ]) {
      try {
        const btn = await this.page.$(sel);
        if (btn && await btn.isVisible()) { await btn.click(); await DELAY(400, 700); return; }
      } catch {}
    }
  }

  async searchJobs(role, location) {
    const keyword = encodeURIComponent(role);
    const url = `${BASE}/Job/jobs.htm?sc.keyword=${keyword}&locT=N&locId=115&fromAge=7&jobType=fulltime`;

    try {
      await this.page.goto(url, { timeout: 30000, waitUntil: 'domcontentloaded' });
      await DELAY(2500, 4000);
    } catch {
      return [];
    }

    await this.closeModal();

    for (let i = 0; i < 4; i++) {
      await this.page.evaluate('window.scrollBy(0, 700)');
      await DELAY(500, 900);
    }

    const cards = await this.page.$$(
      'li.react-job-listing, [data-test="jobListing"], article[class*="job"], li[data-id]'
    );
    const jobs = [];

    for (const card of cards.slice(0, 30)) {
      try {
        const titleEl = await card.$('a[data-test="job-title"], .jobLink, a[class*="jobTitle"]');
        if (!titleEl) continue;

        const title = (await titleEl.textContent() || '').trim();
        let href = (await titleEl.getAttribute('href') || '').split('?')[0];
        if (!href) continue;
        if (!href.startsWith('http')) href = BASE + href;

        const company = await card.$eval(
          '[data-test="employer-short-name"], .jobHeader .employerName, [class*="employer-name"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const location = await card.$eval(
          '[data-test="emp-location"], .jobHeader .subtle, [class*="location"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const exp = await card.$eval(
          '[data-test="job-meta"], [class*="job-age"], [class*="meta"]',
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
      await this.closeModal();

      const content = await this.page.content();
      if (content.includes('Applied') || content.includes('application submitted')) return false;

      let applyBtn = null;
      for (const sel of [
        '[data-test="applyButton"]',
        'button[class*="apply"]',
        'a[class*="apply"]',
        'button:has-text("Apply")',
      ]) {
        applyBtn = await this.page.$(sel);
        if (applyBtn && await applyBtn.isVisible()) break;
        applyBtn = null;
      }

      if (!applyBtn) return false;

      const pages = this.context.pages();
      await applyBtn.click();
      await DELAY(2000, 3500);

      // If new tab opened (external apply), close it
      const nowPages = this.context.pages();
      if (nowPages.length > pages.length) {
        for (const p of nowPages) {
          if (!pages.includes(p)) await p.close();
        }
        return false;
      }

      return true;
    } catch {
      return false;
    }
  }

  async run(target) {
    const result = { applied: 0, failed: 0, skipped: 0, experience_counts: {}, jobs: [] };

    await this.init();

    if (!await this.isLoggedIn()) {
      console.log('[Glassdoor] Not logged in. Run: node auth_setup.js first');
      await this.browser.close();
      return result;
    }
    console.log('[Glassdoor] Logged in ✓');

    outer: for (const role of config.roles) {
      for (const location of config.locations) {
        if (result.applied >= target) break outer;

        process.stdout.write(`[Glassdoor] ${role} @ ${location} → `);
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
            result.jobs.push({ ...job, status: 'applied', platform: 'glassdoor' });
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

module.exports = Glassdoor;
