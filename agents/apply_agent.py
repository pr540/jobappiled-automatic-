"""Auto-applies to pending jobs stored in the DB."""
from datetime import datetime
from core.config import Config
from core.database import db, Job
from core.logger import get_logger
from platforms.linkedin import LinkedInPlatform
from platforms.naukri import NaukriPlatform
from platforms.indeed import IndeedPlatform
from platforms.glassdoor import GlassdoorPlatform

log = get_logger("apply_agent")

PLATFORM_INSTANCES: dict = {}


def _get_platform(name: str):
    if name not in PLATFORM_INSTANCES:
        classes = {
            "linkedin": LinkedInPlatform,
            "naukri": NaukriPlatform,
            "indeed": IndeedPlatform,
            "glassdoor": GlassdoorPlatform,
        }
        cls = classes.get(name)
        if cls:
            instance = cls()
            instance.login()
            PLATFORM_INSTANCES[name] = instance
    return PLATFORM_INSTANCES.get(name)


def run_auto_apply(app=None, daily_limit: int | None = None) -> dict:
    """Apply to all pending jobs up to daily_limit."""
    limit = daily_limit or Config.DAILY_APPLY_TARGET
    results = {"applied": 0, "failed": 0, "skipped": 0}

    def _apply_batch():
        pending = (
            db.session.query(Job)
            .filter_by(status="pending")
            .filter(Job.ats_score >= Config.ATS_MIN_SCORE)
            .order_by(Job.ats_score.desc())
            .limit(limit)
            .all()
        )
        log.info(f"Auto-apply: {len(pending)} pending jobs")

        for job in pending:
            if results["applied"] >= limit:
                break
            platform = _get_platform(job.platform)
            if not platform:
                job.status = "error"
                job.error_message = "Platform not available"
                db.session.commit()
                results["skipped"] += 1
                continue
            try:
                from platforms.base import JobListing
                listing = JobListing(
                    platform=job.platform,
                    title=job.title,
                    company=job.company or "",
                    location=job.location or "",
                    job_url=job.job_url,
                    experience_required=job.experience_required or "",
                    job_description=job.job_description or "",
                    ats_score=job.ats_score,
                )
                success = platform.apply_to_job(listing)
                job.status = "applied" if success else "failed"
                job.applied_at = datetime.utcnow() if success else None
                db.session.commit()
                if success:
                    results["applied"] += 1
                    log.info("Applied", extra={"title": job.title, "company": job.company, "platform": job.platform})
                else:
                    results["failed"] += 1
            except Exception as e:
                job.status = "error"
                job.error_message = str(e)
                db.session.commit()
                results["failed"] += 1
                log.error("Apply error", extra={"job_id": job.id, "error": str(e)})

        # Close all platform drivers
        for p in PLATFORM_INSTANCES.values():
            try:
                p.close()
            except Exception:
                pass
        PLATFORM_INSTANCES.clear()

    if app:
        with app.app_context():
            _apply_batch()
    else:
        _apply_batch()

    log.info("Auto-apply complete", extra=results)
    return results
