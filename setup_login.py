"""
First-time setup: Opens each platform in a real Chrome browser window.
You log in with Google ONCE -- sessions are saved permanently.
Run this ONCE before scheduling daily automation.
"""
import os
import sys
import time

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Force visible browser (not headless) for setup
os.environ["HEADLESS"] = "false"

from dotenv import load_dotenv
load_dotenv()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PROFILE_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "browser_profiles")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "praneethssr.2002@gmail.com")


def p(msg):
    """Print with flush so output appears immediately."""
    print(msg, flush=True)


def get_driver(profile_name: str) -> uc.Chrome:
    profile_dir = os.path.join(PROFILE_BASE, profile_name)
    os.makedirs(profile_dir, exist_ok=True)
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    driver = uc.Chrome(options=options, version_main=None)
    driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return driver


def wait_for_login(driver, check_fn, platform: str, timeout: int = 300):
    """Poll until check_fn returns True or timeout."""
    p(f"\n  [ACTION REQUIRED] Log in with Google in the {platform} browser window.")
    p(f"  Waiting up to {timeout//60} minutes for you to finish...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if check_fn(driver):
                p(f"  [OK] {platform} login confirmed!")
                time.sleep(2)
                return True
        except Exception:
            pass
        time.sleep(3)
    p(f"  [TIMEOUT] {platform} login not detected. Session may still be saved if you logged in.")
    return False


# ─────────────────────────────────────────────
# NAUKRI
# ─────────────────────────────────────────────
def naukri_logged_in(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR,
            ".nI-gNb-drawer__icon, .nI-gNb-info, [data-ga-track='user_icon']")
        return True
    except NoSuchElementException:
        url = driver.current_url
        return "naukri.com" in url and "login" not in url and "nlogin" not in url


def setup_naukri():
    p("\n" + "="*60)
    p("STEP 1/4  --  NAUKRI.COM")
    p("="*60)
    driver = get_driver("naukri")
    try:
        driver.get("https://www.naukri.com")
        time.sleep(4)

        if naukri_logged_in(driver):
            p("  [OK] Already logged in to Naukri!")
            return True

        driver.get("https://www.naukri.com/nlogin/login")
        time.sleep(3)

        # Try Google button
        clicked = False
        for xpath in [
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//span[contains(.,'Google')]/..",
        ]:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                time.sleep(3)
                clicked = True
                p("  Google button clicked on Naukri.")
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not clicked:
            p("  Could not find Google button -- log in manually in the browser window.")

        # Handle Google OAuth popup
        time.sleep(2)
        wins = driver.window_handles
        if len(wins) > 1:
            driver.switch_to.window(wins[-1])
            time.sleep(2)
            try:
                ef = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                for c in CANDIDATE_EMAIL:
                    ef.send_keys(c)
                    time.sleep(0.04)
                driver.find_element(By.ID, "identifierNext").click()
                time.sleep(2)
                p(f"  Email entered: {CANDIDATE_EMAIL}")
                p("  --> Enter your Google password in the popup, then press Next.")
            except NoSuchElementException:
                p("  --> Select your Google account or enter credentials in the popup.")
            driver.switch_to.window(wins[0])

        return wait_for_login(driver, naukri_logged_in, "Naukri", timeout=300)
    finally:
        p("  Naukri browser profile saved.")
        try:
            driver.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────
# LINKEDIN
# ─────────────────────────────────────────────
def linkedin_logged_in(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR,
            ".global-nav__me-photo, nav.global-nav, .feed-identity-module")
        return True
    except NoSuchElementException:
        url = driver.current_url
        return "/feed" in url or "/mynetwork" in url or "/in/" in url


def setup_linkedin():
    p("\n" + "="*60)
    p("STEP 2/4  --  LINKEDIN")
    p("="*60)
    driver = get_driver("linkedin")
    try:
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(4)

        if linkedin_logged_in(driver):
            p("  [OK] Already logged in to LinkedIn!")
            return True

        driver.get("https://www.linkedin.com/login")
        time.sleep(3)

        try:
            ef = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, "username")))
            ef.clear()
            for c in CANDIDATE_EMAIL:
                ef.send_keys(c)
                time.sleep(0.04)
            p(f"  Email pre-filled: {CANDIDATE_EMAIL}")
            p("  --> Enter your LinkedIn password in the browser window, then click Sign in.")
        except TimeoutException:
            p("  --> Enter your LinkedIn credentials in the browser window.")

        return wait_for_login(driver, linkedin_logged_in, "LinkedIn", timeout=300)
    finally:
        p("  LinkedIn browser profile saved.")
        try:
            driver.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────
# INDEED
# ─────────────────────────────────────────────
def indeed_logged_in(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR,
            ".gnav-LoggedInUser, #gnav-user, .icl-Avatar, [data-testid='gnav-user-container']")
        return True
    except NoSuchElementException:
        url = driver.current_url
        return "indeed.com" in url and "login" not in url and "account" not in url and "secure" not in url


