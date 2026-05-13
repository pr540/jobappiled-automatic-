"""
First-time setup: Opens each platform in a real Chrome browser window.
You log in with Google ONCE — sessions are saved permanently.
Run this ONCE before scheduling daily automation.
"""
import os
import sys
import time

# Force non-headless for setup
os.environ["HEADLESS"] = "false"
from dotenv import load_dotenv
load_dotenv()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PROFILE_BASE = os.path.join(os.path.dirname(__file__), "data", "browser_profiles")
CANDIDATE_EMAIL = os.getenv("CANDIDATE_EMAIL", "praneethssr.2002@gmail.com")


def get_driver(profile_name: str) -> uc.Chrome:
    profile_dir = os.path.join(PROFILE_BASE, profile_name)
    os.makedirs(profile_dir, exist_ok=True)
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1200,800")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    driver = uc.Chrome(options=options, version_main=None)
    driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    return driver


def wait_for_login(driver, success_url_part: str, platform: str, timeout: int = 120):
    """Wait until the user finishes Google login."""
    print(f"\n  [ACTION REQUIRED] Complete Google login for {platform} in the browser window.")
    print(f"  Waiting up to {timeout}s for you to finish...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if success_url_part in driver.current_url:
                print(f"  ✓ {platform} login detected!")
                return True
        except Exception:
            pass
        time.sleep(2)
    print(f"  ✗ Timeout waiting for {platform} login.")
    return False


def setup_naukri():
    print("\n" + "="*60)
    print("STEP 1/4 — NAUKRI LOGIN")
    print("="*60)
    driver = get_driver("naukri")
    try:
        driver.get("https://www.naukri.com/nlogin/login")
        time.sleep(3)

        # Check already logged in
        if "mnjuser" in driver.current_url or "myapps" in driver.current_url:
            print("  ✓ Already logged in to Naukri!")
            time.sleep(2)
            return True

        # Click Google login button
        try:
            google_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(@href,'google')] | //button[contains(.,'Google')] | //span[contains(.,'Google')]/.."
                ))
            )
            google_btn.click()
            time.sleep(3)
        except TimeoutException:
            print("  Google button not found — try logging in manually in the browser.")

        # If Google popup opened
        windows = driver.window_handles
        if len(windows) > 1:
            driver.switch_to.window(windows[-1])
            time.sleep(2)
            # Pre-fill email
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
                email_field.clear()
                for c in CANDIDATE_EMAIL:
                    email_field.send_keys(c)
                    time.sleep(0.05)
                driver.find_element(By.ID, "identifierNext").click()
                time.sleep(2)
                print(f"  Email pre-filled: {CANDIDATE_EMAIL}")
                print("  Enter your password in the browser window...")
            except NoSuchElementException:
                print("  Fill in your Google credentials in the browser window.")
            driver.switch_to.window(windows[0])

        return wait_for_login(driver, "naukri.com", "Naukri", timeout=180)
    finally:
        print("  Browser profile saved. Closing Naukri window.")
        try:
            driver.quit()
        except Exception:
            pass


def setup_linkedin():
    print("\n" + "="*60)
    print("STEP 2/4 — LINKEDIN LOGIN")
    print("="*60)
    driver = get_driver("linkedin")
    try:
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)

        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            print("  ✓ Already logged in to LinkedIn!")
            time.sleep(2)
            return True

        driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        # Try to pre-fill email
        try:
            email_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.clear()
            for c in CANDIDATE_EMAIL:
                email_field.send_keys(c)
                time.sleep(0.05)
            print(f"  Email pre-filled: {CANDIDATE_EMAIL}")
            print("  Enter your LinkedIn password in the browser, then click Sign in.")
        except TimeoutException:
            print("  Fill in your LinkedIn credentials in the browser window.")

        return wait_for_login(driver, "/feed", "LinkedIn", timeout=180)
    finally:
        print("  Browser profile saved. Closing LinkedIn window.")
        try:
            driver.quit()
        except Exception:
            pass


def setup_indeed():
    print("\n" + "="*60)
    print("STEP 3/4 — INDEED LOGIN")
    print("="*60)
    driver = get_driver("indeed")
    try:
        driver.get("https://secure.indeed.com/account/login")
        time.sleep(3)

        # Check already logged in
        if "indeed.com/myjobs" in driver.current_url or "indeed.com/jobs" in driver.current_url:
            print("  ✓ Already logged in to Indeed!")
            time.sleep(2)
            return True

        # Click Google sign-in
        try:
            google_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(@href,'google')] | //button[contains(.,'Google')] | //*[@data-tn-element='GoogleSignIn']"
                ))
            )
            google_btn.click()
            time.sleep(3)
            print("  Google sign-in clicked.")
        except TimeoutException:
            print("  Google button not auto-found. Click 'Continue with Google' manually in the browser.")

        return wait_for_login(driver, "indeed.com", "Indeed", timeout=180)
    finally:
        print("  Browser profile saved. Closing Indeed window.")
        try:
            driver.quit()
        except Exception:
            pass


def setup_glassdoor():
    print("\n" + "="*60)
    print("STEP 4/4 — GLASSDOOR LOGIN")
    print("="*60)
    driver = get_driver("glassdoor")
    try:
        driver.get("https://www.glassdoor.co.in/profile/login_input.htm")
        time.sleep(3)

        # Check already logged in
        if "glassdoor.co.in/member/" in driver.current_url:
            print("  ✓ Already logged in to Glassdoor!")
            time.sleep(2)
            return True

        # Click Google sign-in
        try:
            google_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//a[contains(@href,'google')] | //button[contains(.,'Google')]"
                ))
            )
            google_btn.click()
            time.sleep(3)
            print("  Google sign-in clicked.")
        except TimeoutException:
            print("  Google button not auto-found. Click 'Continue with Google' manually.")

        return wait_for_login(driver, "glassdoor.co.in", "Glassdoor", timeout=180)
    finally:
        print("  Browser profile saved. Closing Glassdoor window.")
        try:
            driver.quit()
        except Exception:
            pass


def main():
    print("\n" + "="*60)
    print("  JOBBOT — FIRST-TIME LOGIN SETUP")
    print("  This will open each platform in a browser window.")
    print("  Log in with your Google account when prompted.")
    print("  Sessions are saved — you only need to do this ONCE.")
    print("="*60)
    print(f"\n  Google account to use: {CANDIDATE_EMAIL}\n")

    input("  Press ENTER to begin setup...")

    results = {}

    results["naukri"]    = setup_naukri()
    results["linkedin"]  = setup_linkedin()
    results["indeed"]    = setup_indeed()
    results["glassdoor"] = setup_glassdoor()

    print("\n" + "="*60)
    print("  SETUP COMPLETE — Login Results:")
    print("="*60)
    for platform, ok in results.items():
        status = "✓ Ready" if ok else "✗ Failed (re-run setup)"
        print(f"  {platform.capitalize():<12} {status}")

    all_ok = all(results.values())
    print()
    if all_ok:
        print("  All platforms authenticated!")
        print("  You can now run:  python run_daily.py")
        print("  Or schedule it:   setup_scheduler.bat")
    else:
        failed = [p for p, ok in results.items() if not ok]
        print(f"  Re-run setup for: {', '.join(failed)}")
    print("="*60)


if __name__ == "__main__":
    main()
