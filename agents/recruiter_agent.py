"""Finds recruiters via LinkedIn people search and sends connection requests."""
import time
import random
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from core.config import Config
from core.database import db, Job, RecruiterOutreach
from core.logger import get_logger
from platforms.linkedin import LinkedInPlatform

log = get_logger("recruiter_agent")


def _search_recruiters_on_linkedin(driver, company: str, job_title: str = "") -> list[dict]:
    """Search LinkedIn people for HR/recruiters at a given company.
    Returns list of {name, url, title} dicts for real profiles found."""
    recruiters = []
    search_terms = f"HR recruiter {company} {job_title}".strip()
    query = search_terms.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={query}&origin=GLOBAL_SEARCH_HEADER"
    )
    try:
        driver.get(url)
        time.sleep(random.uniform(2, 4))

        cards = driver.find_elements(By.CSS_SELECTOR,
            ".reusable-search__result-container, "
            "li.reusable-search__result-container, "
            "div[data-chameleon-result-urn]")

        for card in cards[:5]:
            try:
                # Get profile link
                link = card.find_element(By.CSS_SELECTOR,
                    "a.app-aware-link[href*='/in/'], "
                    "a[href*='linkedin.com/in/']")
                href = link.get_attribute("href") or ""
                if "/in/" not in href:
                    continue
                # Normalise — strip query params
                profile_url = href.split("?")[0].rstrip("/")

                # Get name
                try:
                    name_el = card.find_element(By.CSS_SELECTOR,
                        ".entity-result__title-text span[aria-hidden='true'], "
                        ".actor-name, span.t-16")
                    name = name_el.text.strip()
                except NoSuchElementException:
                    name = "Recruiter"

                # Get title — only include if HR/recruiter/talent related
                try:
                    title_el = card.find_element(By.CSS_SELECTOR,
                        ".entity-result__primary-subtitle, "
                        ".subline-level-1")
                    title = title_el.text.strip()
                except NoSuchElementException:
                    title = ""

                hr_keywords = ["recruit", "hr ", "human resource", "talent",
                               "people", "hiring", "staffing", "acquisition"]
                if title and not any(k in title.lower() for k in hr_keywords):
                    continue  # Skip non-HR profiles

                if profile_url:
                    recruiters.append({"name": name, "url": profile_url, "title": title})
                    if len(recruiters) >= 2:
                        break
            except NoSuchElementException:
                continue

    except Exception as e:
        log.warning(f"LinkedIn recruiter search failed for '{company}': {e}")

    return recruiters


def run_recruiter_outreach() -> dict:
    """Search LinkedIn for real recruiters at companies we applied to,
    then send connection requests with a personalised note.
    Must be called inside an active Flask app_context."""
    results = {"contacted": 0, "failed": 0, "skipped": 0}

    # Only target jobs we applied to recently, with a known company name
    applied_jobs = (
        db.session.query(Job)
        .filter(Job.status == "applied")
        .filter(Job.company.isnot(None))
        .filter(Job.company != "")
        .order_by(Job.applied_at.desc())
        .limit(Config.RECRUITER_OUTREACH_LIMIT)
        .all()
    )

    if not applied_jobs:
        log.info("Recruiter outreach: no applied jobs to process")
        return results

    linkedin = LinkedInPlatform()
    try:
        if not linkedin.login():
            log.warning("Recruiter outreach: LinkedIn login failed — skipping")
            return results

        driver = linkedin.driver

        for job in applied_jobs:
            # Skip if we already contacted someone at this company
            already = (
                db.session.query(RecruiterOutreach)
                .filter(
                    RecruiterOutreach.company == job.company,
                    RecruiterOutreach.connection_sent.is_(True),
                )
                .first()
            )
            if already:
                results["skipped"] += 1
                continue

            recruiters = _search_recruiters_on_linkedin(driver, job.company, job.title)

            if not recruiters:
                log.info(f"No recruiters found for {job.company}")
                results["skipped"] += 1
                continue

            for rec in recruiters:
                url = rec.get("url", "")
                if not url:
                    continue

                success = linkedin.send_recruiter_connection(url)

                record = RecruiterOutreach(
                    name=rec.get("name", "Recruiter"),
                    title=rec.get("title", ""),
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
                    log.info(f"Connection sent: {rec['name']} @ {job.company}")
                else:
                    results["failed"] += 1

                # Rate limit — avoid LinkedIn blocking rapid requests
                time.sleep(random.uniform(8, 15))

            # Pause between companies
            time.sleep(random.uniform(3, 6))

    except Exception as e:
        log.error(f"Recruiter outreach error: {e}")
    finally:
        try:
            linkedin.close()
        except Exception:
            pass

    log.info("Recruiter outreach complete", extra=results)
    return results
