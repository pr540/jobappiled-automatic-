"""
Daily auto-apply runner.
Run manually:    python run_daily.py
Or scheduled via Task Scheduler (setup_scheduler.bat).

What it does each run:
  1. Login to all platforms using saved browser sessions
  2. Search DevOps jobs across all roles x locations
  3. Score each job with ATS engine
  4. Apply to jobs with ATS score >= 75%
  5. Send recruiter connection requests on LinkedIn
  6. Save daily report to DB
  7. Print summary
"""
import os
import sys
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from core.database import db, Job, DailyReport
from core.config import Config
from core.logger import get_logger
from ats.ats_engine import calculate_ats_score
from ats.resume_parser import parse_resume

log = get_logger("daily_runner")


# ──────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────
parser = argparse.ArgumentParser(description="JobBot Daily Runner")
parser.add_argument("--platforms", nargs="+",
                    choices=["linkedin", "naukri", "indeed", "glassdoor"],
                    default=["linkedin", "naukri", "indeed", "glassdoor"],
                    help="Platforms to run (default: all)")
parser.add_argument("--limit", type=int, default=Config.DAILY_APPLY_TARGET,
                    help=f"Max jobs to apply (default: {Config.DAILY_APPLY_TARGET})")
parser.add_argument("--search-only", action="store_true",
                    help="Only search jobs, don't apply")
parser.add_argument("--apply-only", action="store_true",
                    help="Only apply to already-found pending jobs")
parser.add_argument("--headless", action="store_true", default=True,
                    help="Run browser headless (default: True)")
args = parser.parse_args()

if args.headless:
    os.environ["HEADLESS"] = "true"
else:
    os.environ["HEADLESS"] = "false"


# ──────────────────────────────────────────────
# Platform registry
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Main runner
# ──────────────────────────────────────────────
def run(app):
    start_time = datetime.now()
    print(f"\n{'='*65}")
    print(f"  JOBBOT DAILY RUN — {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Platforms : {', '.join(args.platforms)}")
    print(f"  Apply limit: {args.limit} jobs")
    print(f"  ATS threshold: {Config.ATS_MIN_SCORE}%")
    print(f"{'='*65}\n")

    resume_data = parse_resume()
    if not resume_data["raw_text"]:
        print("  [WARN] Resume not found at data/resume.pdf — ATS scoring will be limited")
    else:
        print(f"  Resume loaded: {len(resume_data['raw_text'])} chars | Skills: {len(resume_data['skills'])}")

    stats = {
        "scanned": 0, "saved": 0, "applied": 0,
        "skipped_ats": 0, "skipped_dup": 0, "failed": 0,
    }

    with app.app_context():
        if not args.apply_only:
            _run_search(resume_data, stats, app)

        if not args.search_only:
            _run_apply(stats, app)

        _run_recruiter_outreach(app)
        _save_report(stats, app)

    elapsed = (datetime.now() - start_time).seconds
    _print_summary(stats, elapsed)


def _job_exists(url: str) -> bool:
    return db.session.query(Job).filter_by(job_url=url).first() is not None


def _run_search(resume_data: dict, stats: dict, app):
    print("\n[1/3] JOB SEARCH")
    print("-"*40)

    for pname in args.platforms:
        platform = None
        try:
            platform = get_platform(pname)
            logged_in = platform.login()
            if not logged_in:
                print(f"  [{pname}] Login failed — run setup_login.py first")
                continue

            for role in Config.TARGET_ROLES:
                for location in Config.TARGET_LOCATIONS:
                    try:
                        jobs = platform.search_jobs(role, location)
                        print(f"  [{pname}] {role} @ {location}: {len(jobs)} found")

                        for job in jobs:
                            stats["scanned"] += 1
                            if _job_exists(job.job_url):
                                stats["skipped_dup"] += 1
                                continue

                            # Fetch full description if possible
                            if not job.job_description:
                                try:
                                    if hasattr(platform, "_get_job_description"):
                                        job.job_description = platform._get_job_description(job)
                                    elif hasattr(platform, "_get_job_details"):
                                        job.job_description = platform._get_job_details(job)
                                except Exception:
                                    pass

                            jd_text = job.job_description or f"{role} {location} {job.title}"
                            score = calculate_ats_score(jd_text, resume_data["raw_text"])

                            if score < Config.ATS_MIN_SCORE:
                                stats["skipped_ats"] += 1
                                continue

                            record = Job(
                                platform=job.platform,
                                title=job.title,
                                company=job.company,
                                location=job.location,
                                job_url=job.job_url,
                                experience_required=job.experience_required,
                                job_description=job.job_description,
                                ats_score=score,
                                status="pending",
                            )
                            db.session.add(record)
                            db.session.commit()
                            stats["saved"] += 1
                            print(f"    ✓ Saved: {job.title} @ {job.company} (ATS:{score:.0f}%)")

                        time.sleep(2)
                    except Exception as e:
                        print(f"  [{pname}] Error searching {role}@{location}: {e}")
        except Exception as e:
            print(f"  [{pname}] Platform error: {e}")
        finally:
            if platform:
                try:
                    platform.close()
                except Exception:
                    pass


