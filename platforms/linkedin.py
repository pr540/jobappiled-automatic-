"""LinkedIn — Google/direct login, job search, Easy Apply automation."""
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

from core.browser import get_driver, human_delay, safe_click, human_type
from core.config import Config
from core.logger import get_logger
from platforms.base import BasePlatform, JobListing

log = get_logger("linkedin")
BASE = "https://www.linkedin.com"


class LinkedInPlatform(BasePlatform):
    name = "linkedin"

    def __init__(self):
        self.driver = None

    def _init(self):
        if not self.driver:
            self.driver = get_driver("linkedin")

    # ── Authentication ──────────────────────────────────────────
    def login(self) -> bool:
        self._init()
        self.driver.get(f"{BASE}/feed/")
        human_delay(3, 5)

        if self._logged_in():
            log.info("LinkedIn: already authenticated")
            return True

        log.info("LinkedIn: attempting login")
        self.driver.get(f"{BASE}/login")
        human_delay(2, 3)

        try:
            email_field = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_type(email_field, Config.CANDIDATE_EMAIL)
            human_delay(0.5, 1.2)
        except TimeoutException:
            pass

        # Wait up to 90s for session to appear (user fills password)
        for _ in range(45):
            human_delay(2, 2)
            if self._logged_in():
                log.info("LinkedIn: login successful")
                return True

        log.warning("LinkedIn: not logged in — run setup_login.py")
        return False

    def _logged_in(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR,
                ".global-nav__me-photo, [data-control-name='identity_welcome_message'], nav.global-nav")
            return True
        except NoSuchElementException:
            url = self.driver.current_url
            return "/feed" in url or "/mynetwork" in url or "/jobs" in url

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        jobs: list[JobListing] = []
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")

        # f_AL=true = Easy Apply only; f_E=2,3 = 1-3 years
        url = (f"{BASE}/jobs/search/?keywords={query}&location={loc}"
               f"&f_E=2,3&f_AL=true&sortBy=DD&f_TPR=r604800")
        self.driver.get(url)
        human_delay(3, 5)

        # Scroll to load more
        for _ in range(4):
            self.driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(random.uniform(0.5, 1.0))

        cards = self.driver.find_elements(By.CSS_SELECTOR,
            ".jobs-search__results-list li, .scaffold-layout__list-item")
        log.info(f"LinkedIn: {len(cards)} results for '{role}' @ {location}")

        for card in cards[:40]:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue
        return jobs

    def _parse_card(self, card) -> JobListing | None:
        try:
            title_el = card.find_element(By.CSS_SELECTOR,
                "h3.base-search-card__title, a.job-card-list__title, h3[class*='title']")
            link_el = card.find_element(By.CSS_SELECTOR,
                "a.base-card__full-link, a.job-card-list__title, a[href*='/jobs/view/']")
            try:
                company_el = card.find_element(By.CSS_SELECTOR,
                    "h4.base-search-card__subtitle, a[data-tracking-control-name*='company']")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = ""
            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    ".job-search-card__location, span[class*='location']")
                location = loc_el.text.strip()
            except NoSuchElementException:
                location = ""

            url = link_el.get_attribute("href") or ""
            url = url.split("?")[0]
            if not url or "/jobs/view/" not in url:
                return None

            return JobListing(
                platform="linkedin",
                title=title_el.text.strip(),
                company=company,
                location=location,
                job_url=url,
            )
        except NoSuchElementException:
            return None

    def _get_job_details(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 4)
            desc = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    ".show-more-less-html__markup, .description__text, section.description"))
            )
            return desc.text[:3000]
        except TimeoutException:
            return ""

    # ── Easy Apply ───────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        self._init()
        self.driver.get(job.job_url)
        human_delay(2, 4)

        # Check "Applied" badge already present
        try:
            self.driver.find_element(By.XPATH, "//*[contains(.,'Applied')][@class[contains(.,'tvm')]]")
            log.info("LinkedIn: already applied", extra={"url": job.job_url})
            return False
        except NoSuchElementException:
            pass

        try:
            apply_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    ".jobs-apply-button, button[data-control-name='jobdetails_topcard_inapply']"))
            )
            btn_text = apply_btn.text.strip()
            if "Easy Apply" not in btn_text and "Apply" not in btn_text:
                log.info("LinkedIn: no Easy Apply", extra={"url": job.job_url})
                return False

            safe_click(self.driver, apply_btn)
            human_delay(1, 2)
            return self._complete_easy_apply()

        except TimeoutException:
            log.warning("LinkedIn: apply button not found", extra={"url": job.job_url})
            return False

    def _complete_easy_apply(self) -> bool:
        """Walk through all Easy Apply modal steps."""
        for step in range(10):
            human_delay(1, 2)

            # Fill phone number if empty
            try:
                phone = self.driver.find_element(By.CSS_SELECTOR,
                    "input[id*='phoneNumber'], input[autocomplete='tel']")
                if not phone.get_attribute("value").strip():
                    human_type(phone, "")  # user fills this in setup
            except NoSuchElementException:
                pass

            # Answer radio questions (select first option)
            try:
                radios = self.driver.find_elements(By.CSS_SELECTOR,
                    "fieldset input[type='radio']")
                for radio in radios[:3]:
                    if not radio.is_selected():
                        safe_click(self.driver, radio)
                        human_delay(0.3, 0.6)
            except Exception:
                pass

            # Fill text inputs that are empty
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR,
                    ".jobs-easy-apply-form-element input[type='text']:not([readonly])")
                for inp in inputs:
                    if not inp.get_attribute("value").strip():
                        human_type(inp, "2")  # default: 2 years
                        human_delay(0.2, 0.4)
            except Exception:
                pass

            # Click Next / Review / Submit
            submitted = False
            for btn_label in ["Submit application", "Submit", "Review", "Next", "Continue"]:
                try:
                    btn = self.driver.find_element(By.XPATH,
                        f"//button[contains(.,'{btn_label}')]")
                    safe_click(self.driver, btn)
                    if "Submit" in btn_label:
                        log.info("LinkedIn: Easy Apply submitted")
                        return True
                    submitted = True
                    break
                except (NoSuchElementException, ElementClickInterceptedException):
                    continue

            if not submitted:
                # Check if modal closed (success)
                try:
                    self.driver.find_element(By.CSS_SELECTOR,
                        ".artdeco-modal--is-showing")
                except NoSuchElementException:
                    log.info("LinkedIn: modal closed — assumed submitted")
                    return True

        return False

    # ── Recruiter Outreach ───────────────────────────────────────
    def send_recruiter_connection(self, recruiter_url: str) -> bool:
        self._init()
        try:
            self.driver.get(recruiter_url)
            human_delay(2, 4)
            connect_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(.,'Connect')]"))
            )
            safe_click(self.driver, connect_btn)
            human_delay(1, 2)

            # Add a note
            try:
                add_note = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Add a note')]"))
                )
                safe_click(self.driver, add_note)
                note_box = self.driver.find_element(By.ID, "custom-message")
                human_type(note_box, Config.RECRUITER_MESSAGE[:295])
                human_delay(1, 2)
            except TimeoutException:
                pass

            send_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[@aria-label='Send now'] | //button[contains(.,'Send')]"))
            )
            safe_click(self.driver, send_btn)
            log.info("LinkedIn: connection request sent", extra={"url": recruiter_url})
            return True
        except Exception as e:
            log.error("LinkedIn: connection failed", extra={"error": str(e)})
            return False

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
