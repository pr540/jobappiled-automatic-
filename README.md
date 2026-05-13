# DevOps Job Bot — Auto Apply Dashboard

Automated job search, ATS scoring, and one-click Easy Apply across **LinkedIn**, **Naukri**, and **Indeed**.  
Runs daily on a schedule or continuously in a loop. All results visible on a live web dashboard.

---

## What It Does

| Step | What happens |
|------|-------------|
| 1 | Searches LinkedIn, Naukri, Indeed for DevOps / Cloud / SRE roles |
| 2 | ATS-scores each job against your resume (saves only ≥ 75% match) |
| 3 | Auto-applies via Easy Apply / Quick Apply on each platform |
| 4 | Sends recruiter connection requests on LinkedIn |
| 5 | Saves a daily report — visible on the dashboard at `http://localhost:5000` |

---

## Requirements

| Tool | Version |
|------|---------|
| Python | 3.10 or higher (tested on 3.14) |
| Google Chrome | Any recent version |
| Windows | 10 / 11 (batch files are Windows; core Python code is cross-platform) |

---

## Installation

### Step 1 — Clone / Download

```
git clone <repo-url>
cd jobappiled-automatic-
```

Or just extract the ZIP into any folder.

---

### Step 2 — Run the Installer

Double-click **`install.bat`** (or run in terminal):

```bat
install.bat
```

This will:
- Create a Python virtual environment (`.venv`)
- Install `setuptools` and all dependencies from `requirements.txt`
- Create required folders: `data/`, `data/browser_profiles/`, `logs/`, `instance/`

---

### Step 3 — Add Your Resume

Copy your resume PDF to:

```
data\resume.pdf
```

The bot uses this for ATS scoring against every job description.

---

### Step 4 — Configure Your Details

