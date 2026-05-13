"""Indeed India — Google login, job search, Indeed Apply automation."""
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

log = get_logger("indeed")
BASE = "https://in.indeed.com"


class IndeedPlatform(BasePlatform):
    name = "indeed"

    def __init__(self):
        self.driver = None

    def _init(self):
        if not self.driver:
            self.driver = get_driver("indeed")

    # ── Authentication ──────────────────────────────────────────
    def login(self) -> bool:
        self._init()
        self.driver.get(f"{BASE}/jobs?q=devops")
        human_delay(3, 5)

        if self._logged_in():
            log.info("Indeed: already authenticated")
            return True

        log.info("Indeed: attempting Google login")
        self.driver.get("https://secure.indeed.com/account/login")
        human_delay(2, 4)

        for selector in [
            "//*[@data-tn-element='GoogleSignIn']",
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//div[contains(.,'Continue with Google')]",
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
                log.info("Indeed: Google login successful")
                return True

        log.warning("Indeed: login not complete — run setup_login.py")
        return False

    def _logged_in(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR,
                ".gnav-LoggedInUser, #gnav-user, [data-testid='gnav-user-container'], .icl-Avatar")
            return True
        except NoSuchElementException:
            url = self.driver.current_url
            return "indeed.com" in url and "login" not in url and "account" not in url

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

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        jobs: list[JobListing] = []
        url = (f"{BASE}/jobs?q={role.replace(' ', '+')}"
               f"&l={location.replace(' ', '+')}"
               f"&fromage=7&explvl=mid_level&sort=date")
        self.driver.get(url)
        human_delay(3, 5)
        self._scroll()

        cards = self.driver.find_elements(By.CSS_SELECTOR,
            "div.job_seen_beacon, div[class*='jobCard'], li.css-5lfssm")
        log.info(f"Indeed: {len(cards)} results for '{role}' @ {location}")

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
                "h2.jobTitle a, a[data-jk], span[title]")
            try:
                company_el = card.find_element(By.CSS_SELECTOR,
                    "[data-testid='company-name'], .companyName")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = ""
            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    "[data-testid='text-location'], .companyLocation")
                location = loc_el.text.strip()
            except NoSuchElementException:
                location = ""

            href = title_el.get_attribute("href") or ""
            if not href:
                jk = card.get_attribute("data-jk") or card.find_element(
                    By.CSS_SELECTOR, "[data-jk]").get_attribute("data-jk")
                href = f"{BASE}/viewjob?jk={jk}" if jk else ""
            if not href:
                return None

            return JobListing(
                platform="indeed",
                title=title_el.text.strip() or title_el.get_attribute("title") or "",
                company=company,
                location=location,
                job_url=href.split("&")[0],
            )
        except NoSuchElementException:
            return None

    def _get_job_description(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 3)
            desc = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "#jobDescriptionText, .jobsearch-jobDescriptionText"))
            )
            return desc.text[:3000]
        except Exception:
            return ""

    # ── Apply ────────────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        self._init()
        self.driver.get(job.job_url)
        human_delay(2, 4)

        # Indeed Apply button (native apply)
        for selector in [
            "button[id*='indeedApply']",
            "button[class*='indeed-apply']",
            "span.indeed-apply-button",
            "button[data-indeed-apply]",
        ]:
            try:
                btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                safe_click(self.driver, btn)
                human_delay(2, 3)
                return self._complete_indeed_apply()
            except TimeoutException:
                continue

        # External apply — navigate directly (avoids unclosed tab accumulation)
        try:
            ext = self.driver.find_element(By.XPATH,
                "//a[contains(.,'Apply on company site')] | //a[contains(.,'Apply now')]")
            href = ext.get_attribute("href") or ""
            if href:
                self.driver.get(href)
                human_delay(1, 2)
                log.info("Indeed: external apply opened", extra={"url": job.job_url})
                return True
        except NoSuchElementException:
            pass

        log.warning("Indeed: no apply button found", extra={"url": job.job_url})
        return False

    def _complete_indeed_apply(self) -> bool:
        for _ in range(8):
            human_delay(1, 2)
            for btn_label in ["Submit your application", "Submit", "Continue", "Next"]:
                try:
                    btn = self.driver.find_element(By.XPATH,
                        f"//button[contains(.,'{btn_label}')] | //span[contains(.,'{btn_label}')]/..")
                    safe_click(self.driver, btn)
                    if "Submit" in btn_label:
                        log.info("Indeed: application submitted")
                        return True
                    break
                except (NoSuchElementException, Exception):
                    continue
        return False

    def _scroll(self):
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 600)")
            time.sleep(random.uniform(0.4, 0.9))

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
