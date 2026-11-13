"""
reliance_scraper.py
Enterprise Price Comparator

This file is responsible for scanning Reliance Digital. It navigates the website, 
extracts the product details, and handles the specific layout of Reliance web pages.
"""

# ==========================================================
# IMPORTS
# ==========================================================

import re
import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# Import custom browser controls and safe extraction tools
from src.browser import (
    open_page,
    wait_for_presence,
    scroll_page,
    close_popup,
    safe_text,
)

# Import helper functions for cleaning data and checking for duplicates
from src.utils import (
    clean_price,
    title_matches,
    is_duplicate,
)

# Import the standard Product blueprint
from src.models import Product

# Import the logging system to record actions
from src.logger import (
    info,
    warning,
    success,
)

# Import system settings
from src.config import (
    SELECTORS,
    ITEMS_TO_SCRAPE,
)

# Import the backup rating engine
from src.rating_engine import get_reliance_rating


# ==========================================================
# MAIN SCRAPER
# ==========================================================

def scrape_reliance(driver, query):
    """
    The main sequence for scanning Reliance Digital. It loads the search results, 
    scrolls down to reveal all items, and extracts the necessary data point by point.
    """
    info("=" * 60)
    info("Starting Reliance Digital Scraper")
    info("=" * 60)

    products = []
    
    # Format the search link with the exact product name
    base_url = SELECTORS["Reliance"]["url"].format(
        query=query.replace(" ", "%20")
    )

    page = 0
    # Set a hard limit on how many pages to check to prevent infinite scanning
    MAX_PAGES = 3 

    while len(products) < ITEMS_TO_SCRAPE and page < MAX_PAGES:
        # Determine the correct page number formatting for the URL
        if "?" in base_url:
            search_url = f"{base_url}&page={page}"
        else:
            search_url = f"{base_url}?page={page}"

        info(f"Opening Reliance Page {page + 1}")
        open_page(driver, search_url)

        # Wait for the main product container to physically appear on the screen
        try:
            wait_for_presence(
                driver,
                By.CSS_SELECTOR,
                SELECTORS["Reliance"]["container"],
                timeout=20 # Increased timeout to handle slow Reliance servers
            )
        except TimeoutException:
            # If the page takes too long, log a warning and proceed anyway just in case
            warning("Timeout caught. Fast-forcing parse...")
            time.sleep(1.5) 

        # Attempt to dismiss any annoying login or location popups
        close_popup(driver)

        previous_cards = 0
        stagnant = 0
        # Prevent the scraper from scrolling forever if the page gets stuck
        MAX_SCROLLS = 6 

        while True:
            # Find all visible product cards on the screen
            cards = driver.find_elements(
                By.CSS_SELECTOR,
                SELECTORS["Reliance"]["container"]
            )
            
            # If standard cards are not found, attempt a backup search path
            if not cards:
                cards = driver.find_elements(By.CSS_SELECTOR, "li.sp, div.sp__product")

            # If no cards exist at all, exit the scrolling loop
            if not cards:
                break

            # Check if scrolling is actually revealing new products
            if len(cards) == previous_cards:
                stagnant += 1
            else:
                stagnant = 0

            previous_cards = len(cards)

            # Stop scrolling if the bottom of the page is reached
            if stagnant >= MAX_SCROLLS:
                break

            # Process each individual product card found on the screen
            for card in cards:
                # Stop immediately if the required number of items has been collected
                if len(products) >= ITEMS_TO_SCRAPE:
                    break
                try:
                    # Skip invisible elements to save time
                    if not card.is_displayed():
                        continue

                    # Quickly check the title to avoid processing known duplicates
                    temp_title = extract_title(card)
                    if temp_title and is_duplicate(products, temp_title):
                        continue

                    # Extract all the data from the card
                    product = extract_product(driver, card, query)

                    # If the extraction failed or it wasn't a match, skip to the next card
                    if product is None:
                        continue

                    # Double-check for duplicates just to be safe
                    if is_duplicate(products, product.name):
                        continue

                    # Add the verified product to the final list
                    products.append(product)
                    success(f"Collected {len(products)}/{ITEMS_TO_SCRAPE}")

                except Exception:
                    pass

            if len(products) >= ITEMS_TO_SCRAPE:
                break

            # Scroll down to force the website to load more items
            scroll_page(driver)
            time.sleep(0.3) 
            
        page += 1

    success(f"Reliance Finished ({len(products)} products)")
    return products

