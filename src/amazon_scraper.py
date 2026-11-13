"""
amazon_scraper.py
Enterprise Price Comparator

This file handles the automated scraping of Amazon. It is responsible for 
opening search pages, extracting product details, and structuring the data.
"""

import time
import re
from selenium.webdriver.common.by import By

# Importing custom tools and configurations for the project
from src.browser import open_page, wait_for_presence, scroll_page, close_popup, safe_text, safe_attribute
from src.utils import clean_price, clean_rating, title_matches, is_duplicate
from src.models import Product
from src.logger import info, warning, success
from src.config import SELECTORS, ITEMS_TO_SCRAPE
from src.rating_engine import get_amazon_rating

def scrape_amazon(driver, query):
    """
    Main function to drive the Amazon scraping process. It navigates through 
    search result pages until it collects the required number of products.
    """
    info("Starting Amazon scraper...")
    products = []
    page = 1

    while len(products) < ITEMS_TO_SCRAPE:
        # Construct the search URL for the current page
        search_url = SELECTORS["Amazon"]["url"].format(query=query.replace(" ", "+")) + f"&page={page}"
        info(f"Opening Amazon Page {page}")
        open_page(driver, search_url)
        
        # Wait for the product containers to load on the screen
        try: 
            wait_for_presence(driver, By.CSS_SELECTOR, SELECTORS["Amazon"]["container"])
        except Exception:
            warning("Amazon page failed to load.")
            break
            
        close_popup(driver)
        
        before = len(products)
        # Extract product details from the loaded page
        scrape_current_page(driver, query, products)
        
        # Stop scraping if we reached the target or if no new products were found
        if len(products) >= ITEMS_TO_SCRAPE: break
        if len(products) == before: break
        page += 1

    success(f"Amazon Finished ({len(products)} products)")
    return products

def scrape_current_page(driver, query, products):
    """
    Scrolls down the current page to load all items and processes each product card.
    """
    previous_cards = 0
    retries = 0
    
    # Scroll and wait for elements to load (up to 6 retries if page is slow)
    while retries < 6:
        scroll_page(driver)
        time.sleep(1)
        cards = driver.find_elements(By.CSS_SELECTOR, SELECTORS["Amazon"]["container"])
        
        if len(cards) == previous_cards: retries += 1
        else: retries = 0
        previous_cards = len(cards)

        # Loop through each product container found on the page
        for card in cards:
            if len(products) >= ITEMS_TO_SCRAPE: return
            try:
                # Skip items that aren't visible on the screen
                if not card.is_displayed(): continue
                
                # Extract the data and create a Product object
                product = extract_product(driver, card, query)
                
                # Skip if extraction failed or if we already have this product
                if product is None: continue
                if is_duplicate(products, product.name): continue
                
                products.append(product)
                success(f"Collected {len(products)}/{ITEMS_TO_SCRAPE}")
            except Exception:
                pass

def extract_title(card):
    """
    Attempts to find the product title using a list of known Amazon CSS selectors.
    """
    for css in ["h2 span", "h2 a span", "span.a-size-medium.a-color-base.a-text-normal", "span.a-size-base-plus.a-color-base.a-text-normal", "span.a-size-medium", "span.a-size-base-plus"]:
        title = safe_text(card, css).strip()
        if len(title) > 15: return title.split('\n')[0]
        
    # Fallback to reading raw text lines
    for line in card.text.split("\n"):
        line = line.strip()
        if len(line) > 20 and "₹" not in line and "Sponsored" not in line: return line
    return ""

def extract_price(card):
    """
    Strict CSS Hierarchy to ensure we ONLY grab the primary selling price.
    """
    for css in ["span.a-price-whole", "span.a-price .a-offscreen", "span.a-offscreen"]:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, css)
            for element in elements:
                # Get the text, including hidden attributes if Amazon tries to mask it
                text = element.text.strip() or element.get_attribute("textContent").strip()
                price = clean_price(text)
                
                # Validate that it is a standard product price (excludes accessory/placeholder prices)
                if price and price > 1000:
                    return price
        except Exception:
            continue
            
    return None

def extract_rating(card):
    """
    Searches for the Amazon star rating element.
    """
    for css in ["span.a-icon-alt", "[aria-label*='out of 5 stars']", "i.a-icon-star-small span"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = element.text or element.get_attribute("aria-label") or ""
                rating = clean_rating(text)
                if rating != "Unrated": return rating
        except Exception: pass
    return "Unrated"

def extract_url(card):
    """
    Finds the product link. Fixes partial URLs by prepending the Amazon domain.
    """
    for css in ["h2 a", "a.a-link-normal.s-no-outline", "a.a-link-normal"]:
        href = safe_attribute(card, css, "href")
        if href:
            if href.startswith("/"): href = "https://www.amazon.in" + href
            return href
    return ""

def extract_original_price(card):
    """
    Extracts the original (MRP/crossed-out) price for discount calculations.
    """
    for css in [".a-text-price .a-offscreen", "span.a-price.a-text-price span.a-offscreen", "span[data-strike='true']"]:
        price = clean_price(safe_text(card, css))
        if price: return price
    return None

def extract_review_count(card):
    """
    Extracts the total number of customer reviews.
    """
    for css in ["span.a-size-base.s-underline-text", "a[href*='#customerReviews'] span", "span[aria-label*='ratings']"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = (element.text or element.get_attribute("aria-label") or "")
                match = re.search(r"([\d,]+)", text)
                if match: return int(match.group(1).replace(",", ""))
        except Exception: pass
    return 0

def is_sponsored(card):
    """
    Checks if the product is a sponsored ad.
    """
    return "sponsored" in " ".join(card.text.lower().split())

def extract_product(driver, card, query):
    """
    Compiles all extraction functions, validates the data, and returns a Product object.
    """
    try:
        card_text = card.text.lower()
        
        # Skip items that cannot be purchased
        if "currently unavailable" in card_text or "out of stock" in card_text:
            return None

        # Skip sponsored ads
        if is_sponsored(card): return None

        # Validate title
        title = extract_title(card)
        if not title or not title_matches(title, query): return None

        # Validate price
        price = extract_price(card)
        if not price or price < 1000: return None

        url = extract_url(card)
        rating = extract_rating(card)

        # Missing Rating Recovery: Try to get missing ratings directly from the product page
        if rating == "Unrated" and url:
            try:
                # Retrieve rating from the live product page if missing on the search results
                recovered_rating, _ = get_amazon_rating(driver, url)
                if recovered_rating == "OUT_OF_STOCK":
                    info(f"Dropped -> {title} (Out of Stock on live page)")
                    return None
                elif recovered_rating != "Unrated":
                    rating = recovered_rating
            except Exception:
                pass

        # Calculate discount percentage
        original_price = extract_original_price(card)
        if not original_price or original_price <= price:
            original_price = price
            discount = "0%"
        else:
            try: discount = f"{round((original_price-price)*100/original_price)}%"
            except Exception: discount = "0%"

        review_count = extract_review_count(card)
        
        # ==========================================
        # UNRATED PRODUCT HANDLER
        # ==========================================
        # If the platform hides the star rating due to low volume, 
        # we set the review count to 0 to maintain data consistency.
        if rating == "Unrated":
            review_count = 0

        info(f"Amazon Title : {title}")
        info(f"Amazon Price : ₹{price}")
        success(f"Amazon Accepted -> {title}")

        # Assemble and return the final data model
        return Product(
            platform="Amazon", name=title, price=price, rating=rating,
            url=url, original_price=original_price, discount=discount, review_count=review_count
        )
    except Exception:
        return None