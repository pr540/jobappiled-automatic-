"""Naukri.com job search and apply automation."""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.browser import get_driver, human_delay, safe_click, human_type
from core.config import Config
from core.logger import get_logger
from platforms.base import BasePlatform, JobListing

log = get_logger("naukri")

BASE_URL = "https://www.naukri.com"


class NaukriPlatform(BasePlatform):
    name = "naukri"

    def __init__(self):
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            self.driver = get_driver("naukri")

    def login(self) -> bool:
        self._init_driver()
        self.driver.get(BASE_URL)
        human_delay(2, 4)
        if self._is_logged_in():
            log.info("Naukri already logged in")
            return True
        self.driver.get(f"{BASE_URL}/nlogin/login")
        human_delay(2, 3)
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "usernameField"))
            )
            human_type(email_field, Config.CANDIDATE_EMAIL)
            human_delay(0.5, 1)
            # Try Google login link
            try:
                google_btn = self.driver.find_element(By.XPATH, "//a[contains(@href,'google')]")
                safe_click(self.driver, google_btn)
                human_delay(3, 5)
                self._handle_google_oauth()
                return self._is_logged_in()
            except NoSuchElementException:
                pass
        except TimeoutException:
            log.error("Naukri login page not loaded")
        return False

    def _handle_google_oauth(self):
        """Switch to Google OAuth popup and complete sign-in."""
        human_delay(2, 4)
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            human_delay(2, 3)
            try:
                email_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                human_type(email_field, Config.CANDIDATE_EMAIL)
                self.driver.find_element(By.ID, "identifierNext").click()
                human_delay(2, 3)
                log.info("Google OAuth: email entered — waiting for manual password")
            except NoSuchElementException:
                pass

    def _is_logged_in(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR, ".nI-gNb-drawer__icon")
            return True
        except NoSuchElementException:
            return False

    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init_driver()
        jobs: list[JobListing] = []
        query = role.replace(" ", "-")
        loc = location.replace(" ", "-")
        url = f"{BASE_URL}/{query}-jobs-in-{loc}?experience=1,3&jobAge=7"
        self.driver.get(url)
        human_delay(3, 5)

        self._scroll_page()
        cards = self.driver.find_elements(By.CSS_SELECTOR, "article.jobTuple")
        log.info(f"Naukri: {len(cards)} jobs for {role} @ {location}")

        for card in cards:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "a.title")
                company_el = card.find_element(By.CSS_SELECTOR, ".companyInfo .company-name")
                location_el = card.find_element(By.CSS_SELECTOR, ".locWdth")
                exp_el = card.find_element(By.CSS_SELECTOR, ".expwdth")
                jobs.append(JobListing(
                    platform="naukri",
                    title=title_el.text.strip(),
                    company=company_el.text.strip(),
                    location=location_el.text.strip(),
                    job_url=title_el.get_attribute("href"),
                    experience_required=exp_el.text.strip(),
                ))
            except NoSuchElementException:
                continue

        return jobs

    def apply_to_job(self, job: JobListing) -> bool:
        self.driver.get(job.job_url)
        human_delay(2, 4)
        try:
            apply_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".apply-button"))
            )
            safe_click(self.driver, apply_btn)
            human_delay(2, 3)
            # Handle "Already Applied" overlay
            try:
                already = self.driver.find_element(By.XPATH, "//*[contains(text(),'Already Applied')]")
                log.info("Already applied — skipping", extra={"url": job.job_url})
                return False
            except NoSuchElementException:
                pass
            log.info("Applied on Naukri", extra={"title": job.title, "company": job.company})
            return True
        except TimeoutException:
            log.warning("Apply button not found on Naukri", extra={"url": job.job_url})
            return False

    def _get_job_description(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 3)
            desc = self.driver.find_element(By.CSS_SELECTOR, ".job-desc")
            return desc.text
        except Exception:
            return ""

    def _scroll_page(self):
        for _ in range(6):
            self.driver.execute_script("window.scrollBy(0, 700)")
            time.sleep(random.uniform(0.4, 0.9))

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