# ==========================================================
# TITLE EXTRACTION
# ==========================================================

def extract_title(card):
    """
    Hunts for the product's full name using various known text locations.
    """
    selectors = [
        "div.product-card-title", # NEW: Injected exact class name from latest website update
        "p.sp__name",
        "div.product-name",
        "div.product-title",
        "h2",
        "h3",
        "a[title]",
        "a"
    ]

    # Check common HTML tags first
    for css in selectors:
        title = safe_text(card, css).strip()
        if len(title) > 15:
            # Filter out random promotional text lines
            lines = [line.strip() for line in title.split('\n') if len(line.strip()) > 15 and "OFFER" not in line.upper()]
            if lines:
                return max(lines, key=len)

    # Fallback method: Scan all visible text for the longest valid sentence
    for line in card.text.split("\n"):
        line = line.strip()
        if (
            len(line) > 20
            and "₹" not in line
            and "%" not in line
            and "Delivery" not in line
            and "FREE" not in line.upper()
            and "OFFER" not in line.upper()
        ):
            return line

    return ""

# ==========================================================
# PRICE EXTRACTION
# ==========================================================

def extract_price(card):
    """
    Locates the current selling price of the item.
    """
    selectors = [
        "span.price",
        "span.sale-price",
        "span.TextWeb__Text-sc-1cyx778-0",
        "div.price",
        "span[data-testid='price']",
        "span"
    ]

    for css in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, css)
            for element in elements:
                text = element.text.strip()
                if "₹" not in text:
                    continue
                price = clean_price(text)
                if price and price > 0:
                    return price
        except Exception:
            continue
            
    # Fallback method: Search the raw text for a currency symbol next to numbers
    try:
        match = re.search(r"₹\s*([\d,]+)", card.text[:100]) 
        if match:
            price = clean_price(match.group(0))
            if price > 0:
                return price
    except Exception:
        pass
        
    return None

# ==========================================================
# ORIGINAL PRICE (MRP) EXTRACTION
# ==========================================================

def extract_original_price(card):
    """
    Locates the crossed-out Maximum Retail Price (MRP).
    """
    try:
        card_text = card.text
        match = re.search(r"MRP\s*[\n:]*\s*₹\s*([\d,]+)", card_text, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
    except Exception:
        pass

    selectors = [
        "span.old-price",
        "span.strike-price",
        "span.original-price",
        "del",
        "s"
    ]
    for css in selectors:
        price = clean_price(safe_text(card, css))
        if price:
            return price
            
    # Fallback method: If two prices are visible, assume the higher one is the MRP
    try:
        matches = re.findall(r"₹\s*([\d,]+)", card.text)
        prices = []
        for match in matches:
            val = int(match.replace(",", ""))
            prices.append(val)
        if len(prices) > 1:
            return max(prices)
    except Exception:
        pass
        
    return None

# ==========================================================
# RATING
# ==========================================================

def extract_rating(card):
    """
    Extracts the star rating (e.g., 4.5 out of 5).
    """
    selectors = [
        "span.rating",
        "div.rating",
        "span.star-rating",
        "div.star-rating",
        "[aria-label*='Rating']",
        "[aria-label*='rating']",
        "[class*='rating']"
    ]

    for css in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, css)
            for element in elements:
                text = element.text.strip()
                if text:
                    match = re.search(r"\b([1-5]\.[0-9])\b", text)
                    if match:
                        rating = match.group(1)
                        return rating
        except Exception:
            continue
    return "Unrated"

# ==========================================================
# PRODUCT URL
# ==========================================================

def extract_url(card):
    """
    Finds the direct hyperlink to the product's purchase page.
    """
    selectors = [
        "a.details-container", # NEW: Injected exact class name from latest website update
        "a[href*='/product/']",
        "a[href*='/products/']",
        "a[href*='/p/']",
        "a[href]",
    ]

    for css in selectors:
        try:
            links = card.find_elements(By.CSS_SELECTOR, css)
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue

                # Rebuild the link if it is incomplete
                if href.startswith("/"):
                    href = "https://www.reliancedigital.in" + href
                
                if "reliancedigital.in" in href and (
                    "/product/" in href or "/products/" in href
                ):
                    return href.split("?")[0]
        except Exception:
            continue
    
    return ""

