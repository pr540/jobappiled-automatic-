"""LinkedIn job search and Easy Apply automation."""
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

log = get_logger("linkedin")

BASE_URL = "https://www.linkedin.com"


class LinkedInPlatform(BasePlatform):
    name = "linkedin"

    def __init__(self):
        self.driver = None

    def _init_driver(self):
        if self.driver is None:
            self.driver = get_driver("linkedin")

    def login(self) -> bool:
        self._init_driver()
        self.driver.get(f"{BASE_URL}/feed/")
        human_delay(2, 4)
        if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
            log.info("LinkedIn already authenticated via saved session")
            return True
        log.warning("LinkedIn session expired — manual login required")
        self.driver.get(f"{BASE_URL}/login")
        human_delay(2, 3)
        try:
            email_field = self.driver.find_element(By.ID, "username")
            human_type(email_field, Config.CANDIDATE_EMAIL)
            human_delay(0.5, 1)
            pass_field = self.driver.find_element(By.ID, "password")
            human_type(pass_field, "")  # password entered manually for security
            human_delay(1, 2)
            log.warning("Password field left blank — fill in manually or use session cookie")
        except NoSuchElementException:
            pass
        return False

    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init_driver()
        jobs: list[JobListing] = []
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")
        url = (
            f"{BASE_URL}/jobs/search/?keywords={query}&location={loc}"
            f"&f_E=2,3&f_AL=true&sortBy=DD"
        )
        self.driver.get(url)
        human_delay(3, 5)

        for page in range(3):
            self._scroll_job_list()
            cards = self.driver.find_elements(By.CSS_SELECTOR, ".jobs-search__results-list li")
            log.info(f"LinkedIn page {page+1}: {len(cards)} cards for {role} @ {location}")
            for card in cards:
                try:
                    title_el = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title")
                    company_el = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle")
                    location_el = card.find_element(By.CSS_SELECTOR, ".job-search-card__location")
                    link_el = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link")
                    jobs.append(JobListing(
                        platform="linkedin",
                        title=title_el.text.strip(),
                        company=company_el.text.strip(),
                        location=location_el.text.strip(),
                        job_url=link_el.get_attribute("href").split("?")[0],
                    ))
                except NoSuchElementException:
                    continue

            # Next page
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Page {0}']".format(page + 2))
                safe_click(self.driver, next_btn)
                human_delay(3, 5)
            except NoSuchElementException:
                break

        return jobs

    def _get_job_details(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 4)
            desc_el = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".show-more-less-html__markup"))
            )
            return desc_el.text
        except TimeoutException:
            return ""

    def apply_to_job(self, job: JobListing) -> bool:
        self.driver.get(job.job_url)
        human_delay(2, 4)
        try:
            apply_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".jobs-apply-button"))
            )
            if "Easy Apply" not in apply_btn.text:
                log.info("Not Easy Apply — skipping", extra={"url": job.job_url})
                return False
            safe_click(self.driver, apply_btn)
            human_delay(1, 2)
            self._fill_easy_apply_form()
            return True
        except TimeoutException:
            log.warning("Apply button not found", extra={"url": job.job_url})
            return False

    def _fill_easy_apply_form(self):
        """Step through Easy Apply modal, filling known fields."""
        max_steps = 8
        for _ in range(max_steps):
            human_delay(1, 2)
            # Fill phone if present
            try:
                phone = self.driver.find_element(By.CSS_SELECTOR, "input[id*='phoneNumber']")
                if not phone.get_attribute("value"):
                    human_type(phone, "")
            except NoSuchElementException:
                pass

            # Try to click Next or Submit
            for btn_text in ["Submit application", "Next", "Review"]:
                try:
                    btn = self.driver.find_element(
                        By.XPATH, f"//button[contains(.,'{btn_text}')]"
                    )
                    safe_click(self.driver, btn)
                    if "Submit" in btn_text:
                        log.info("LinkedIn Easy Apply submitted")
                        return
                    break
                except NoSuchElementException:
                    continue

    def fetch_job_descriptions(self, jobs: list[JobListing]) -> list[JobListing]:
        for job in jobs:
            job.job_description = self._get_job_details(job)
            human_delay(1, 2)
        return jobs

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def send_recruiter_connection(self, recruiter_url: str) -> bool:
        self._init_driver()
        self.driver.get(recruiter_url)
        human_delay(2, 4)
        try:
            connect_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Connect')]"))
            )
            safe_click(self.driver, connect_btn)
            human_delay(1, 2)
            # Add a note
            try:
                add_note = self.driver.find_element(By.XPATH, "//button[contains(.,'Add a note')]")
                safe_click(self.driver, add_note)
                note_box = self.driver.find_element(By.ID, "custom-message")
                human_type(note_box, Config.RECRUITER_MESSAGE[:300])
                human_delay(1, 2)
                send_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Send now']")
                safe_click(self.driver, send_btn)
            except NoSuchElementException:
                send_btn = self.driver.find_element(By.XPATH, "//button[contains(.,'Send')]")
                safe_click(self.driver, send_btn)
            log.info("Connection request sent", extra={"url": recruiter_url})
            return True
        except Exception as e:
            log.error("Connection failed", extra={"error": str(e)})
            return False

    def _scroll_job_list(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 600)")
            time.sleep(random.uniform(0.3, 0.7))
