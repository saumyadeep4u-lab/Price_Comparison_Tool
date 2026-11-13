"""
browser.py
Enterprise Price Comparator

Browser Management
------------------
This file controls the invisible Google Chrome browser that visits the websites. 
It contains specialized rules to prevent the scraper from being detected as a bot, 
handles annoying popups, and scrolls down pages just like a real human would.
"""

# ==========================================================
# IMPORTS
# ==========================================================

import random
import time

# 'undetected_chromedriver' is a special version of Chrome that hides automated behavior
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# Import the maximum time allowed for a page to load from the settings menu
from src.config import PAGE_LOAD_TIMEOUT


# ==========================================================
# BROWSER CLASS
# ==========================================================

class Browser:
    """
    Sets up and configures the automated web browser with stealth settings.
    """

    def __init__(self):
        self.driver = None

    # ------------------------------------------------------

    def start(self):
        """
        Launches the browser and applies multiple anti-detection shields 
        so websites do not block the scraper.
        """
        print("Booting Enterprise Stealth Chrome...")

        options = uc.ChromeOptions()

        # Window Settings: Open the browser fully maximized
        options.add_argument("--start-maximized")

        # Anti-Detection Settings: Turn off flags that tell websites "I am a robot"
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--lang=en-IN")

        # Better Rendering: Disable heavy graphical processing to speed up scraping
        options.add_argument("--disable-gpu")

        # Launch the custom stealth browser
        self.driver = uc.Chrome(
            options=options,
            version_main=150,
            use_subprocess=True
        )

        self.driver.maximize_window()

        # Set a hard time limit for how long the browser will wait for a page to load
        self.driver.set_page_load_timeout(
            PAGE_LOAD_TIMEOUT
        )

        # Advanced Stealth: Hide the internal "webdriver" flag from the browser's system variables
        self.driver.execute_script("""
Object.defineProperty(navigator,'webdriver',{
get:()=>undefined
});
""")

        return self.driver

    # ------------------------------------------------------

    def stop(self):
        """
        Safely shuts down the browser and frees up computer memory.
        """
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass


# ==========================================================
# CREATE DRIVER
# ==========================================================

def create_driver():
    """
    A simple helper function to quickly launch the configured browser.
    """
    browser = Browser()
    return browser.start()

# ==========================================================
# WAIT HELPERS
# ==========================================================
# Websites load data at different speeds. These functions force the script 
# to wait until the required information actually appears on the screen.

def wait_for_presence(
    driver,
    by,
    value,
    timeout=20
):
    """
    Pauses the scraper until a specific element exists in the website's background code.
    """
    return WebDriverWait(
        driver,
        timeout
    ).until(
        EC.presence_of_element_located(
            (
                by,
                value
            )
        )
    )


def wait_for_visible(
    driver,
    by,
    value,
    timeout=20
):
    """
    Pauses the scraper until a specific element becomes physically visible on the screen.
    """
    return WebDriverWait(
        driver,
        timeout
    ).until(
        EC.visibility_of_element_located(
            (
                by,
                value
            )
        )
    )


# ==========================================================
# SAFE PAGE LOAD
# ==========================================================

def open_page(driver, url):
    """
    Attempts to open a webpage. If the page fails or times out, 
    it will retry up to 3 times before giving up.
    """
    attempts = 3

    for attempt in range(attempts):
        try:
            driver.get(url)

            # Wait until the browser signals that the webpage has finished rendering
            WebDriverWait(
                driver,
                15
            ).until(
                lambda d: d.execute_script(
                    "return document.readyState"
                ) == "complete"
            )

            # Pause for a random amount of time (1.5s to 2.5s) to mimic human browsing behavior
            time.sleep(
                random.uniform(
                    1.5,
                    2.5
                )
            )

            return

        except Exception:
            # If the final attempt fails, report the error. Otherwise, wait 2 seconds and try again.
            if attempt == attempts - 1:
                raise
            time.sleep(2)


# ==========================================================
# SMART SCROLL
# ==========================================================

