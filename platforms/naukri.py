"""Naukri.com — Google login, job search, and apply automation."""
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

log = get_logger("naukri")
BASE = "https://www.naukri.com"


class NaukriPlatform(BasePlatform):
    name = "naukri"

    def __init__(self):
        self.driver = None

    def _init(self):
        if not self.driver:
            self.driver = get_driver("naukri")

    # ── Authentication ──────────────────────────────────────────
    def login(self) -> bool:
        self._init()
        self.driver.get(BASE)
        human_delay(3, 5)

        if self._logged_in():
            log.info("Naukri: already authenticated")
            return True

        log.info("Naukri: attempting Google login")
        self.driver.get(f"{BASE}/nlogin/login")
        human_delay(2, 4)

        # Try Google button
        for selector in [
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//*[contains(@class,'google')]",
        ]:
            try:
                btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                safe_click(self.driver, btn)
                human_delay(2, 4)
                break
            except (TimeoutException, NoSuchElementException):
                continue

        # Handle Google OAuth popup
        self._handle_google_popup()

        # Wait up to 60s for login to complete
        for _ in range(30):
            human_delay(2, 2)
            if self._logged_in():
                log.info("Naukri: Google login successful")
                return True

        log.warning("Naukri: login did not complete — use setup_login.py first")
        return False

    def _logged_in(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR,
                ".nI-gNb-drawer__icon, .nI-gNb-info, [data-ga-track='user_icon']")
            return True
        except NoSuchElementException:
            return "naukri.com" in self.driver.current_url and "login" not in self.driver.current_url

    def _handle_google_popup(self):
        human_delay(2, 3)
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            human_delay(1, 2)
            try:
                # Pick the Google account
                account_divs = self.driver.find_elements(By.CSS_SELECTOR, "[data-identifier]")
                for div in account_divs:
                    if Config.CANDIDATE_EMAIL.lower() in (div.get_attribute("data-identifier") or "").lower():
                        safe_click(self.driver, div)
                        log.info("Naukri: Google account selected")
                        human_delay(2, 3)
                        break
            except Exception:
                pass
            self.driver.switch_to.window(windows[0])

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        jobs: list[JobListing] = []

        # Build Naukri search URL
        role_slug = role.lower().replace(" ", "-")
        loc_slug = location.lower().replace(" ", "-")
        url = (f"{BASE}/{role_slug}-jobs-in-{loc_slug}"
               f"?experience=1,3&jobAge=7&jobtype=1")
        self.driver.get(url)
        human_delay(3, 5)

        # Fallback: use search bar
        if "no jobs" in self.driver.page_source.lower() or "0 jobs" in self.driver.page_source.lower():
            url2 = f"{BASE}/jobs/{role.replace(' ', '-').lower()}-jobs?experience=1,3&location={location}"
            self.driver.get(url2)
            human_delay(3, 5)

        self._scroll()
        cards = self.driver.find_elements(By.CSS_SELECTOR,
            "article.jobTuple, div.srp-jobtuple-wrapper, div[class*='jobTuple']")

        log.info(f"Naukri: {len(cards)} results for '{role}' @ {location}")

        for card in cards[:50]:
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
                "a.title, a[class*='title'], .jobTitle a, a[href*='/job-listings-']")
            company_el = card.find_element(By.CSS_SELECTOR,
                ".companyInfo .company-name, span[class*='comp-name'], a[class*='comp-name']")
            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    ".locWdth, span[class*='location'], li[class*='loc']")
                location = loc_el.text.strip()
            except NoSuchElementException:
                location = ""
            try:
                exp_el = card.find_element(By.CSS_SELECTOR,
                    ".expwdth, span[class*='exp'], li[class*='exp']")
                exp = exp_el.text.strip()
            except NoSuchElementException:
                exp = ""

            url = title_el.get_attribute("href") or ""
            if not url:
                return None
            return JobListing(
                platform="naukri",
                title=title_el.text.strip(),
                company=company_el.text.strip(),
                location=location,
                job_url=url.split("?")[0],
                experience_required=exp,
            )
        except NoSuchElementException:
            return None

    def _get_job_description(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 3)
            desc = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    ".job-desc, .dang-inner-html, section.styles_job-desc-container__txpYf"))
            )
            return desc.text[:3000]
        except Exception:
            return ""

    # ── Apply ────────────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        self._init()
        self.driver.get(job.job_url)
        human_delay(2, 4)

        # Check if already applied
        if self._already_applied():
            log.info("Naukri: already applied", extra={"url": job.job_url})
            return False

        # Try "Apply" button
        for selector in [
            "//button[contains(.,'Apply')]",
            "//a[contains(.,'Apply')]",
            "//*[@id='apply-button']",
            "//button[@class[contains(.,'apply')]]",
        ]:
            try:
                btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                safe_click(self.driver, btn)
                human_delay(2, 3)

                # Handle any confirmation / already-applied overlay
                if self._already_applied():
                    return False

                # If chatbot / questionnaire appears, try to close
                self._handle_questionnaire()

                log.info("Naukri: applied", extra={"title": job.title, "company": job.company})
                return True
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException):
                continue

        log.warning("Naukri: apply button not found", extra={"url": job.job_url})
        return False

    def _already_applied(self) -> bool:
        try:
            text = self.driver.find_element(By.XPATH,
                "//*[contains(text(),'Already Applied') or contains(text(),'already applied')]")
            return True
        except NoSuchElementException:
            return False

    def _handle_questionnaire(self):
        """Close or skip any post-apply questionnaire."""
        human_delay(1, 2)
        for close_sel in ["button[class*='close']", "button[aria-label='close']", ".crossIcon"]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, close_sel).click()
                human_delay(0.5, 1)
                return
            except NoSuchElementException:
                continue

    def _scroll(self):
        for _ in range(6):
            self.driver.execute_script("window.scrollBy(0, 700)")
            time.sleep(random.uniform(0.4, 0.9))

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
