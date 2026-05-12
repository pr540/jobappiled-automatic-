"""Glassdoor job search automation."""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.browser import get_driver, human_delay, safe_click
from core.config import Config
from core.logger import get_logger
from platforms.base import BasePlatform, JobListing

log = get_logger("glassdoor")

BASE_URL = "https://www.glassdoor.co.in"


class GlassdoorPlatform(BasePlatform):
    name = "glassdoor"

    def __init__(self):
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            self.driver = get_driver("glassdoor")

    def login(self) -> bool:
        self._init_driver()
        self.driver.get(f"{BASE_URL}/profile/login_input.htm")
        human_delay(2, 3)
        try:
            google_btn = self.driver.find_element(
                By.XPATH, "//a[contains(@href,'google') or contains(.,'Google')]"
            )
            safe_click(self.driver, google_btn)
            human_delay(3, 5)
            log.info("Glassdoor Google OAuth initiated")
            return True
        except NoSuchElementException:
            log.warning("Glassdoor Google button not found")
            return False

    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init_driver()
        jobs: list[JobListing] = []
        url = (
            f"{BASE_URL}/Job/jobs.htm"
            f"?sc.keyword={role.replace(' ', '+')}"
            f"&locT=C&locId=3&jobType=fulltime"
        )
        self.driver.get(url)
        human_delay(3, 5)

        # Close modal if present
        try:
            close_btn = self.driver.find_element(By.CSS_SELECTOR, "[alt='Close']")
            safe_click(self.driver, close_btn)
        except NoSuchElementException:
            pass

        self._scroll()
        cards = self.driver.find_elements(By.CSS_SELECTOR, "li.react-job-listing")
        log.info(f"Glassdoor: {len(cards)} jobs for {role} @ {location}")

        for card in cards:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "a[data-test='job-title']")
                company_el = card.find_element(By.CSS_SELECTOR, "[data-test='employer-short-name']")
                loc_el = card.find_element(By.CSS_SELECTOR, "[data-test='emp-location']")
                jobs.append(JobListing(
                    platform="glassdoor",
                    title=title_el.text.strip(),
                    company=company_el.text.strip(),
                    location=loc_el.text.strip(),
                    job_url="https://www.glassdoor.co.in" + title_el.get_attribute("href"),
                ))
            except NoSuchElementException:
                continue

        return jobs

    def apply_to_job(self, job: JobListing) -> bool:
        """Glassdoor redirects to company sites — log and mark accordingly."""
        self.driver.get(job.job_url)
        human_delay(2, 4)
        try:
            apply_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='applyButton']"))
            )
            href = apply_btn.get_attribute("href") or ""
            if "glassdoor" not in href:
                log.info("Glassdoor external apply", extra={"url": job.job_url})
                safe_click(self.driver, apply_btn)
                return True
        except TimeoutException:
            pass
        return False

    def _scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 700)")
            time.sleep(random.uniform(0.4, 0.9))

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
