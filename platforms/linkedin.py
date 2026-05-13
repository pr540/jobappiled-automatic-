"""LinkedIn — persistent session login, job search, Easy Apply automation."""
import os
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
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

log = get_logger("linkedin")
BASE = "https://www.linkedin.com"


class LinkedInPlatform(BasePlatform):
    name = "linkedin"

    def __init__(self):
        self.driver = None

    def _init(self):
        if not self.driver:
            self.driver = get_driver("linkedin")

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
            self.driver.get(f"{BASE}/feed/")
            human_delay(3, 5)
        except WebDriverException:
            return False

        if self._logged_in():
            log.info("LinkedIn: already authenticated")
            return True

        # CI/GitHub Actions: use password login if env var is set
        password = os.getenv("LINKEDIN_PASSWORD", "")
        if password:
            return self._login_with_password(password)

        log.info("LinkedIn: attempting login via saved session")
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

        # Wait up to 90s for saved session to activate
        for _ in range(45):
            human_delay(2, 2)
            if self._logged_in():
                log.info("LinkedIn: login successful")
                return True

        log.warning("LinkedIn: not logged in — run setup_login.py first")
        return False

    def _login_with_password(self, password: str) -> bool:
        """Direct email+password login for CI/headless environments."""
        try:
            self.driver.get(f"{BASE}/login")
            human_delay(2, 3)
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            human_type(email_field, Config.CANDIDATE_EMAIL)
            human_delay(0.5, 1)
            pass_field = self.driver.find_element(By.ID, "password")
            human_type(pass_field, password)
            human_delay(0.5, 1)
            pass_field.submit()
            human_delay(4, 6)
            if self._logged_in():
                log.info("LinkedIn: password login successful")
                return True
            log.warning("LinkedIn: password login failed")
            return False
        except Exception as e:
            log.error(f"LinkedIn: password login error: {e}")
            return False

    def _logged_in(self) -> bool:
        try:
            if not self._is_alive():
                return False
            self.driver.find_element(By.CSS_SELECTOR,
                ".global-nav__me-photo, nav.global-nav, "
                "[data-control-name='identity_welcome_message'], "
                ".feed-identity-module, .global-nav__primary-link")
            return True
        except NoSuchElementException:
            try:
                url = self.driver.current_url
                return any(p in url for p in ["/feed", "/mynetwork", "/jobs", "/messaging", "/notifications"])
            except WebDriverException:
                return False

    # ── Job Search ───────────────────────────────────────────────
    def search_jobs(self, role: str, location: str) -> list[JobListing]:
        self._init()
        if not self._is_alive():
            return []
        jobs: list[JobListing] = []
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")

        # f_AL=true = Easy Apply only; f_E=2,3 = Associate+Mid-Senior; sortBy=DD = recent first
        url = (f"{BASE}/jobs/search/?keywords={query}&location={loc}"
               f"&f_E=2,3&f_AL=true&sortBy=DD&f_TPR=r604800")

        try:
            self.driver.get(url)
            human_delay(3, 5)
        except WebDriverException:
            return []

        # Scroll to load all cards
        for _ in range(5):
            self.driver.execute_script("window.scrollBy(0, 800)")
            time.sleep(random.uniform(0.6, 1.2))

        # Try both logged-in and public card selectors
        cards = self.driver.find_elements(By.CSS_SELECTOR,
            ".jobs-search__results-list li, "
            ".scaffold-layout__list-item, "
            "li.ember-view[class*='jobs-search-results'], "
            ".job-card-container")

        if not cards:
            cards = self.driver.find_elements(By.CSS_SELECTOR,
                "li[data-occludable-job-id], div[data-job-id]")

        log.info(f"LinkedIn: {len(cards)} cards for '{role}' @ {location}")

        for card in cards[:40]:
            try:
                job = self._parse_card(card)
                if job:
                    jobs.append(job)
            except (StaleElementReferenceException, NoSuchElementException):
                continue
            except Exception:
                continue
        return jobs

    def _parse_card(self, card) -> JobListing | None:
        try:
            title_el = card.find_element(By.CSS_SELECTOR,
                "h3.base-search-card__title, "
                "a.job-card-list__title, "
                "h3[class*='title'], "
                ".job-card-container__link, "
                "a[class*='job-card']")
            link_el = card.find_element(By.CSS_SELECTOR,
                "a.base-card__full-link, "
                "a.job-card-list__title, "
                "a[href*='/jobs/view/'], "
                "a[class*='job-card']")

            try:
                company_el = card.find_element(By.CSS_SELECTOR,
                    "h4.base-search-card__subtitle, "
                    "a[data-tracking-control-name*='company'], "
                    ".job-card-container__company-name, "
                    "span[class*='company']")
                company = company_el.text.strip()
            except NoSuchElementException:
                company = ""

            try:
                loc_el = card.find_element(By.CSS_SELECTOR,
                    ".job-search-card__location, "
                    "span[class*='location'], "
                    ".job-card-container__metadata-item")
                location = loc_el.text.strip()
            except NoSuchElementException:
                location = ""

            url = link_el.get_attribute("href") or ""
            url = url.split("?")[0]
            title = title_el.text.strip()
            if not url or not title:
                return None
            if "/jobs/view/" not in url and "/jobs/collections/" not in url:
                return None

            return JobListing(
                platform="linkedin",
                title=title,
                company=company,
                location=location,
                job_url=url,
            )
        except (NoSuchElementException, StaleElementReferenceException):
            return None

    def _get_job_details(self, job: JobListing) -> str:
        try:
            if not self._is_alive():
                return ""
            self.driver.get(job.job_url)
            human_delay(2, 4)
            desc = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    ".show-more-less-html__markup, "
                    ".description__text, "
                    "section.description, "
                    ".jobs-description-content__text"))
            )
            return desc.text[:3000]
        except (TimeoutException, WebDriverException):
            return ""

    # ── Easy Apply ───────────────────────────────────────────────
    def apply_to_job(self, job: JobListing) -> bool:
        if not self._is_alive():
            raise WebDriverException("LinkedIn driver session is dead")

        try:
            self.driver.get(job.job_url)
            human_delay(2, 4)
        except WebDriverException as e:
            raise

        # Check already applied
        try:
            src = self.driver.page_source.lower()
            if "applied" in src and ("you applied" in src or "application submitted" in src):
                log.info("LinkedIn: already applied", extra={"url": job.job_url})
                return False
        except WebDriverException:
            pass

        # Find Easy Apply button — try multiple selectors
        apply_btn = None
        for sel in [
            (By.CSS_SELECTOR, ".jobs-apply-button--top-card"),
            (By.CSS_SELECTOR, "button.jobs-apply-button"),
            (By.CSS_SELECTOR, "[data-control-name='jobdetails_topcard_inapply']"),
            (By.XPATH, "//button[contains(@class,'jobs-apply-button')]"),
            (By.XPATH, "//button[contains(text(),'Easy Apply')]"),
            (By.XPATH, "//button[contains(text(),'Apply') and not(contains(text(),'Save'))]"),
        ]:
            try:
                apply_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(sel)
                )
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not apply_btn:
            log.info("LinkedIn: no Easy Apply button", extra={"url": job.job_url})
            return False

        btn_text = apply_btn.text.strip()
        if "Easy Apply" not in btn_text and "Apply" not in btn_text:
            log.info("LinkedIn: button is not Apply", extra={"text": btn_text})
            return False

        try:
            safe_click(self.driver, apply_btn)
            human_delay(1, 2)
        except (ElementClickInterceptedException, WebDriverException):
            try:
                self.driver.execute_script("arguments[0].click();", apply_btn)
                human_delay(1, 2)
            except WebDriverException:
                return False

        return self._complete_easy_apply(job)

    def _complete_easy_apply(self, job: JobListing) -> bool:
        """Walk through all Easy Apply modal steps and submit."""
        for step in range(12):
            human_delay(1.5, 2.5)

            # Dismiss any "how did you find this job" dialog
            try:
                dismiss = self.driver.find_element(By.XPATH,
                    "//button[@aria-label='Dismiss']")
                if dismiss.is_displayed():
                    safe_click(self.driver, dismiss)
                    human_delay(0.5, 1)
                    continue
            except NoSuchElementException:
                pass

            # Fill phone number if empty
            try:
                phones = self.driver.find_elements(By.CSS_SELECTOR,
                    "input[id*='phoneNumber'], input[autocomplete='tel'], "
                    "input[name*='phone']")
                for phone in phones:
                    if phone.is_displayed() and not phone.get_attribute("value").strip():
                        phone.clear()
                        human_type(phone, "9999999999")
                        human_delay(0.3, 0.6)
            except Exception:
                pass

            # Fill years of experience (empty number inputs)
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR,
                    ".jobs-easy-apply-form-element input[type='text']:not([readonly]), "
                    ".jobs-easy-apply-form-element input[type='number']:not([readonly])")
                for inp in inputs:
                    if inp.is_displayed() and not inp.get_attribute("value").strip():
                        human_type(inp, "2")
                        human_delay(0.2, 0.4)
            except Exception:
                pass

            # Select radio — first option
            try:
                radios = self.driver.find_elements(By.CSS_SELECTOR,
                    "fieldset input[type='radio']")
                seen_groups = set()
                for radio in radios:
                    name = radio.get_attribute("name") or ""
                    if name not in seen_groups and not radio.is_selected():
                        safe_click(self.driver, radio)
                        seen_groups.add(name)
                        human_delay(0.3, 0.5)
            except Exception:
                pass

            # Handle select dropdowns — pick first non-empty option
            try:
                selects = self.driver.find_elements(By.CSS_SELECTOR,
                    ".jobs-easy-apply-form-element select")
                for sel in selects:
                    if sel.is_displayed():
                        s = Select(sel)
                        if s.first_selected_option.get_attribute("value") in ("", "Select an option"):
                            for opt in s.options:
                                if opt.get_attribute("value"):
                                    s.select_by_value(opt.get_attribute("value"))
                                    break
                        human_delay(0.3, 0.5)
            except Exception:
                pass

            # Click action button in order of priority
            clicked = False
            for btn_label in ["Submit application", "Submit", "Review", "Next", "Continue"]:
                try:
                    btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH,
                            f"//button[contains(.,'{btn_label}') and "
                            f"not(contains(@class,'cancel')) and "
                            f"not(contains(@aria-label,'Dismiss'))]"))
                    )
                    if btn.is_displayed():
                        safe_click(self.driver, btn)
                        human_delay(1, 2)
                        if "Submit" in btn_label:
                            # Dismiss success modal if it appears
                            self._dismiss_success_modal()
                            log.info("LinkedIn: Easy Apply submitted",
                                     extra={"title": job.title})
                            return True
                        clicked = True
                        break
                except (TimeoutException, NoSuchElementException,
                        ElementClickInterceptedException):
                    continue

            if not clicked:
                # Modal may have closed = success
                try:
                    self.driver.find_element(By.CSS_SELECTOR, ".artdeco-modal--is-showing")
                except NoSuchElementException:
                    log.info("LinkedIn: modal closed — assumed submitted",
                             extra={"title": job.title})
                    return True

        log.warning("LinkedIn: Easy Apply did not complete", extra={"url": job.job_url})
        return False

    def _dismiss_success_modal(self):
        human_delay(1, 2)
        for sel in [
            (By.XPATH, "//button[contains(@aria-label,'Dismiss')]"),
            (By.XPATH, "//button[contains(.,'Not now')]"),
            (By.XPATH, "//button[contains(.,'Done')]"),
            (By.CSS_SELECTOR, "button.artdeco-modal__dismiss"),
        ]:
            try:
                btn = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(sel))
                safe_click(self.driver, btn)
                human_delay(0.5, 1)
                return
            except (TimeoutException, NoSuchElementException):
                continue

    # ── Recruiter Outreach ───────────────────────────────────────
    def send_recruiter_connection(self, recruiter_url: str) -> bool:
        if not self._is_alive():
            return False
        try:
            self.driver.get(recruiter_url)
            human_delay(2, 4)

            connect_btn = None
            for sel in [
                (By.XPATH, "//button[contains(.,'Connect')]"),
                (By.XPATH, "//button[@aria-label[contains(.,'Connect')]]"),
            ]:
                try:
                    connect_btn = WebDriverWait(self.driver, 6).until(
                        EC.element_to_be_clickable(sel)
                    )
                    break
                except TimeoutException:
                    continue

            if not connect_btn:
                # Try "More" menu → Connect
                try:
                    more = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH,
                            "//button[contains(@aria-label,'More actions')]"))
                    )
                    safe_click(self.driver, more)
                    human_delay(0.5, 1)
                    connect_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH,
                            "//li[contains(.,'Connect')]/div"))
                    )
                except TimeoutException:
                    return False

            safe_click(self.driver, connect_btn)
            human_delay(1, 2)

            # Add a note
            try:
                add_note = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[contains(.,'Add a note')]"))
                )
                safe_click(self.driver, add_note)
                note_box = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "custom-message"))
                )
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
            log.error("LinkedIn: connection failed", extra={"error": str(e)[:100]})
            return False

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