def scroll_page(driver):
    """
    Scrolls down the webpage slowly and naturally, just like a human would. 
    This forces modern "lazy-loading" websites to reveal hidden product images and prices.
    """
    previous_height = 0
    stable = 0

    # Keep scrolling down until the webpage stops getting longer (meaning the bottom was reached)
    while stable < 3:
        driver.execute_script(
            "window.scrollBy(0,700);"
        )

        # Pause for a random fraction of a second between scrolls
        time.sleep(
            random.uniform(
                1.2,
                2.0
            )
        )

        # Check how tall the webpage is now
        current_height = driver.execute_script(
            "return document.body.scrollHeight"
        )

        if current_height == previous_height:
            stable += 1 # The page didn't grow, we might be at the bottom
        else:
            stable = 0  # The page grew, reset the counter
            previous_height = current_height

    # Do one final jump to the absolute bottom of the page to trigger any remaining loads
    driver.execute_script(
        "window.scrollTo(0, document.body.scrollHeight);"
    )
    time.sleep(1.5)


# ==========================================================
# POPUP HANDLER
# ==========================================================

def close_popup(driver):
    """
    Detects annoying location or login popups that block the screen 
    and attempts to close them by pressing 'Escape' or clicking the 'X' button.
    """
    # Attempt 1: Just press the Escape key
    try:
        driver.find_element(
            By.TAG_NAME,
            "body"
        ).send_keys(
            Keys.ESCAPE
        )
    except Exception:
        pass

    # Attempt 2: Search for common "Close" buttons hidden in the code
    popup_selectors = [
        "button._2KpZ6l._2doB4z",
        "button[aria-label='Close']",
        "button.close",
        ".close",
        ".modal-close"
    ]

    for css in popup_selectors:
        try:
            button = driver.find_element(
                By.CSS_SELECTOR,
                css
            )
            # If a close button is visible, click it and stop searching
            if button.is_displayed():
                button.click()
                time.sleep(1)
                break
        except Exception:
            continue

# ==========================================================
# SAFE FIND
# ==========================================================

def safe_find(parent, css):
    """
    Searches for an element on the screen. If it doesn't exist or disappears suddenly, 
    it returns nothing instead of crashing the entire scraper.
    """
    try:
        return parent.find_element(
            By.CSS_SELECTOR,
            css
        )
    except (
        NoSuchElementException,
        StaleElementReferenceException,
        Exception
    ):
        return None


# ==========================================================
# SAFE TEXT
# ==========================================================

def safe_text(parent, css):
    """
    Extracts text from a webpage safely. If standard text extraction fails, 
    it attempts deeper methods to find hidden or dynamically loaded text.
    """
    element = safe_find(
        parent,
        css
    )

    if not element:
        return ""

    # Method A: Standard visible text extraction
    try:
        text = element.text.strip()
        if text:
            return text
    except Exception:
        pass

    # Method B: Extract deeper background text
    try:
        text = element.get_attribute(
            "innerText"
        )
        if text:
            return text.strip()
    except Exception:
        pass

    # Method C: Extract raw, unformatted text content
    try:
        text = element.get_attribute(
            "textContent"
        )
        if text:
            return text.strip()
    except Exception:
        pass

    return ""


# ==========================================================
# SAFE ATTRIBUTE
# ==========================================================

def safe_attribute(
    parent,
    css,
    attribute
):
    """
    Extracts a specific attribute (like a hyperlink URL or an image source) 
    from a webpage element safely.
    """
    element = safe_find(
        parent,
        css
    )

    if not element:
        return ""

    try:
        value = element.get_attribute(
            attribute
        )
        return value if value else ""

    except Exception:
        return ""


# ==========================================================
# SAFE ELEMENT TEXT
# ==========================================================

def safe_element_text(
    parent,
    css
):
    """
    A specialized text extractor used primarily by the Rating Engine 
    to hunt for hidden review counts and star ratings inside HTML tags.
    """
    element = safe_find(
        parent,
        css
    )

    if not element:
        return ""

    # Check multiple possible hiding spots for the rating text
    for attr in (
        "text",
        "innerText",
        "textContent",
        "aria-label"
    ):
        try:
            if attr == "text":
                value = element.text
            else:
                value = element.get_attribute(attr)

            if value:
                return value.strip()
        except Exception:
            continue

    return ""