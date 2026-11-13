"""
rating_engine.py
Enterprise Price Comparator

This file acts as a high-speed "Data Recovery Engine." If a platform hides 
the product's rating or review count on the main search page, this engine 
briefly visits the actual product page in the background to fetch the missing details.
"""

import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils import clean_rating

# ==========================================================
# BACKGROUND FETCH (Used by Flipkart for Review Counts)
# ==========================================================
def fetch_html_background(driver, url):
    """
    Attempts to download a webpage's code silently in the background 
    without actually opening a new visual tab.
    """
    if not url: return None
    try:
        # A small script to fetch the webpage data behind the scenes
        script = """
        var url = arguments[0];
        var callback = arguments[1];
        fetch(url)
            .then(r => r.text())
            .then(html => callback(html))
            .catch(err => callback(null));
        """
        html = driver.execute_async_script(script, url)
        if html: return html
    except Exception:
        pass
    return None

# ==========================================================
# FOREGROUND TAB FETCH (JSON-LD + Dynamic CSS)
# ==========================================================
def open_new_tab(driver, url):
    """
    Opens a new browser tab to visit the specific product page 
    and waits until the basic structure of the page has loaded.
    """
    if not url: return False
    try:
        # Open a blank tab and switch the automated browser's focus to it
        driver.execute_script("window.open('about:blank');")
        driver.switch_to.window(driver.window_handles[-1])
        
        # Navigate to the product link
        driver.get(url)
        
        # Wait up to 8 seconds for the webpage's 'body' to appear
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except Exception:
        return False

def close_current_tab(driver, original_tab):
    """
    Closes the temporary product tab and switches the browser's 
    focus back to the original search results page.
    """
    try:
        if driver.current_window_handle != original_tab:
            driver.close()
    except Exception: pass
    
    try: 
        driver.switch_to.window(original_tab)
    except Exception: pass

def fetch_dynamic_rating(driver, url, selectors):
    """
    The main recovery function. It visits the product page and hunts for 
    the missing star ratings and review counts using multiple advanced methods.
    """
    original_tab = driver.current_window_handle
    
    # If we can't open the page, return standard defaults
    if not open_new_tab(driver, url):
        return "Unrated", 0

    rating = "Unrated"
    review_count = 0
    
    try:
        start_time = time.time()
        
        # Give the page a maximum of 3.5 seconds to reveal its data
        while time.time() - start_time < 3.5:
            time.sleep(0.4)
            
            # ------------------------------------------------------
            # A. JSON-LD (Lightning Fast Backend Data)
            # ------------------------------------------------------
            # First, check the website's hidden "data scripts" (JSON-LD) 
            # which often contain exact ratings before the page visually loads.
            try:
                scripts = driver.find_elements(By.XPATH, "//script[@type='application/ld+json']")
                for script in scripts:
                    content = script.get_attribute('innerHTML')
                    
                    # Extract the numerical star rating
                    if "ratingValue" in content and rating == "Unrated":
                        match = re.search(r'"ratingValue"\s*:\s*"?([0-9.]+)"?', content)
                        if match:
                            r = clean_rating(match.group(1))
                            if r != "Unrated": rating = r
                            
                    # Extract the total number of reviews
                    if "reviewCount" in content or "ratingCount" in content:
                        match = re.search(r'"(?:reviewCount|ratingCount)"\s*:\s*"?([\d,]+)"?', content)
                        if match:
                            review_count = int(match.group(1).replace(",", ""))
            except Exception: pass

            # ------------------------------------------------------
            # B. CSS SELECTORS (Standard UI fallback)
            # ------------------------------------------------------
            # If the hidden data failed, scan the visible text on the webpage
            if rating == "Unrated" or review_count == 0:
                try:
                    # Grab all the visible text on the screen
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    
                    # Look for explicit labels like "7 Ratings"
                    if review_count == 0:
                        match = re.search(r"([\d,]+)\s*Ratings?", page_text, re.IGNORECASE)
                        if match: review_count = int(match.group(1).replace(",", ""))
                        
                    # Advanced check: Look for naked numbers next to star ratings
                    if review_count == 0:
                        match = re.search(r"(?:[1-5]\.\d)[^\da-zA-Z]{1,10}?\b([\d,]+)\b(?!\s*(?:inch|cm|gb|tb|hz|kg|w|\.\d))", page_text, re.IGNORECASE)
                        if match: review_count = int(match.group(1).replace(",", ""))
                except Exception: pass

                # If the rating is still missing, try clicking through specific HTML elements
                if rating == "Unrated":
                    for css in selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, css)
                            for element in elements:
                                text = element.text or element.get_attribute("aria-label") or ""
                                r = clean_rating(text)
                                if r != "Unrated": 
                                    rating = r
                                    break
                            if rating != "Unrated": break
                        except Exception: pass

            # ------------------------------------------------------
            # C. EXIT CONDITION
            # ------------------------------------------------------
            # If we successfully found both pieces of data, stop searching to save time
            if rating != "Unrated" and review_count > 0:
                return rating, review_count

        return rating, review_count

    except Exception:
        # If the page completely crashes, return the safe defaults
        return "Unrated", 0
    finally:
        # Guarantee that the temporary tab is closed so the computer doesn't slow down
        close_current_tab(driver, original_tab)

# ==========================================================
# EXPORTS (Platform Specific Rules)
# ==========================================================
# These functions pass specific HTML tags to the engine depending on the website.

def get_amazon_rating(driver, url):
    selectors = [
        "span[data-hook='rating-out-of-text']",
        "span.a-icon-alt",
        "#acrPopover span.a-size-base",
        "#acrPopover"
    ]
    return fetch_dynamic_rating(driver, url, selectors)

def get_flipkart_rating(driver, url):
    selectors = [
        "div.XQDdHH",
        "span.XQDdHH",
        "div._3LWZlK",
        "[aria-label*='Rating']",
        "[aria-label*='rating']",
        "div._2d4LTz"
    ]
    return fetch_dynamic_rating(driver, url, selectors)

def get_reliance_rating(driver, url):
    selectors = [
        "span.rating",
        "div.rating",
        "span.star-rating",
        "div.star-rating",
        ".rui-rating-star",
        "[class*='rating']",
        ".pdp__rating"
    ]
    return fetch_dynamic_rating(driver, url, selectors)