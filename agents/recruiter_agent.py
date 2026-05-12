"""Finds recruiters for applied jobs and sends LinkedIn connection requests."""
import re
from datetime import datetime
from openai import OpenAI
from core.config import Config
from core.database import db, Job, RecruiterOutreach
from core.logger import get_logger
from platforms.linkedin import LinkedInPlatform

log = get_logger("recruiter_agent")


def _find_recruiters_via_gpt(job_title: str, company: str) -> list[dict]:
    """Use GPT to generate likely LinkedIn search queries for recruiters."""
    if not Config.OPENAI_API_KEY:
        return []
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    prompt = (
        f"Generate 3 LinkedIn search URLs to find HR/recruiters at '{company}' "
        f"who might be hiring for '{job_title}'. Return JSON array with keys: name (generic), url."
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=400,
        )
        import json
        data = json.loads(resp.choices[0].message.content)
        return data.get("recruiters", [])
    except Exception as e:
        log.error("GPT recruiter search failed", extra={"error": str(e)})
        return []


def run_recruiter_outreach(app=None) -> dict:
    """Find recruiters for recently applied jobs and send connection requests."""
    results = {"contacted": 0, "failed": 0, "skipped": 0}

    def _outreach():
        applied_jobs = (
            db.session.query(Job)
            .filter_by(status="applied")
            .order_by(Job.applied_at.desc())
            .limit(Config.RECRUITER_OUTREACH_LIMIT)
            .all()
        )
        linkedin = LinkedInPlatform()
        linkedin.login()

        for job in applied_jobs:
            existing = (
                db.session.query(RecruiterOutreach)
                .filter_by(company=job.company)
                .first()
            )
            if existing:
                results["skipped"] += 1
                continue

            recruiters = _find_recruiters_via_gpt(job.title, job.company or "")
            for rec in recruiters[:2]:
                url = rec.get("url", "")
                if not url or "linkedin.com" not in url:
                    continue
                success = linkedin.send_recruiter_connection(url)
                record = RecruiterOutreach(
                    name=rec.get("name", "Recruiter"),
                    company=job.company,
                    linkedin_url=url,
                    connection_sent=success,
                    message_sent=success,
                    job_id=job.id,
                    created_at=datetime.utcnow(),
                )
                db.session.add(record)
                db.session.commit()
                if success:
                    results["contacted"] += 1
                else:
                    results["failed"] += 1

        linkedin.close()

    if app:
        with app.app_context():
            _outreach()
    else:
        _outreach()

    log.info("Recruiter outreach complete", extra=results)
    return results