# ==========================================================
# REVIEW COUNT EXTRACTION
# ==========================================================

def extract_review_count(card):
    """
    Extracts the total number of customer reviews.
    """
    selectors = [
        "span.rating", "div.rating", "span.star-rating", "div.star-rating",
        "[class*='review']", "[class*='rating']"
    ]
    
    for css in selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, css)
            for element in elements:
                text = element.text or element.get_attribute("aria-label") or ""
                match = re.search(r"([\d,]+)\s*Ratings?", text, re.IGNORECASE)
                if match: return int(match.group(1).replace(",", ""))
                match = re.search(r"([\d,]+)\s*Reviews?", text, re.IGNORECASE)
                if match: return int(match.group(1).replace(",", ""))
                match = re.search(r"\(\s*([\d,]+)\s*\)", text)
                if match: return int(match.group(1).replace(",", ""))
                if text.strip().isdigit():
                    return int(text.strip())
        except Exception:
            pass

    # Fallback method: Scan the raw text for numbers next to the word 'Ratings'
    try:
        card_text = card.text
        match = re.search(r"([\d,]+)\s*Ratings?", card_text, re.IGNORECASE)
        if match: return int(match.group(1).replace(",", ""))
        
        match = re.search(r"([\d,]+)\s*Reviews?", card_text, re.IGNORECASE)
        if match: return int(match.group(1).replace(",", ""))
        
        match = re.search(
            r"(?:[1-5]\.\d)[^\da-zA-Z]{1,10}?\b([\d,]+)\b(?!\s*(?:inch|cm|gb|tb|hz|kg|w|\.\d))", 
            card_text, 
            re.IGNORECASE
        )
        if match: return int(match.group(1).replace(",", ""))

    except Exception:
        pass
        
    return 0

# ==========================================================
# ADVERTISEMENT
# ==========================================================

def is_advertisement(card):
    """
    Checks if the item is a paid advertisement so it can be skipped.
    """
    try:
        badges = card.find_elements(
            By.XPATH,
            ".//*[contains(text(),'Sponsored') or contains(text(),'Advertisement')]"
        )
        return len(badges) > 0
    except Exception:
        return False

# ==========================================================
# EXTRACT PRODUCT
# ==========================================================

def extract_product(driver, card, query):
    """
    The central processor for a single item. It calls all the extraction functions 
    above and compiles the data into the standard Product blueprint.
    """
    try:
        # Ignore sponsored items
        if is_advertisement(card):
            return None

        title = extract_title(card)
        if not title:
            return None

        # Verify that the found item actually matches the requested search term
        if not all(word.lower() in title.lower() for word in query.split()): 
            return None

        price = extract_price(card)
        
        # Ignore items that are too cheap (likely accessories, not laptops)
        if not price or price < 10000:
            return None

        url = extract_url(card)
        rating = extract_rating(card)
        review_count = extract_review_count(card)

        # ======================================================
        # BACKGROUND DATA RECOVERY
        # Accepts BOTH Rating and Review Count from the live page
        # ======================================================
        # If the rating is hidden, visit the actual product page behind the scenes
        if (rating == "Unrated" or review_count == 0) and url:
            try:
                recovered_rating, recovered_reviews = get_reliance_rating(driver, url)
                
                if recovered_rating and recovered_rating != "Unrated":
                    rating = recovered_rating
                    
                if recovered_reviews and recovered_reviews > 0:
                    review_count = recovered_reviews
            except Exception:
                pass
        # ======================================================

        original_price = extract_original_price(card)
        
        # Calculate the exact discount percentage based on the final prices
        if not original_price or original_price <= price:
            original_price = price
            discount = "0%"
        else:
            try:
                percentage = round((original_price - price) * 100 / original_price)
                discount = f"{percentage}%"
            except Exception:
                discount = "0%"

        # Record the successful find
        info(f"Title : {title}")
        info(f"Price : ₹{price}")
        success(f"Accepted -> {title}")
        
        # Package the data and send it back to the main list
        return Product(
            platform="Reliance Digital",
            name=title,
            price=price,
            rating=rating,
            url=url,
            original_price=original_price,
            discount=discount,
            review_count=review_count
        )

    except Exception:
        return None