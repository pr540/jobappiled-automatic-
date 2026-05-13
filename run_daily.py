"""
Daily auto-apply runner.
  Run manually :  python run_daily.py
  Scheduled    :  Task Scheduler calls daily_runner.bat every morning

Flow:
  1. Kill stale Chrome/chromedriver processes
  2. Login to all platforms via saved Google sessions
  3. Search DevOps jobs  (all roles x all locations)
  4. ATS-score each job  (save >= 75% to DB)
  5. Auto-apply          (up to --limit jobs)
  6. Recruiter outreach  (LinkedIn connections)
  7. Save daily report   (visible on dashboard)
"""
import os
import sys
import time
import argparse
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Respect .env HEADLESS setting; CLI --headless overrides ──
_env_headless = os.getenv("HEADLESS", "false").lower() == "true"

parser = argparse.ArgumentParser(description="JobBot Daily Runner")
parser.add_argument("--platforms", nargs="+",
                    choices=["linkedin", "naukri", "indeed", "glassdoor"],
                    default=["linkedin", "naukri", "indeed", "glassdoor"])
parser.add_argument("--limit", type=int, default=int(os.getenv("DAILY_APPLY_TARGET", "100")),
                    help="Max jobs to apply today")
parser.add_argument("--search-only", action="store_true")
parser.add_argument("--apply-only", action="store_true")
parser.add_argument("--retry-errors", action="store_true",
                    help="Reset error/failed jobs to pending before applying")
parser.add_argument("--headless", action="store_true", default=_env_headless)
parser.add_argument("--no-headless", dest="headless", action="store_false")
args = parser.parse_args()

os.environ["HEADLESS"] = "true" if args.headless else "false"

from app import create_app
from core.database import db, Job, DailyReport
from core.config import Config
from core.logger import get_logger
from ats.ats_engine import calculate_ats_score
from ats.resume_parser import parse_resume

log = get_logger("daily_runner")


# ──────────────────────────────────────────────────
# Chrome cleanup — kills stale processes before each run
# ──────────────────────────────────────────────────
def kill_stale_chrome():
    """Kill lingering chromedriver / undetected-chrome processes."""
    for proc in ["chromedriver.exe", "chrome.exe"]:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
    time.sleep(2)


# ──────────────────────────────────────────────────
# Platform factory with retry
# ──────────────────────────────────────────────────
def get_platform(name: str):
    if name == "linkedin":
        from platforms.linkedin import LinkedInPlatform
        return LinkedInPlatform()
    if name == "naukri":
        from platforms.naukri import NaukriPlatform
        return NaukriPlatform()
    if name == "indeed":
        from platforms.indeed import IndeedPlatform
        return IndeedPlatform()
    if name == "glassdoor":
        from platforms.glassdoor import GlassdoorPlatform
        return GlassdoorPlatform()
    raise ValueError(f"Unknown platform: {name}")


def start_platform_with_retry(name: str, retries: int = 2):
    """Start a platform, retrying once if Chrome fails to connect."""
    for attempt in range(retries):
        try:
            p = get_platform(name)
            p.login()
            return p
        except Exception as e:
            log.warning(f"[{name}] attempt {attempt+1} failed: {e}")
            try:
                p.close()
            except Exception:
                pass
            kill_stale_chrome()
            time.sleep(3)
    return None


# ──────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────
def run(app):
    start_time = datetime.now()
    print(f"\n{'='*65}")
    print(f"  JOBBOT DAILY RUN  —  {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Platforms  : {', '.join(args.platforms)}")
    print(f"  Limit      : {args.limit} jobs")
    print(f"  ATS min    : {Config.ATS_MIN_SCORE}%")
    print(f"  Headless   : {args.headless}")
    print(f"{'='*65}\n")

    resume_data = parse_resume()
    if not resume_data["raw_text"]:
        print("  [WARN] Resume not found at data/resume.pdf")
    else:
        print(f"  Resume: {len(resume_data['skills'])} skills | {len(resume_data['raw_text'])} chars\n")

    stats = {"scanned": 0, "saved": 0, "applied": 0,
             "skipped_ats": 0, "skipped_dup": 0, "failed": 0}

    with app.app_context():
        if not args.apply_only:
            _run_search(resume_data, stats, app)
            kill_stale_chrome()   # clean slate before apply

        if not args.search_only:
            if args.retry_errors:
                _reset_error_jobs()
            _run_apply(stats, app)
            kill_stale_chrome()

        _run_recruiter_outreach()
        _save_report(stats)

    elapsed = (datetime.now() - start_time).seconds
    _print_summary(stats, elapsed)