def _run_apply(stats: dict, app):
    print(f"\n[2/3] AUTO APPLY (limit: {args.limit})")
    print("-"*40)

    pending = (
        db.session.query(Job)
        .filter_by(status="pending")
        .filter(Job.ats_score >= Config.ATS_MIN_SCORE)
        .order_by(Job.ats_score.desc())
        .limit(args.limit * 2)  # grab extra as buffer
        .all()
    )
    print(f"  Found {len(pending)} pending jobs to process")

    # Group by platform to reuse browser sessions
    by_platform: dict[str, list] = {}
    for j in pending:
        by_platform.setdefault(j.platform, []).append(j)

    applied_count = 0

    for pname, jobs in by_platform.items():
        if applied_count >= args.limit:
            break

        platform = None
        try:
            platform = get_platform(pname)
            if not platform.login():
                print(f"  [{pname}] Login failed — skipping")
                continue

            for job in jobs:
                if applied_count >= args.limit:
                    break
                try:
                    from platforms.base import JobListing
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
                        applied_count += 1
                        stats["applied"] += 1
                        print(f"  ✓ Applied [{pname}]: {job.title} @ {job.company} (ATS:{job.ats_score:.0f}%)")
                    else:
                        job.status = "failed"
                        stats["failed"] += 1
                    db.session.commit()
                    time.sleep(3)
                except Exception as e:
                    job.status = "error"
                    job.error_message = str(e)
                    db.session.commit()
                    stats["failed"] += 1
                    print(f"  ✗ Failed [{pname}]: {job.title} — {e}")
        except Exception as e:
            print(f"  [{pname}] Platform error during apply: {e}")
        finally:
            if platform:
                try:
                    platform.close()
                except Exception:
                    pass


def _run_recruiter_outreach(app):
    print("\n[3/3] RECRUITER OUTREACH")
    print("-"*40)
    try:
        from agents.recruiter_agent import run_recruiter_outreach
        result = run_recruiter_outreach(app=app)
        print(f"  Contacted: {result.get('contacted',0)} | Failed: {result.get('failed',0)} | Skipped: {result.get('skipped',0)}")
    except Exception as e:
        print(f"  Outreach error: {e}")


def _save_report(stats: dict, app):
    from datetime import date
    from sqlalchemy import func
    today = date.today()
    avg_ats = db.session.query(func.avg(Job.ats_score)).filter(
        Job.status == "applied"
    ).scalar() or 0

    existing = db.session.query(DailyReport).filter_by(date=today).first()
    if existing:
        existing.jobs_scanned  += stats["scanned"]
        existing.jobs_applied  += stats["applied"]
        existing.ats_avg_score  = round(float(avg_ats), 1)
    else:
        db.session.add(DailyReport(
            date=today,
            jobs_scanned=stats["scanned"],
            jobs_applied=stats["applied"],
            ats_avg_score=round(float(avg_ats), 1),
        ))
    db.session.commit()


def _print_summary(stats: dict, elapsed: int):
    print(f"\n{'='*65}")
    print("  DAILY RUN COMPLETE")
    print(f"{'='*65}")
    print(f"  Jobs Scanned   : {stats['scanned']}")
    print(f"  Jobs Saved     : {stats['saved']}")
    print(f"  Jobs Applied   : {stats['applied']}")
    print(f"  Skipped (ATS)  : {stats['skipped_ats']}  (score below {Config.ATS_MIN_SCORE}%)")
    print(f"  Skipped (Dup)  : {stats['skipped_dup']}  (already in DB)")
    print(f"  Failed         : {stats['failed']}")
    print(f"  Elapsed        : {elapsed//60}m {elapsed%60}s")
    print(f"{'='*65}\n")

    log.info("Daily run complete", extra=stats)


if __name__ == "__main__":
    flask_app = create_app()
    with flask_app.app_context():
        from core.database import init_db
        init_db()
    run(flask_app)
