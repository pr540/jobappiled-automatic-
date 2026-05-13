"""Auto-applies to pending jobs stored in the DB."""
from datetime import datetime
from core.config import Config
from core.database import db, Job
from core.logger import get_logger

log = get_logger("apply_agent")


def _get_platform(name: str):
    classes = {
        "linkedin": "platforms.linkedin.LinkedInPlatform",
        "naukri": "platforms.naukri.NaukriPlatform",
        "indeed": "platforms.indeed.IndeedPlatform",
        "glassdoor": "platforms.glassdoor.GlassdoorPlatform",
    }
    path = classes.get(name)
    if not path:
        return None
    import importlib
    module_path, class_name = path.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    instance = getattr(mod, class_name)()
    instance.login()
    return instance


def run_auto_apply(daily_limit: int | None = None) -> dict:
    """Apply to all pending jobs up to daily_limit. Must be called inside app_context."""
    limit = daily_limit or Config.DAILY_APPLY_TARGET
    results = {"applied": 0, "failed": 0, "skipped": 0}

    pending = (
        db.session.query(Job)
        .filter_by(status="pending")
        .filter(Job.ats_score >= Config.ATS_MIN_SCORE)
        .order_by(Job.ats_score.desc())
        .limit(limit)
        .all()
    )
    log.info(f"Auto-apply: {len(pending)} pending jobs")

    # Group by platform so we only open one browser per platform
    by_platform: dict[str, list] = {}
    for job in pending:
        by_platform.setdefault(job.platform, []).append(job)

    for pname, jobs in by_platform.items():
        if results["applied"] >= limit:
            break

        platform = None
        try:
            platform = _get_platform(pname)
        except Exception as e:
            log.error(f"Cannot start platform {pname}: {e}")

        if not platform:
            for job in jobs:
                job.status = "error"
                job.error_message = f"Platform {pname} could not start"
                db.session.commit()
                results["skipped"] += 1
            continue

        try:
            from platforms.base import JobListing
            for job in jobs:
                if results["applied"] >= limit:
                    break
                try:
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
                        log.info("Applied", extra={"title": job.title, "platform": pname})
                    else:
                        results["failed"] += 1
                except Exception as e:
                    job.status = "error"
                    job.error_message = str(e)[:200]
                    db.session.commit()
                    results["failed"] += 1
                    log.error(f"Apply error [{pname}]: {e}")
        finally:
            try:
                platform.close()
            except Exception:
                pass

    log.info("Auto-apply complete", extra=results)
    return results
