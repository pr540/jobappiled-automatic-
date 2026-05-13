"""Glassdoor India — Google login, job search, apply automation."""
import time
import random

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    _SELENIUM_OK = True
except ImportError:
    _SELENIUM_OK = False  # Vercel — browser methods won't be called

from core.browser import get_driver, human_delay, safe_click
from core.config import Config
from core.logger import get_logger
from platforms.base import BasePlatform, JobListing

log = get_logger("glassdoor")
BASE = "https://www.glassdoor.co.in"


class GlassdoorPlatform(BasePlatform):
    name = "glassdoor"

    def __init__(self):
        self.driver = None

    def _init(self):
        if not self.driver:
            self.driver = get_driver("glassdoor")

    # ── Authentication ──────────────────────────────────────────
    def login(self) -> bool:
        self._init()
        self.driver.get(f"{BASE}/Job/index.htm")
        human_delay(3, 5)

        if self._logged_in():
            log.info("Glassdoor: already authenticated")
            return True

        log.info("Glassdoor: attempting Google login")
        self.driver.get(f"{BASE}/profile/login_input.htm")
        human_delay(2, 4)

        # Close any modal first
        self._close_modal()

        for selector in [
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//*[contains(@data-brandviews,'google')]",
            "//div[contains(@class,'google')]//button",
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

        self._handle_google_popup()

        for _ in range(40):
            human_delay(2, 2)
            if self._logged_in():
                log.info("Glassdoor: Google login successful")
                return True

        log.warning("Glassdoor: login not complete — run setup_login.py")
        return False

    def _logged_in(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR,
                ".SVGInline.avatar, [data-test='user-menu'], .userMenu, .dropdown-avatar")
            return True
        except NoSuchElementException:
            url = self.driver.current_url
            return "glassdoor" in url and "login" not in url and "signin" not in url

    def _handle_google_popup(self):
        human_delay(2, 3)
        windows = self.driver.window_handles
        if len(windows) > 1:
            self.driver.switch_to.window(windows[-1])
            human_delay(1, 2)
            try:
                account_divs = self.driver.find_elements(By.CSS_SELECTOR, "[data-identifier]")
                for div in account_divs:
                    if Config.CANDIDATE_EMAIL.lower() in (div.get_attribute("data-identifier") or "").lower():
                        safe_click(self.driver, div)
                        human_delay(2, 3)
                        break
            except Exception:
                pass
            self.driver.switch_to.window(windows[0])

    def _close_modal(self):
        for sel in ["[alt='Close']", "button.modal_closeIcon", "button[class*='close']", "[data-test='close']"]:
            try:
                self.driver.find_element(By.CSS_SELECTOR, sel).click()
                human_delay(0.5, 1)
                return
            except NoSuchElementException:
                continue

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        jobs: list[JobListing] = []

        url = (f"{BASE}/Job/jobs.htm"
               f"?sc.keyword={role.replace(' ', '+')}"
               f"&locT=N&locId=115&fromAge=7"
               f"&jobType=fulltime")
        self.driver.get(url)
        human_delay(3, 5)
        self._close_modal()
        self._scroll()

        cards = self.driver.find_elements(By.CSS_SELECTOR,
            "li.react-job-listing, [data-test='jobListing'], article[class*='job']")
        log.info(f"Glassdoor: {len(cards)} results for '{role}' @ {location}")

        for card in cards[:30]:
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
                "a[data-test='job-title'], .jobLink, a[class*='jobTitle']")
            try:
                company_el = card.find_element(By.CSS_SELECTOR,
                    "[data-test='employer-short-name'], .jobHeader .employerName")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = ""
            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    "[data-test='emp-location'], .jobHeader .subtle")
                location = loc_el.text.strip()
            except NoSuchElementException:
                location = ""

            href = title_el.get_attribute("href") or ""
            if not href:
                return None
            if not href.startswith("http"):
                href = BASE + href

            return JobListing(
                platform="glassdoor",
                title=title_el.text.strip(),
                company=company,
                location=location,
                job_url=href.split("?")[0],
            )
        except NoSuchElementException:
            return None

    def _get_job_description(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 3)
            self._close_modal()
            desc = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "[data-test='jobDescriptionContent'], .desc, .jobDescriptionContent"))
            )
            return desc.text[:3000]
        except Exception:
            return ""

    # ── Apply ────────────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        self._init()
        self.driver.get(job.job_url)
        human_delay(2, 4)
        self._close_modal()

        for selector in [
            "[data-test='applyButton']",
            "button[class*='apply']",
            "a[class*='apply']",
        ]:
            try:
                btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                safe_click(self.driver, btn)
                human_delay(1, 2)
                log.info("Glassdoor: apply clicked", extra={"url": job.job_url})
                return True
            except TimeoutException:
                continue

        log.warning("Glassdoor: apply button not found", extra={"url": job.job_url})
        return False

    def _scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 700)")
            time.sleep(random.uniform(0.4, 0.9))

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
