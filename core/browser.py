"""Shared browser factory — returns an undetected Chrome driver (Windows + Linux CI)."""
import os
import time
import random
import platform
import subprocess
import undetected_chromedriver as uc
from core.config import Config
from core.logger import get_logger

log = get_logger("browser")
IS_LINUX = platform.system() == "Linux"


def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    time.sleep(random.uniform(min_s, max_s))


def _get_chrome_version() -> int | None:
    """Detect installed Chrome major version — Windows and Linux."""
    if IS_LINUX:
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ]
    else:
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\%s\AppData\Local\Google\Chrome\Application\chrome.exe" % os.getenv("USERNAME", ""),
        ]
    for p in paths:
        if os.path.exists(p):
            try:
                out = subprocess.check_output([p, "--version"], stderr=subprocess.DEVNULL, timeout=5)
                version_str = out.decode().strip().split()[-1]
                return int(version_str.split(".")[0])
            except Exception:
                pass
    return None


def get_driver(profile_name: str = "default") -> uc.Chrome:
    profile_dir = os.path.abspath(os.path.join(Config.BROWSER_PROFILE_DIR, profile_name))
    os.makedirs(profile_dir, exist_ok=True)

    options = uc.ChromeOptions()

    if Config.HEADLESS:
        # Linux CI: use --headless=new; Windows: legacy --headless
        options.add_argument("--headless=new" if IS_LINUX else "--headless")
        options.add_argument("--disable-gpu")

    # Required for Linux/Docker/CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if IS_LINUX:
        options.add_argument("--shm-size=2gb")
        options.add_argument("--disable-software-rasterizer")

    # Anti-bot and stability flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--lang=en-US,en")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--ignore-certificate-errors")

    chrome_ver = _get_chrome_version()
    log.info(f"Chrome version detected: {chrome_ver}  OS: {platform.system()}")

    try:
        driver = uc.Chrome(
            options=options,
            version_main=chrome_ver,
            use_subprocess=True,
        )
        driver.execute_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        driver.set_page_load_timeout(45)
        log.info("Browser started", extra={"profile": profile_name, "headless": Config.HEADLESS})
        return driver
    except Exception as e:
        log.error("Browser start failed", extra={"error": str(e)})
        raise


def safe_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    human_delay(0.3, 0.7)
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)
    human_delay(0.5, 1.2)


def human_type(element, text: str):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.04, 0.10))
