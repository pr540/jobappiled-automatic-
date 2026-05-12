"""Indeed job search and apply automation."""
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

log = get_logger("indeed")

BASE_URL = "https://in.indeed.com"


class IndeedPlatform(BasePlatform):
    name = "indeed"

    def __init__(self):
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            self.driver = get_driver("indeed")

    def login(self) -> bool:
        self._init_driver()
        self.driver.get(f"{BASE_URL}/account/login")
        human_delay(2, 3)
        try:
            google_btn = self.driver.find_element(
                By.XPATH, "//a[contains(@href,'google') or contains(.,'Google')]"
            )
            safe_click(self.driver, google_btn)
            human_delay(3, 5)
            log.info("Indeed Google OAuth triggered — session will persist via profile")
            return True
        except NoSuchElementException:
            log.warning("Google button not found on Indeed login")
            return False

    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init_driver()
        jobs: list[JobListing] = []
        url = f"{BASE_URL}/jobs?q={role.replace(' ', '+')}&l={location.replace(' ', '+')}&fromage=7&explvl=mid_level"
        self.driver.get(url)
        human_delay(3, 5)
        self._scroll()

        cards = self.driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
        log.info(f"Indeed: {len(cards)} results for {role} @ {location}")

        for card in cards:
            try:
                title_el = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
                company_el = card.find_element(By.CSS_SELECTOR, "[data-testid='company-name']")
                loc_el = card.find_element(By.CSS_SELECTOR, "[data-testid='text-location']")
                jobs.append(JobListing(
                    platform="indeed",
                    title=title_el.text.strip(),
                    company=company_el.text.strip(),
                    location=loc_el.text.strip(),
                    job_url="https://in.indeed.com" + title_el.get_attribute("href"),
                ))
            except NoSuchElementException:
                continue

        return jobs

    def apply_to_job(self, job: JobListing) -> bool:
        self.driver.get(job.job_url)
        human_delay(2, 4)
        try:
            apply_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id*='indeedApply']"))
            )
            safe_click(self.driver, apply_btn)
            human_delay(2, 3)
            self._fill_indeed_form()
            return True
        except TimeoutException:
            try:
                ext_btn = self.driver.find_element(By.XPATH, "//a[contains(.,'Apply on company site')]")
                log.info("External apply — skipping", extra={"url": job.job_url})
            except NoSuchElementException:
                pass
            return False

    def _fill_indeed_form(self):
        """Walk through Indeed's multi-step apply form."""
        for _ in range(6):
            human_delay(1, 2)
            for btn_label in ["Continue", "Review your application", "Submit your application"]:
                try:
                    btn = self.driver.find_element(By.XPATH, f"//button[contains(.,'{btn_label}')]")
                    safe_click(self.driver, btn)
                    if "Submit" in btn_label:
                        log.info("Indeed application submitted")
                        return
                    break
                except NoSuchElementException:
                    continue

    def _scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 600)")
            time.sleep(random.uniform(0.3, 0.8))

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
