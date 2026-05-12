"""Orchestrates multi-platform job search, ATS filtering, and DB persistence."""
from core.config import Config
from core.database import db, Job
from core.logger import get_logger
from ats.ats_engine import should_apply, calculate_ats_score
from ats.resume_parser import parse_resume
from platforms.linkedin import LinkedInPlatform
from platforms.naukri import NaukriPlatform
from platforms.indeed import IndeedPlatform
from platforms.glassdoor import GlassdoorPlatform

log = get_logger("job_search_agent")

PLATFORM_MAP = {
    "linkedin": LinkedInPlatform,
    "naukri": NaukriPlatform,
    "indeed": IndeedPlatform,
    "glassdoor": GlassdoorPlatform,
}


def _job_url_exists(url: str) -> bool:
    return db.session.query(Job).filter_by(job_url=url).first() is not None


def run_job_search(platforms: list[str] | None = None, app=None) -> dict:
    """Search all platforms × all roles × all locations. Returns summary."""
    platforms = platforms or list(PLATFORM_MAP.keys())
    resume = parse_resume()
    results = {"scanned": 0, "saved": 0, "skipped_ats": 0, "skipped_dup": 0, "errors": 0}

    for pname in platforms:
        PlatformClass = PLATFORM_MAP.get(pname)
        if not PlatformClass:
            continue
        platform = PlatformClass()
        try:
            platform.login()
            for role in Config.TARGET_ROLES:
                for location in Config.TARGET_LOCATIONS:
                    try:
                        jobs = platform.search_jobs(role, location)
                        results["scanned"] += len(jobs)
                        for job in jobs:
                            if _job_url_exists(job.job_url):
                                results["skipped_dup"] += 1
                                continue
                            # Fetch description if empty
                            if not job.job_description and hasattr(platform, "_get_job_description"):
                                job.job_description = platform._get_job_description(job)
                            score = calculate_ats_score(job.job_description or role, resume["raw_text"])
                            job.ats_score = score
                            if score < Config.ATS_MIN_SCORE:
                                results["skipped_ats"] += 1
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
                            if app:
                                with app.app_context():
                                    db.session.add(record)
                                    db.session.commit()
                            else:
                                db.session.add(record)
                                db.session.commit()
                            results["saved"] += 1
                    except Exception as e:
                        log.error("Search error", extra={"platform": pname, "role": role, "error": str(e)})
                        results["errors"] += 1
        finally:
            platform.close()

    log.info("Job search complete", extra=results)
    return results
