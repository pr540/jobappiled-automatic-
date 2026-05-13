"""Naukri.com — Google login, job search, and apply automation."""
import os
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, WebDriverException,
    StaleElementReferenceException,
)

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

    def _is_alive(self) -> bool:
        try:
            _ = self.driver.current_url
            return True
        except WebDriverException:
            return False

    # ── Authentication ──────────────────────────────────────────
    def login(self) -> bool:
        self._init()
        try:
            self.driver.get(BASE)
            human_delay(3, 5)
        except WebDriverException:
            return False

        if self._logged_in():
            log.info("Naukri: already authenticated")
            return True

        # CI/GitHub Actions: use password login if env var is set
        password = os.getenv("NAUKRI_PASSWORD", "")
        if password:
            return self._login_with_password(password)

        log.info("Naukri: attempting Google login")
        self.driver.get(f"{BASE}/nlogin/login")
        human_delay(2, 4)

        for selector in [
            "//a[contains(@href,'google')]",
            "//button[contains(text(),'Google')]",
            "//*[contains(@class,'google')]",
            "//span[contains(text(),'Google')]/..",
        ]:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                safe_click(self.driver, btn)
                human_delay(2, 4)
                break
            except (TimeoutException, NoSuchElementException):
                continue

        self._handle_google_popup()

        for _ in range(30):
            human_delay(2, 2)
            if self._logged_in():
                log.info("Naukri: login successful")
                return True

        log.warning("Naukri: login did not complete — run setup_login.py first")
        return False

    def _logged_in(self) -> bool:
        try:
            if not self._is_alive():
                return False
            self.driver.find_element(By.CSS_SELECTOR,
                ".nI-gNb-drawer__icon, .nI-gNb-info, [data-ga-track='user_icon'], "
                ".user-name, .nI-gNb-sb__icon-mask--user")
            return True
        except NoSuchElementException:
            try:
                url = self.driver.current_url
                return "naukri.com" in url and "login" not in url and "nlogin" not in url
            except WebDriverException:
                return False

    def _login_with_password(self, password: str) -> bool:
        """Direct email+password login for CI/headless environments."""
        try:
            self.driver.get(f"{BASE}/nlogin/login")
            human_delay(2, 3)
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "input[placeholder*='Email'], input[type='email'], "
                    "#usernameField, input[name='username']"))
            )
            human_type(email_field, Config.CANDIDATE_EMAIL)
            human_delay(0.5, 1)
            pass_field = self.driver.find_element(By.CSS_SELECTOR,
                "input[type='password'], #passwordField, input[name='password']")
            human_type(pass_field, password)
            human_delay(0.5, 1)
            login_btn = self.driver.find_element(By.CSS_SELECTOR,
                "button[type='submit'], .loginButton, button.btn-dark")
            safe_click(self.driver, login_btn)
            human_delay(4, 6)
            if self._logged_in():
                log.info("Naukri: password login successful")
                return True
            log.warning("Naukri: password login failed")
            return False
        except Exception as e:
            log.error(f"Naukri: password login error: {e}")
            return False

    def _handle_google_popup(self):
        human_delay(2, 3)
        try:
            windows = self.driver.window_handles
            if len(windows) > 1:
                self.driver.switch_to.window(windows[-1])
                human_delay(1, 2)
                try:
                    account_divs = self.driver.find_elements(By.CSS_SELECTOR, "[data-identifier]")
                    for div in account_divs:
                        ident = div.get_attribute("data-identifier") or ""
                        if Config.CANDIDATE_EMAIL.lower() in ident.lower():
                            safe_click(self.driver, div)
                            log.info("Naukri: Google account selected")
                            human_delay(2, 3)
                            break
                    else:
                        # No matching account found — click first available
                        if account_divs:
                            safe_click(self.driver, account_divs[0])
                            human_delay(2, 3)
                except Exception:
                    pass
                self.driver.switch_to.window(windows[0])
        except WebDriverException:
            pass

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        if not self._is_alive():
            return []
        jobs: list[JobListing] = []

        role_slug = role.lower().replace(" ", "-")
        loc_slug = location.lower().replace(" ", "-")
        url = (f"{BASE}/{role_slug}-jobs-in-{loc_slug}"
               f"?experience=1,3&jobAge=7&jobtype=1")

        try:
            self.driver.get(url)
            human_delay(3, 5)
        except WebDriverException:
            return []

        src = self.driver.page_source.lower()
        if "no jobs" in src or "0 jobs found" in src or "zero jobs" in src:
            fallback = (f"{BASE}/jobs?q={role.replace(' ', '%20')}"
                        f"&l={location.replace(' ', '%20')}&experience=1,3")
            try:
                self.driver.get(fallback)
                human_delay(3, 5)
            except WebDriverException:
                return []

        self._scroll()

        cards = self.driver.find_elements(By.CSS_SELECTOR,
            "article.jobTuple, div.srp-jobtuple-wrapper, "
            "div[class*='jobTuple'], div[class*='job-tuple'], "
            ".cust-job-tuple")

        log.info(f"Naukri: {len(cards)} cards for '{role}' @ {location}")

        for card in cards[:50]:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except StaleElementReferenceException:
                continue
            except Exception:
                continue
        return jobs

    def _parse_card(self, card) -> JobListing | None:
        try:
            title_el = card.find_element(By.CSS_SELECTOR,
                "a.title, a[class*='title'], .jobTitle a, "
                "a[href*='/job-listings-'], a[href*='naukri.com']")
            try:
                company_el = card.find_element(By.CSS_SELECTOR,
                    ".companyInfo .company-name, span[class*='comp-name'], "
                    "a[class*='comp-name'], .comp-name")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = ""
            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    ".locWdth, span[class*='location'], li[class*='loc'], .loc-wrap")
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
            title = title_el.text.strip()
            if not url or not title:
                return None
            return JobListing(
                platform="naukri",
                title=title,
                company=company,
                location=location,
                job_url=url.split("?")[0],
                experience_required=exp,
            )
        except (NoSuchElementException, StaleElementReferenceException):
            return None

    def _get_job_description(self, job: JobListing) -> str:
        try:
            self.driver.get(job.job_url)
            human_delay(2, 3)
            desc = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    ".job-desc, .dang-inner-html, "
                    "section.styles_job-desc-container__txpYf, "
                    ".jd-desc, [class*='job-desc']"))
            )
            return desc.text[:3000]
        except Exception:
            return ""

    # ── Apply ────────────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        if not self._is_alive():
            raise WebDriverException("Naukri driver session is dead")

        main_window = self.driver.current_window_handle

        try:
            self.driver.get(job.job_url)
            human_delay(2, 4)
        except WebDriverException as e:
            raise

        if self._already_applied():
            log.info("Naukri: already applied", extra={"url": job.job_url})
            return False

        # Check for external apply (redirects to company site — skip)
        page_src = self.driver.page_source.lower()
        if "apply on company site" in page_src or "apply on employer site" in page_src:
            log.info("Naukri: external apply site — skipping", extra={"url": job.job_url})
            return False

        apply_btn = None
        for selector in [
            (By.ID, "apply-button"),
            (By.CSS_SELECTOR, "button.apply-button"),
            (By.CSS_SELECTOR, "button[class*='apply']"),
            (By.CSS_SELECTOR, "a[class*='apply']"),
            (By.XPATH, "//button[contains(text(),'Apply')]"),
            (By.XPATH, "//a[contains(text(),'Apply')]"),
            (By.XPATH, "//button[normalize-space()='Apply']"),
        ]:
            try:
                apply_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(selector)
                )
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not apply_btn:
            log.warning("Naukri: apply button not found", extra={"url": job.job_url})
            return False

        try:
            safe_click(self.driver, apply_btn)
            human_delay(2, 3)
        except (ElementClickInterceptedException, WebDriverException):
            try:
                self.driver.execute_script("arguments[0].click();", apply_btn)
                human_delay(2, 3)
            except WebDriverException:
                return False

        # Handle new tab/window that may open
        all_windows = self.driver.window_handles
        if len(all_windows) > 1:
            new_win = [w for w in all_windows if w != main_window]
            if new_win:
                self.driver.switch_to.window(new_win[0])
                human_delay(1, 2)
                # New tab opened — this is external apply, close and return False
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver.switch_to.window(main_window)
                log.info("Naukri: external tab opened — skipping", extra={"url": job.job_url})
                return False

        # Check if redirected to login (session expired)
        if "login" in self.driver.current_url or "nlogin" in self.driver.current_url:
            log.warning("Naukri: session expired during apply")
            return False

        if self._already_applied():
            return False

        # Handle questionnaire / chatbot overlay
        self._handle_questionnaire()

        # Check if still on page or redirected to success
        human_delay(1, 2)
        if self._already_applied():
            log.info("Naukri: applied", extra={"title": job.title, "company": job.company})
            return True

        # Check for success message
        src = self.driver.page_source.lower()
        if any(kw in src for kw in ["application submitted", "successfully applied",
                                     "application sent", "applied successfully"]):
            log.info("Naukri: applied", extra={"title": job.title, "company": job.company})
            return True

        log.warning("Naukri: apply result unclear — marking as attempted",
                    extra={"url": job.job_url})
        return True  # Assume applied if no error

    def _already_applied(self) -> bool:
        try:
            src = self.driver.page_source.lower()
            if any(kw in src for kw in ["already applied", "application submitted",
                                         "you applied", "applied on"]):
                return True
            self.driver.find_element(By.XPATH,
                "//*[contains(text(),'Already Applied') or "
                "contains(text(),'already applied') or "
                "contains(text(),'You Applied')]")
            return True
        except NoSuchElementException:
            return False
        except WebDriverException:
            return False

    def _handle_questionnaire(self):
        human_delay(1, 2)
        # Try to dismiss modal/overlay first
        for close_sel in [
            "button[aria-label='close']",
            "button[class*='close']",
            ".crossIcon",
            "button.modal__close",
            "[class*='modal'] button[class*='close']",
        ]:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, close_sel)
                if btn.is_displayed():
                    btn.click()
                    human_delay(0.5, 1)
                    return
            except (NoSuchElementException, ElementClickInterceptedException):
                continue

        # Answer any visible yes/no questions
        try:
            radios = self.driver.find_elements(By.CSS_SELECTOR,
                "input[type='radio']:not(:checked)")
            if radios:
                safe_click(self.driver, radios[0])
                human_delay(0.5, 1)
        except Exception:
            pass

        # Click Confirm / Submit / OK if present
        for btn_text in ["Confirm", "Submit", "OK", "Yes", "Continue"]:
            try:
                btn = self.driver.find_element(By.XPATH,
                    f"//button[contains(text(),'{btn_text}')]")
                if btn.is_displayed():
                    safe_click(self.driver, btn)
                    human_delay(1, 2)
                    return
            except (NoSuchElementException, ElementClickInterceptedException):
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
