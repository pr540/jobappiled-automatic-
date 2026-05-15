# DevOps Job Bot — Auto Apply Dashboard

Automated job search, ATS scoring, and one-click Easy Apply across **LinkedIn**, **Naukri**, **Glassdoor**, and **Indeed**.
Runs daily via Playwright (Node.js) or Python/Selenium. All results visible on a live web dashboard.

---

## What Was Done (May 15 2025)

| # | What |
|---|------|
| 1 | Added **Playwright automation** (`playwright/`) — Node.js runner for LinkedIn, Naukri, Glassdoor |
| 2 | Google sign-in session saved per platform (one-time setup, auto-reused every day) |
| 3 | LinkedIn **Easy Apply** — auto-fills multi-step forms (phone, years of experience, dropdowns, radios) |
| 4 | Naukri **direct apply** — handles questionnaires, skips external/company-site jobs |
| 5 | Glassdoor **apply button** click, skips external-redirect jobs |
| 6 | **Experience count display** in terminal — shows breakdown of experience required per job viewed |
| 7 | **Email notification** after each run (Gmail SMTP, needs App Password in `.env`) |
| 8 | **Mobile push** via ntfy.sh (free app — subscribe to a topic, get push on phone) |
| 9 | Removed unused files: Dockerfile, docker-compose, Vercel, GitHub Actions, scratch files |
| 10 | Added `run_playwright.bat` in root — double-click to run every morning |

---

## Quick Start (Playwright — Recommended)