# ──────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────
def _job_exists(url: str) -> bool:
    return db.session.query(Job).filter_by(job_url=url).first() is not None


def _reset_error_jobs():
    count = (
        db.session.query(Job)
        .filter(Job.status.in_(["error", "failed"]))
        .update({"status": "pending", "error_message": None}, synchronize_session=False)
    )
    db.session.commit()
    print(f"  [reset] {count} error/failed jobs reset to pending")


def _run_search(resume_data: dict, stats: dict, app):
    print("\n[1/3] JOB SEARCH")
    print("-" * 40)

    for pname in args.platforms:
        platform = start_platform_with_retry(pname)
        if not platform:
            print(f"  [{pname}] Could not start — skipping")
            continue
        try:
            for role in Config.TARGET_ROLES:
                for location in Config.TARGET_LOCATIONS:
                    try:
                        jobs = platform.search_jobs(role, location)
                        new_count = 0
                        for job in jobs:
                            stats["scanned"] += 1
                            if _job_exists(job.job_url):
                                stats["skipped_dup"] += 1
                                continue
                            # Fetch description if possible
                            if not job.job_description:
                                try:
                                    fn = getattr(platform, "_get_job_description",
                                                 getattr(platform, "_get_job_details", None))
                                    if fn:
                                        job.job_description = fn(job)
                                except Exception:
                                    pass
                            jd_text = job.job_description or f"{role} {location} {job.title}"
                            score = calculate_ats_score(jd_text, resume_data["raw_text"])
                            if score < Config.ATS_MIN_SCORE:
                                stats["skipped_ats"] += 1
                                continue
                            record = Job(
                                platform=job.platform, title=job.title,
                                company=job.company, location=job.location,
                                job_url=job.job_url,
                                experience_required=job.experience_required,
                                job_description=job.job_description,
                                ats_score=score, status="pending",
                            )
                            db.session.add(record)
                            db.session.commit()
                            stats["saved"] += 1
                            new_count += 1
                        if new_count:
                            print(f"  [{pname}] {role} @ {location}: {len(jobs)} found, {new_count} saved (ATS>={Config.ATS_MIN_SCORE}%)")
                        time.sleep(1)
                    except Exception as e:
                        log.error(f"Search error [{pname}] {role}@{location}: {e}")
        finally:
            try:
                platform.close()
            except Exception:
                pass
        kill_stale_chrome()
        time.sleep(2)