Edit **`.env`** (create it if it doesn't exist — copy from the template below):

```env
# Your info
CANDIDATE_NAME=Your Full Name
CANDIDATE_EMAIL=your.email@gmail.com
CANDIDATE_LINKEDIN=https://www.linkedin.com/in/yourprofile/

# Bot settings
ATS_MIN_SCORE=75            # Only apply to jobs scoring >= this (0-100)
DAILY_APPLY_TARGET=150      # Max applications per run
RECRUITER_OUTREACH_LIMIT=30 # Max LinkedIn connection requests per run
HEADLESS=true               # true = run Chrome hidden; false = visible windows

# Optional: platform passwords for CI/headless environments
# LINKEDIN_PASSWORD=yourpassword
# NAUKRI_PASSWORD=yourpassword

# Optional: Flask settings
FLASK_PORT=5000
FLASK_SECRET_KEY=change-me-in-production
MORNING_SCAN_TIME=09:00     # Daily scan time (HH:MM, IST)
REPORT_TIME=20:00            # Daily report generation time
```

---

### Step 5 — Log In to Platforms (One Time Only)

Run the login setup script **once**. It opens a real Chrome window for each platform and saves your session permanently:

```bat
.venv\Scripts\python setup_login.py
```

A browser window opens for each platform in this order:
1. **Naukri** — click "Sign in with Google", select your account
2. **LinkedIn** — enter email + password
3. **Indeed** — click "Continue with Google", select your account
4. **Glassdoor** — click "Continue with Google", select your account

Sessions are saved to `data/browser_profiles/` and reused on every run (no login needed again unless session expires).

---

## How to Start

### Option A — Continuous Loop (Recommended)

Runs search + apply every 2 hours automatically until you stop it:

```bat
run_loop.bat
```

Or from terminal with custom settings:

```bat
.venv\Scripts\activate
python run_loop.py --platforms linkedin naukri indeed --interval 120 --limit 150
```

| Flag | Default | Description |
|------|---------|-------------|
| `--platforms` | `linkedin naukri indeed` | Which platforms to use |
| `--interval` | `120` | Minutes between cycles |
| `--limit` | `150` | Max jobs to apply per cycle |
| `--search-only` | off | Only search, don't apply |
| `--apply-only` | off | Only apply to existing pending jobs |

Press **Ctrl+C** to stop cleanly. Progress is logged to `logs/loop_run.log`.

---

### Option B — Single Daily Run

Runs one complete cycle (search → ATS score → apply → outreach → report):

```bat
run_now.bat
```

Or from terminal:

```bat
.venv\Scripts\activate
python run_daily.py --platforms linkedin naukri indeed --limit 150
```

---

### Option C — Windows Task Scheduler (Runs Every Morning Automatically)

Set up automatic daily execution at 9:00 AM — runs even without opening the app:

1. Right-click **`setup_scheduler.bat`**
2. Click **"Run as administrator"**

This registers a Windows Task Scheduler job called `JobBotDailyApply` that runs `daily_runner.bat` every day at 09:00.

To verify it was created:
```bat
schtasks /query /tn "JobBotDailyApply"
```

To trigger it manually:
```bat
schtasks /run /tn "JobBotDailyApply"
```

To remove it:
```bat
schtasks /delete /tn "JobBotDailyApply" /f
```

---

## Dashboard

Start the web dashboard to monitor everything in real time:

```bat
start.bat
```

Then open: **http://localhost:5000**

### Dashboard Features

| Section | What you see |
|---------|-------------|
| Stats cards | Jobs scanned, applied, interviews, rejected, pending, avg ATS score |
| Search Jobs | Triggers search only (no apply) |
| Auto Apply (Full Cycle) | Searches new jobs + applies to all pending in one click |
| Recruiter Outreach | Sends LinkedIn connection requests to recruiters |
| ATS Score Checker | Paste any job description to check your match score |
| Recent Jobs table | Live list with platform, title, company, ATS %, status |
| Recruiter Outreach table | Who was contacted, connection sent, replies received |

The dashboard auto-refreshes every 30 seconds. When a job is running, a progress bar shows the current phase (searching / applying) with live counts.

---

## Project Structure

```
jobappiled-automatic-/
├── app.py                  # Flask app entry point + blueprint registration
├── run_daily.py            # One-shot daily runner (search + apply + outreach)
├── run_loop.py             # Continuous loop runner (repeats every N minutes)
├── setup_login.py          # First-time platform login setup
│
├── agents/
│   ├── job_search_agent.py # Searches all platforms, ATS scores, saves to DB
│   ├── apply_agent.py      # Applies to pending jobs grouped by platform
│   └── recruiter_agent.py  # Sends LinkedIn recruiter connection requests
│
├── platforms/
│   ├── linkedin.py         # LinkedIn Easy Apply automation
│   ├── naukri.py           # Naukri apply automation
│   ├── indeed.py           # Indeed Apply automation
│   └── glassdoor.py        # Glassdoor apply automation
│
├── api/
│   ├── dashboard.py        # /api/dashboard/* — stats and recent jobs
│   ├── jobs.py             # /api/jobs/* — trigger search/apply, status polling
│   ├── resume.py           # /api/resume/* — upload, parse, ATS check
│   ├── outreach.py         # /api/outreach/* — recruiter table
│   └── reports.py          # /api/reports/* — daily report generation
│
├── ats/
│   ├── ats_engine.py       # Skill-matching ATS scorer
│   └── resume_parser.py    # PDF resume parser (pdfplumber)
│
├── core/
│   ├── browser.py          # Chrome driver factory (undetected_chromedriver)
│   ├── config.py           # All settings (reads from .env)
│   ├── database.py         # SQLAlchemy models (Job, DailyReport, etc.)
│   └── logger.py           # JSON structured logger
│
├── scheduler/
│   └── task_runner.py      # APScheduler — morning scan + auto-apply cron jobs
│
├── frontend/
│   ├── templates/index.html
│   └── static/
│       ├── css/style.css
│       └── js/dashboard.js
│
├── data/
│   ├── resume.pdf          # ← PUT YOUR RESUME HERE
│   └── browser_profiles/   # Saved Chrome sessions (auto-created)
│
├── logs/
│   ├── loop_run.log        # Continuous loop activity log
│   └── daily_run.log       # Daily run log
│
├── .env                    # Your config (create from template above)
├── requirements.txt        # Python dependencies
├── install.bat             # First-time install script
├── start.bat               # Start dashboard server
├── run_now.bat             # Run one complete cycle now
├── run_loop.bat            # Start continuous loop
├── daily_runner.bat        # Called by Task Scheduler
└── setup_scheduler.bat     # Register Windows Task Scheduler job (run as Admin)
```

---

## Target Roles and Locations

Configured in `core/config.py` — edit to change what jobs are searched:

**Roles searched:**
- DevOps Engineer
- AWS Cloud Engineer
- Kubernetes Engineer
- Site Reliability Engineer
- Infrastructure Engineer
- Platform Engineer

**Locations:**
- Remote, Hyderabad, Bangalore, Pune, Chennai

**Skills matched for ATS:**
AWS, Terraform, Docker, Kubernetes, Jenkins, GitHub Actions, Linux, Bash, Python, CI/CD, CloudWatch, Grafana, Prometheus, IAM, EKS, EC2, S3, VPC, Route53, ELB, Auto Scaling, WAF

---

## Logs

| File | Contents |
|------|----------|
| `logs/loop_run.log` | Continuous loop — every cycle start/end, platform activity |
| `logs/daily_run.log` | Single daily run output |
| `logs/flask.log` | Flask server output |

---

## Troubleshooting

**`No module named 'distutils'`**
Already fixed — `setuptools` is imported in `core/browser.py` before Chrome driver loads.

**Login fails / "run setup_login.py first"**
Browser session expired. Run `setup_login.py` again and log in to the affected platform.

**Chrome version mismatch**
`undetected_chromedriver` auto-detects your Chrome version. If it fails, update Chrome to the latest version.

**Dashboard not loading**
Make sure `start.bat` is running and visit `http://localhost:5000`. Check `logs/flask.log` for errors.

**0 jobs found**
ATS threshold may be too high. Lower `ATS_MIN_SCORE` in `.env` (e.g., `ATS_MIN_SCORE=60`). Also confirm your resume is at `data/resume.pdf`.

**Applied count not increasing**
Most jobs may not have Easy Apply. The bot skips jobs that require external apply on company websites — this is intentional to avoid incomplete applications.

---

## Daily Automatic Plan (Recommended Setup)

```
Morning (9:00 AM)     →  Task Scheduler runs daily_runner.bat automatically
                          Search → ATS Score → Apply → Outreach → Report

Evening (check)       →  Open http://localhost:5000 to review results

Continuous mode       →  Run run_loop.bat manually for all-day applying
                          Repeats every 2 hours until you close the window
```

For maximum applications per day, run **both**:
1. `start.bat` — keeps the dashboard running
2. `run_loop.bat` — keeps applying every 2 hours