def setup_indeed():
    p("\n" + "="*60)
    p("STEP 3/4  --  INDEED")
    p("="*60)
    driver = get_driver("indeed")
    try:
        driver.get("https://in.indeed.com/jobs?q=devops")
        time.sleep(4)

        if indeed_logged_in(driver):
            p("  [OK] Already logged in to Indeed!")
            return True

        driver.get("https://secure.indeed.com/account/login")
        time.sleep(3)

        clicked = False
        for xpath in [
            "//*[@data-tn-element='GoogleSignIn']",
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//div[contains(.,'Continue with Google')]",
        ]:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                time.sleep(3)
                clicked = True
                p("  Google button clicked on Indeed.")
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not clicked:
            p("  --> Click 'Continue with Google' manually in the Indeed browser window.")

        # Handle popup
        time.sleep(2)
        wins = driver.window_handles
        if len(wins) > 1:
            driver.switch_to.window(wins[-1])
            time.sleep(2)
            try:
                divs = driver.find_elements(By.CSS_SELECTOR, "[data-identifier]")
                for d in divs:
                    if CANDIDATE_EMAIL.lower() in (d.get_attribute("data-identifier") or "").lower():
                        d.click()
                        p(f"  Google account selected: {CANDIDATE_EMAIL}")
                        break
            except Exception:
                pass
            driver.switch_to.window(wins[0])

        return wait_for_login(driver, indeed_logged_in, "Indeed", timeout=300)
    finally:
        p("  Indeed browser profile saved.")
        try:
            driver.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────
# GLASSDOOR
# ─────────────────────────────────────────────
def glassdoor_logged_in(driver) -> bool:
    try:
        driver.find_element(By.CSS_SELECTOR,
            ".SVGInline.avatar, [data-test='user-menu'], .userMenu, .dropdown-avatar")
        return True
    except NoSuchElementException:
        url = driver.current_url
        return "glassdoor" in url and "login" not in url and "signin" not in url and "profile" not in url


def _close_modal(driver):
    for sel in ["[alt='Close']", "button.modal_closeIcon", "[data-test='close']", "button[class*='close']"]:
        try:
            driver.find_element(By.CSS_SELECTOR, sel).click()
            time.sleep(0.5)
            return
        except NoSuchElementException:
            continue


def setup_glassdoor():
    p("\n" + "="*60)
    p("STEP 4/4  --  GLASSDOOR")
    p("="*60)
    driver = get_driver("glassdoor")
    try:
        driver.get("https://www.glassdoor.co.in/Job/index.htm")
        time.sleep(4)
        _close_modal(driver)

        if glassdoor_logged_in(driver):
            p("  [OK] Already logged in to Glassdoor!")
            return True

        driver.get("https://www.glassdoor.co.in/profile/login_input.htm")
        time.sleep(3)
        _close_modal(driver)

        clicked = False
        for xpath in [
            "//a[contains(@href,'google')]",
            "//button[contains(.,'Google')]",
            "//*[contains(@class,'google')]//button",
        ]:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                time.sleep(3)
                clicked = True
                p("  Google button clicked on Glassdoor.")
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not clicked:
            p("  --> Click 'Continue with Google' manually in the Glassdoor browser window.")

        # Handle popup
        time.sleep(2)
        wins = driver.window_handles
        if len(wins) > 1:
            driver.switch_to.window(wins[-1])
            time.sleep(2)
            try:
                divs = driver.find_elements(By.CSS_SELECTOR, "[data-identifier]")
                for d in divs:
                    if CANDIDATE_EMAIL.lower() in (d.get_attribute("data-identifier") or "").lower():
                        d.click()
                        p(f"  Google account selected: {CANDIDATE_EMAIL}")
                        break
            except Exception:
                pass
            driver.switch_to.window(wins[0])

        return wait_for_login(driver, glassdoor_logged_in, "Glassdoor", timeout=300)
    finally:
        p("  Glassdoor browser profile saved.")
        try:
            driver.quit()
        except Exception:
            pass


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    p("\n" + "="*60)
    p("  JOBBOT -- PLATFORM LOGIN SETUP")
    p("  A Chrome window will open for each platform.")
    p("  Sign in with Google when the browser opens.")
    p("  Your session will be saved permanently.")
    p("="*60)
    p(f"\n  Google account: {CANDIDATE_EMAIL}\n")

    results = {}
    results["naukri"]    = setup_naukri()
    results["linkedin"]  = setup_linkedin()
    results["indeed"]    = setup_indeed()
    results["glassdoor"] = setup_glassdoor()

    p("\n" + "="*60)
    p("  SETUP RESULTS")
    p("="*60)
    for platform, ok in results.items():
        status = "[OK]   Ready" if ok else "[FAIL] Re-run setup"
        p(f"  {platform.capitalize():<12}  {status}")

    p("")
    failed = [pf for pf, ok in results.items() if not ok]
    if not failed:
        p("  All 4 platforms authenticated!")
        p("  Run daily automation:  python run_daily.py")
        p("  Schedule daily task:   setup_scheduler.bat (as Admin)")
    else:
        p(f"  Failed: {', '.join(failed)}")
        p("  Re-run this script to retry failed platforms.")
    p("="*60)


if __name__ == "__main__":
    main()
