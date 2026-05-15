const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const config = require('../config');

const DELAY = (min, max) => new Promise(r => setTimeout(r, min + Math.random() * (max - min)));

function parseExpMin(expStr) {
  if (!expStr) return 0;
  const m = expStr.match(/(\d+)/);
  return m ? parseInt(m[1]) : 0;
}

class LinkedIn {
  constructor() {
    this.authFile = path.join(config.authDir, 'linkedin_state.json');
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
      await this.page.goto('https://www.linkedin.com/feed/', { timeout: 20000, waitUntil: 'domcontentloaded' });
      await this.page.waitForSelector('.global-nav__me-photo, .feed-identity-module, nav.global-nav', { timeout: 8000 });
      return true;
    } catch {
      return false;
    }
  }

  async searchJobs(role, location) {
    const q = encodeURIComponent(role);
    const l = encodeURIComponent(location);
    const url = `https://www.linkedin.com/jobs/search/?keywords=${q}&location=${l}&f_AL=true&f_E=2,3&sortBy=DD&f_TPR=r604800`;

    try {
      await this.page.goto(url, { timeout: 30000, waitUntil: 'domcontentloaded' });
      await DELAY(2500, 4000);
    } catch {
      return [];
    }

    for (let i = 0; i < 4; i++) {
      await this.page.evaluate('window.scrollBy(0, 700)');
      await DELAY(600, 1000);
    }

    const cards = await this.page.$$('li[data-occludable-job-id], .jobs-search__results-list li, .scaffold-layout__list-item');
    const jobs = [];

    for (const card of cards.slice(0, 40)) {
      try {
        const titleEl = await card.$('a.job-card-list__title, h3.base-search-card__title, h3[class*="title"]');
        const linkEl = await card.$('a[href*="/jobs/view/"], a.base-card__full-link');
        if (!titleEl || !linkEl) continue;

        const title = (await titleEl.textContent() || '').trim();
        const href = (await linkEl.getAttribute('href') || '').split('?')[0];
        if (!href.includes('/jobs/view/') || !title) continue;

        const company = await card.$eval(
          'h4.base-search-card__subtitle, .job-card-container__company-name, a[class*="company"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const location = await card.$eval(
          '.job-search-card__location, span[class*="location"]',
          el => el.textContent.trim()
        ).catch(() => '');

        const exp = await card.$eval(
          '.job-card-container__metadata-item, [class*="metadata-item"]',
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
      if (content.includes('You applied') || content.includes('Application submitted')) return false;

      // Find Easy Apply button
      let applyBtn = null;
      for (const sel of [
        '.jobs-apply-button--top-card',
        'button.jobs-apply-button',
        'button[class*="jobs-apply-button"]',
      ]) {
        applyBtn = await this.page.$(sel);
        if (applyBtn && await applyBtn.isVisible()) break;
        applyBtn = null;
      }
      if (!applyBtn) return false;

      const btnText = (await applyBtn.textContent() || '').trim();
      if (!btnText.includes('Apply')) return false;

      await applyBtn.click();
      await DELAY(1500, 2500);

      return await this._completeEasyApply();
    } catch {
      return false;
    }
  }

  async _completeEasyApply() {
    for (let step = 0; step < 12; step++) {
      await DELAY(1200, 2000);

      // Dismiss success modals
      try {
        const dismiss = await this.page.$('button[aria-label="Dismiss"]');
        if (dismiss && await dismiss.isVisible()) { await dismiss.click(); continue; }
      } catch {}

      // Fill phone
      try {
        for (const phone of await this.page.$$('input[id*="phoneNumber"], input[autocomplete="tel"]')) {
          if (await phone.isVisible() && !(await phone.inputValue()).trim()) {
            await phone.fill(config.phone);
          }
        }
      } catch {}

      // Fill empty text/number inputs (years of experience etc.)
      try {
        for (const inp of await this.page.$$(
          '.jobs-easy-apply-form-element input[type="text"]:not([readonly]), ' +
          '.jobs-easy-apply-form-element input[type="number"]:not([readonly])'
        )) {
          if (await inp.isVisible() && !(await inp.inputValue()).trim()) {
            await inp.fill('2');
            await DELAY(150, 300);
          }
        }
      } catch {}

      // Select first radio per group
      try {
        const seen = new Set();
        for (const radio of await this.page.$$('fieldset input[type="radio"]')) {
          const name = await radio.getAttribute('name') || '';
          if (!seen.has(name) && !(await radio.isChecked())) {
            await radio.check().catch(() => {});
            seen.add(name);
            await DELAY(200, 400);
          }
        }
      } catch {}

      // Handle dropdowns
      try {
        for (const sel of await this.page.$$('.jobs-easy-apply-form-element select')) {
          if (!await sel.isVisible()) continue;
          const val = await sel.inputValue();
          if (!val) {
            const options = await sel.$$('option[value]:not([value=""])');
            if (options.length) await sel.selectOption({ index: 1 });
          }
        }
      } catch {}

      // Click action buttons
      let clicked = false;
      for (const label of ['Submit application', 'Submit', 'Review', 'Next', 'Continue']) {
        try {
          const btn = await this.page.$(`button:has-text("${label}")`);
          if (btn && await btn.isVisible() && await btn.isEnabled()) {
            await btn.click();
            await DELAY(1200, 2000);
            if (label.includes('Submit')) {
              await this._dismissModal();
              return true;
            }
            clicked = true;
            break;
          }
        } catch {}
      }

      if (!clicked) {
        const modal = await this.page.$('.artdeco-modal--is-showing');
        if (!modal) return true;
      }
    }
    return false;
  }

  async _dismissModal() {
    await DELAY(800, 1500);
    for (const sel of [
      'button[aria-label*="Dismiss"]',
      'button:has-text("Not now")',
      'button:has-text("Done")',
      'button.artdeco-modal__dismiss',
    ]) {
      try {
        const btn = await this.page.$(sel);
        if (btn && await btn.isVisible()) { await btn.click(); return; }
      } catch {}
    }
  }

  async run(target) {
    const result = { applied: 0, failed: 0, skipped: 0, experience_counts: {}, jobs: [] };

    await this.init();

    if (!await this.isLoggedIn()) {
      console.log('[LinkedIn] Not logged in. Run: node auth_setup.js first');
      await this.browser.close();
      return result;
    }
    console.log('[LinkedIn] Logged in ✓');

    outer: for (const role of config.roles) {
      for (const location of config.locations) {
        if (result.applied >= target) break outer;

        process.stdout.write(`[LinkedIn] ${role} @ ${location} → `);
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
            result.jobs.push({ ...job, status: 'applied', platform: 'linkedin' });
            console.log('✓ Applied');
          } else {
            result.skipped++;
            console.log('skip');
          }

          await DELAY(1800, 3200);
        }
      }
    }

    // Refresh saved auth
    await this.context.storageState({ path: this.authFile });
    await this.browser.close();
    return result;
  }
}

module.exports = LinkedIn;
