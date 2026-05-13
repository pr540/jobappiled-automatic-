"""Orchestrates multi-platform job search, ATS filtering, and DB persistence."""
from core.config import Config
from core.database import db, Job
from core.logger import get_logger
from ats.ats_engine import calculate_ats_score
from ats.resume_parser import parse_resume

log = get_logger("job_search_agent")

PLATFORM_MAP = {
    "linkedin": "platforms.linkedin.LinkedInPlatform",
    "naukri": "platforms.naukri.NaukriPlatform",
    "indeed": "platforms.indeed.IndeedPlatform",
    "glassdoor": "platforms.glassdoor.GlassdoorPlatform",
}


def _get_platform_class(name: str):
    module_path, class_name = PLATFORM_MAP[name].rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def _job_url_exists(url: str) -> bool:
    return db.session.query(Job).filter_by(job_url=url).first() is not None


def run_job_search(platforms: list[str] | None = None) -> dict:
    """Search all platforms × all roles × all locations. Returns summary dict."""
    platforms = platforms or list(PLATFORM_MAP.keys())
    resume = parse_resume()
    results = {"scanned": 0, "saved": 0, "skipped_ats": 0, "skipped_dup": 0, "errors": 0}

    for pname in platforms:
        if pname not in PLATFORM_MAP:
            continue
        try:
            PlatformClass = _get_platform_class(pname)
        except Exception as e:
            log.error(f"Cannot load platform {pname}: {e}")
            continue

        platform = PlatformClass()
        try:
            if not platform.login():
                log.warning(f"[{pname}] login failed — skipping")
                continue

            for role in Config.TARGET_ROLES:
                for location in Config.TARGET_LOCATIONS:
                    try:
                        jobs = platform.search_jobs(role, location)
                        results["scanned"] += len(jobs)
                        for job in jobs:
                            if _job_url_exists(job.job_url):
                                results["skipped_dup"] += 1
                                continue

                            if not job.job_description and hasattr(platform, "_get_job_description"):
                                try:
                                    job.job_description = platform._get_job_description(job)
                                except Exception:
                                    pass

                            score = calculate_ats_score(
                                job.job_description or f"{role} {location}",
                                resume["raw_text"]
                            )
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
                            db.session.add(record)
                            db.session.commit()
                            results["saved"] += 1

                    except Exception as e:
                        log.error(f"Search error [{pname}] {role}@{location}: {e}")
                        results["errors"] += 1

        except Exception as e:
            log.error(f"Platform error [{pname}]: {e}")
            results["errors"] += 1
        finally:
            try:
                platform.close()
            except Exception:
                pass

    log.info("Job search complete", extra=results)
    return results