# ──────────────────────────────────────────────────
# Apply
# ──────────────────────────────────────────────────
def _run_apply(stats: dict, app):
    print(f"\n[2/3] AUTO APPLY  (limit: {args.limit})")
    print("-" * 40)

    pending = (
        db.session.query(Job)
        .filter_by(status="pending")
        .filter(Job.ats_score >= Config.ATS_MIN_SCORE)
        .order_by(Job.ats_score.desc())
        .limit(args.limit * 2)
        .all()
    )
    print(f"  {len(pending)} pending jobs queued")
    if not pending:
        return

    # Group by platform
    by_platform: dict[str, list] = {}
    for j in pending:
        by_platform.setdefault(j.platform, []).append(j)

    applied_total = 0

    for pname, jobs in by_platform.items():
        if applied_total >= args.limit:
            break

        platform = start_platform_with_retry(pname)
        if not platform:
            print(f"  [{pname}] Could not start browser — skipping {len(jobs)} jobs")
            continue

        try:
            from platforms.base import JobListing
            for job in jobs:
                if applied_total >= args.limit:
                    break
                try:
                    listing = JobListing(
                        platform=job.platform, title=job.title,
                        company=job.company or "", location=job.location or "",
                        job_url=job.job_url,
                        experience_required=job.experience_required or "",
                        job_description=job.job_description or "",
                        ats_score=job.ats_score,
                    )
                    success = platform.apply_to_job(listing)
                    if success:
                        job.status = "applied"
                        job.applied_at = datetime.utcnow()
                        applied_total += 1
                        stats["applied"] += 1
                        print(f"  [OK] [{pname}] {job.title} @ {job.company}  ATS:{job.ats_score:.0f}%")
                    else:
                        job.status = "failed"
                        stats["failed"] += 1
                        print(f"  [--] [{pname}] {job.title} — skipped (not Easy Apply)")
                    db.session.commit()
                    time.sleep(3)
                except Exception as e:
                    err_str = str(e)
                    # Browser session died — restart and retry this job once
                    if "invalid session id" in err_str or "disconnected" in err_str:
                        log.warning(f"[{pname}] Session died, restarting browser...")
                        try:
                            platform.close()
                        except Exception:
                            pass
                        kill_stale_chrome()
                        time.sleep(3)
                        platform = start_platform_with_retry(pname)
                        if not platform:
                            log.error(f"[{pname}] Could not restart browser — aborting platform")
                            break
                        try:
                            success = platform.apply_to_job(listing)
                            if success:
                                job.status = "applied"
                                job.applied_at = datetime.utcnow()
                                applied_total += 1
                                stats["applied"] += 1
                                print(f"  [OK] [{pname}] {job.title} @ {job.company}  ATS:{job.ats_score:.0f}% (retry)")
                            else:
                                job.status = "failed"
                                stats["failed"] += 1
                        except Exception as e2:
                            job.status = "error"
                            job.error_message = str(e2)[:200]
                            stats["failed"] += 1
                            log.error(f"Apply retry error [{pname}]: {e2}")
                    else:
                        job.status = "error"
                        job.error_message = err_str[:200]
                        stats["failed"] += 1
                        log.error(f"Apply error [{pname}]: {e}")
                    db.session.commit()
        finally:
            try:
                platform.close()
            except Exception:
                pass
        kill_stale_chrome()
        time.sleep(2)

    print(f"\n  Applied today: {applied_total}")


# ──────────────────────────────────────────────────
# Recruiter outreach
# ──────────────────────────────────────────────────
def _run_recruiter_outreach():
    print("\n[3/3] RECRUITER OUTREACH")
    print("-" * 40)
    try:
        from agents.recruiter_agent import run_recruiter_outreach
        result = run_recruiter_outreach()
        print(f"  Contacted: {result.get('contacted',0)}  Failed: {result.get('failed',0)}  Skipped: {result.get('skipped',0)}")
    except Exception as e:
        print(f"  Outreach error: {e}")


# ──────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────
def _save_report(stats: dict):
    from datetime import date
    from sqlalchemy import func
    today = date.today()
    avg_ats = db.session.query(func.avg(Job.ats_score)).filter(
        Job.status == "applied").scalar() or 0
    existing = db.session.query(DailyReport).filter_by(date=today).first()
    if existing:
        existing.jobs_scanned += stats["scanned"]
        existing.jobs_applied += stats["applied"]
        existing.ats_avg_score = round(float(avg_ats), 1)
    else:
        db.session.add(DailyReport(
            date=today, jobs_scanned=stats["scanned"],
            jobs_applied=stats["applied"], ats_avg_score=round(float(avg_ats), 1),
        ))
    db.session.commit()


def _print_summary(stats: dict, elapsed: int):
    print(f"\n{'='*65}")
    print("  DAILY RUN COMPLETE")
    print(f"{'='*65}")
    print(f"  Jobs Scanned   : {stats['scanned']}")
    print(f"  Jobs Saved (DB): {stats['saved']}")
    print(f"  Jobs Applied   : {stats['applied']}")
    print(f"  Skipped (ATS<{Config.ATS_MIN_SCORE}%): {stats['skipped_ats']}")
    print(f"  Skipped (Dup)  : {stats['skipped_dup']}")
    print(f"  Failed         : {stats['failed']}")
    print(f"  Time Taken     : {elapsed//60}m {elapsed%60}s")
    print(f"{'='*65}\n")
    log.info("Daily run complete", extra=stats)


# ──────────────────────────────────────────────────
# Entry
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("Cleaning up stale Chrome processes...")
    kill_stale_chrome()

    flask_app = create_app()
    with flask_app.app_context():
        from core.database import init_db
        init_db()
    run(flask_app)
