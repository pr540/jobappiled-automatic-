"""Shared browser factory — returns an undetected Chrome driver."""
import os
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from core.config import Config
from core.logger import get_logger

log = get_logger("browser")


def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    time.sleep(random.uniform(min_s, max_s))


def get_driver(profile_name: str = "default") -> uc.Chrome:
    profile_dir = os.path.join(Config.BROWSER_PROFILE_DIR, profile_name)
    os.makedirs(profile_dir, exist_ok=True)

    options = uc.ChromeOptions()
    if Config.HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    try:
        driver = uc.Chrome(options=options, version_main=None)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        log.info("Browser started", extra={"profile": profile_name})
        return driver
    except Exception as e:
        log.error("Failed to start browser", extra={"error": str(e)})
        raise


def safe_click(driver, element):
    """Scroll to element then click with human delay."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    human_delay(0.3, 0.8)
    element.click()
    human_delay(0.5, 1.5)


def human_type(element, text: str):
    """Type text character by character like a human."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.04, 0.12))