### Prerequisites
- Node.js 18+ installed ([nodejs.org](https://nodejs.org))
- Your resume at `data\resume.pdf`
- `.env` filled with your details (see below)

### Step 1 — Install (one time)

Open CMD inside the `playwright\` folder:

```bat
install.bat
```

This installs npm packages, downloads Chromium, and opens each platform browser for Google login.

### Step 2 — Sign in with Google (one time)

```bat
node auth_setup.js
```

Browser opens for each platform. Sign in with Google (`praneethssr.2002@gmail.com`), press ENTER. Sessions saved to `playwright\auth\` — never need to log in again unless session expires.

### Step 3 — Run every morning

Double-click `run_playwright.bat` in the root folder, or:

```bat
cd playwright
node run_jobs.js
```

**What it does each run:**

| Platform | Target | Method |
|---|---|---|
| LinkedIn | 40 jobs | Easy Apply (auto-fills all form steps) |
| Naukri | 35 jobs | Direct Apply button |
| Glassdoor | 25 jobs | Apply button (skips external redirects) |
| **Total** | **100 jobs** | Glassdoor fills the gap if others fall short |

---

## Terminal Output

```
╔════════════════════════════════════════════════════╗
║          JOB BOT — PLAYWRIGHT RUNNER               ║
║  Candidate : Sanagapalli Sri Ram Praneeth          ║
║  Target    : 100                                   ║
╚════════════════════════════════════════════════════╝

[1/3] LinkedIn  (target: 40)
[LinkedIn] Logged in ✓
[LinkedIn] DevOps Engineer @ Hyderabad → 28 found
  ↳ [1-3 Yrs] DevOps Engineer @ TCS ... ✓ Applied
  ↳ [2-4 Yrs] AWS Cloud Engineer @ Infosys ... ✓ Applied

┌─────────────────────────────────────────────────┐
│     EXPERIENCE REQUIRED (all jobs viewed)        │
├───────────────────────────┬─────────────────────┤
│ 1-3 Yrs                   │ ████████████ 42     │
│ 3-5 Yrs                   │ ████ 8              │
└───────────────────────────┴─────────────────────┘

╔════════════════════════════════════════════════════╗
║  LinkedIn   : 40 applied  | 12 skipped            ║
║  Naukri     : 35 applied  | 8 skipped             ║
║  Glassdoor  : 25 applied  | 5 skipped             ║
║  TOTAL      : 100 jobs applied                    ║
╚════════════════════════════════════════════════════╝
```

---

## Notifications Setup

Edit `.env`:

```env
# Email (Gmail App Password)
# Get at: myaccount.google.com → Security → App passwords
SMTP_USER=praneethssr.2002@gmail.com
SMTP_PASS=your_gmail_app_password
NOTIFY_EMAIL=praneethssr.2002@gmail.com

# Mobile push via ntfy.sh (free)
# 1. Install ntfy app on phone
# 2. Subscribe to any topic name you choose
# 3. Set NTFY_TOPIC to that name
NTFY_TOPIC=praneeth_jobs
```

After each run you receive:
- **Email** — full HTML report with all applied jobs, experience breakdown
- **Mobile** — instant push: "100 jobs applied | LinkedIn 40 | Naukri 35 | Glassdoor 25"

---

## Playwright File Structure

```
playwright/
├── auth_setup.js        ← one-time Google login per platform
├── run_jobs.js          ← main runner (run this every morning)
├── config.js            ← reads .env settings
├── notify.js            ← email + mobile push after run
├── install.bat          ← first-time install script
├── run_jobs.bat         ← run from inside playwright folder
├── package.json
├── auth/                ← saved Google sessions (gitignored)
│   ├── linkedin_state.json
│   ├── naukri_state.json
│   └── glassdoor_state.json
└── platforms/
    ├── linkedin.js      ← Easy Apply automation
    ├── naukri.js        ← direct apply automation
    └── glassdoor.js     ← apply button automation
```

---

## Configure Your Details

Edit **`.env`** in the root folder:

```env
# Your info
CANDIDATE_NAME=Sanagapalli Sri Ram Praneeth
CANDIDATE_EMAIL=praneethssr.2002@gmail.com
CANDIDATE_LINKEDIN=https://www.linkedin.com/in/sriampraneeth143/
CANDIDATE_PHONE=9999999999

# Bot settings
ATS_MIN_SCORE=75
DAILY_APPLY_TARGET=100      # Playwright runner caps at 100 per morning
MAX_EXPERIENCE_YEARS=3
HEADLESS=false              # false = see browser; true = run hidden
```

---

## Target Roles and Locations

Configured in `playwright/config.js` and `core/config.py`:

**Roles:** DevOps Engineer, AWS Cloud Engineer, Kubernetes Engineer, Site Reliability Engineer, Infrastructure Engineer, Platform Engineer

**Locations:** Hyderabad, Bangalore, Remote, Pune, Chennai

**ATS Skills matched:** AWS, Terraform, Docker, Kubernetes, Jenkins, GitHub Actions, Linux, Bash, Python, CI/CD, CloudWatch, Grafana, Prometheus, IAM, EKS, EC2, S3, VPC, Route53, ELB, Auto Scaling, WAF

---

## Python/Selenium Runner (Alternative)

The original Selenium-based runner still works. Use it if Playwright has issues:

```bat
install.bat              # create .venv and install Python deps
.venv\Scripts\python setup_login.py   # one-time login
run_now.bat              # run one cycle
run_loop.bat             # run every 2 hours continuously
start.bat                # open web dashboard at http://localhost:5000
```

---

## Project Structure

```
jobappiled-automatic-/
├── run_playwright.bat      ← Morning run (double-click this)
├── playwright/             ← Playwright Node.js automation (new)
├── app.py                  ← Flask dashboard entry point
├── run_daily.py            ← Python one-shot runner
├── run_loop.py             ← Python continuous loop runner
├── setup_login.py          ← Python one-time login setup
├── agents/                 ← job search, apply, recruiter agents
├── platforms/              ← Selenium platform automation
├── api/                    ← Flask API blueprints
├── ats/                    ← ATS scoring + resume parser
├── core/                   ← browser, config, database, logger
├── scheduler/              ← APScheduler cron jobs
├── data/resume.pdf         ← YOUR RESUME (put it here)
├── .env                    ← your config
└── requirements.txt        ← Python dependencies
```

---

## Troubleshooting

**`node auth_setup.js` — browser opens but can't detect login**
Press ENTER in the terminal manually after you're signed in.

**Session expired (login prompt appears during run)**
Delete the old auth file and re-run `node auth_setup.js` for that platform:
```
del playwright\auth\linkedin_state.json
node auth_setup.js
```

**Glassdoor skipped (target already reached)**
Normal — LinkedIn + Naukri hit 100, Glassdoor not needed that run.

**`No module named 'distutils'`** (Python runner)
Fixed — `setuptools` pre-imported in `core/browser.py`.

**0 jobs applied on LinkedIn**
Easy Apply filter only. Jobs without Easy Apply are skipped (intentional — avoids incomplete external applications).

**Email not sending**
Make sure `SMTP_PASS` is a Gmail **App Password**, not your regular password.
Get one at: myaccount.google.com → Security → 2-Step Verification → App passwords
