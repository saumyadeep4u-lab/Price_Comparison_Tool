"""
flipkart_scraper.py
Enterprise Price Comparator

Purpose:
This file acts as our "Digital Shopper" for Flipkart. It knows how to open 
search pages, scroll through the results, and carefully read the information 
(like title, price, and reviews) from the screen.
"""

import time
import re
from selenium.webdriver.common.by import By

# Import our custom tools that help control the browser and clean the data
from src.browser import open_page, wait_for_presence, scroll_page, safe_text, safe_attribute
from src.utils import clean_price, clean_rating, title_matches, is_duplicate
from src.models import Product
from src.logger import info, warning, success
from src.config import SELECTORS, ITEMS_TO_SCRAPE
from src.rating_engine import get_flipkart_rating

# ==========================================================
# THE MAIN CONTROLLER
# ==========================================================

def scrape_flipkart(driver, query):
    """
    This is the main steering wheel for the Flipkart scraper. It opens the 
    browser, goes to Flipkart, searches for your item, and collects the data.
    """
    info("=" * 60)
    info("Starting Flipkart Scraper")
    info("=" * 60)
    
    products = []
    page = 1

    # Keep searching page by page until we have enough products
    while len(products) < ITEMS_TO_SCRAPE:
        # Format the search link to include what the user typed in
        url = SELECTORS["Flipkart"]["url"].format(query=query.replace(" ", "+")) + f"&page={page}"
        info(f"Opening Flipkart Page {page}")
        
        # Tell the browser to open the Flipkart search page
        open_page(driver, url)
        
        # Wait patiently for the product boxes to actually load on the screen
        try: 
            wait_for_presence(driver, By.CSS_SELECTOR, SELECTORS["Flipkart"]["container"])
        except Exception:
            # If the page is broken or too slow, print a warning and stop
            warning("Flipkart page failed.")
            break

        # Remember how many products we had before we started scraping this page
        before = len(products)
        
        # Send the browser to our helper function to scroll and grab the products
        scrape_current_page(driver, query, products)
        
        # If we collected enough products, stop the loop!
        if len(products) >= ITEMS_TO_SCRAPE: break
        
        # If the page didn't give us any new products, we might be at the end of the results
        if len(products) == before: break
        
        # Move on to the next page
        page += 1

    success(f"Flipkart Finished ({len(products)} products)")
    return products


# ==========================================================
# PAGE SCROLLER
# ==========================================================

def scrape_current_page(driver, query, products):
    """
    Scrolls down the current page to load all items and processes each product box.
    """
    previous_count = 0
    retries = 0
    
    # Scroll down the page multiple times to force hidden products to load
    # We allow up to 6 retries just in case the internet is being slow
    while retries < 6:
        scroll_page(driver)
        time.sleep(1) # Give the website a 1-second breather to load images
        
        # Gather all the HTML "boxes" (cards) on the screen that hold product info
        cards = driver.find_elements(By.CSS_SELECTOR, SELECTORS["Flipkart"]["container"])
        
        # Check if scrolling actually revealed any new boxes
        if len(cards) == previous_count: 
            retries += 1
        else: 
            retries = 0
            
        previous_count = len(cards)

        # Loop through every single product box we found on the screen
        for card in cards:
            # Stop immediately if we have collected enough products overall
            if len(products) >= ITEMS_TO_SCRAPE: return
            
            try:
                # Skip this box if it's invisible or hidden on the screen
                if not card.is_displayed(): continue
                
                # Send the box to our inspector function to pull out the price, title, etc.
                product = extract_product(driver, card, query)
                
                # If the inspector says it was a bad product, skip it
                if product is None: continue
                
                # Make sure we don't accidentally add the exact same laptop twice
                if is_duplicate(products, product.name): continue
                
                # Save the successfully checked laptop into our final list!
                products.append(product)
                success(f"Collected {len(products)}/{ITEMS_TO_SCRAPE}")
            except Exception:
                pass


# ==========================================================
# DATA COMPILATION
# ==========================================================

def extract_product(driver, card, query):
    """
    This function acts as an inspector. It looks at a single product box,
    pulls out all the pieces of data, and packages them into a 'Product' object.
    """
    try:
        card_text = card.text.lower()
        
        # Skip items that cannot be purchased right now
        if "sold out" in card_text or "coming soon" in card_text or "out of stock" in card_text:
            return None

        # Find the title of the product
        title = extract_title(card)
        if not title: 
            return None
            
        # ==========================================
        # EXACT MATCH FILTER
        # ==========================================
        # Ensures that every word entered in the search query is present in the title
        if not all(word.lower() in title.lower() for word in query.split()): 
            return None

        # Find the current selling price, ignore super cheap accessories (under ₹1000)
        price = extract_price(card)
        if not price or price < 1000: return None

        # Extract the link and customer reviews
        url = extract_url(card)
        rating = extract_rating(card)
        review_count = extract_review_count(card)

        # -----------------------------------------------------------
        # BACKGROUND DATA RECOVERY
        # If the rating is hidden on the main search page (shows as "Unrated"), 
        # we secretly visit the product's actual page to hunt for it!
        # -----------------------------------------------------------
        if rating == "Unrated" and url:
            try:
                recovered_rating, recovered_reviews = get_flipkart_rating(driver, url)
                
                # Sometimes items go out of stock right as we click them
                if recovered_rating == "OUT_OF_STOCK":
                    info(f"Dropped -> {title} (Out of Stock on live page)")
                    return None
                
                # If we found a real rating on the background page, update it!
                if recovered_rating and recovered_rating != "Unrated":
                    rating = recovered_rating
                    
                # Update review count if we successfully recovered those numbers too
                if review_count == 0 and recovered_reviews > 0:
                    review_count = recovered_reviews
            except Exception:
                pass

        # Find the original crossed-out price (MRP) and calculate the discount
        original_price = extract_original_price(card, price)
        if not original_price or original_price <= price:
            original_price = price
            discount = "0%"
        else:
            try: 
                discount = f"{round(((original_price - price) * 100) / original_price)}%"
            except Exception: 
                discount = "0%"

        # ==========================================
        # UNRATED PRODUCT HANDLER & FORMATTER
        # ==========================================
        # If the platform hides the star rating due to low volume, 
        # we set the review count to 0 to keep our data neat and consistent.
        if rating == "Unrated":
            review_count = 0
        else:
            # BUG FIX: Forces whole numbers to display with a decimal (e.g. "4" -> "4.0")
            try:
                rating = f"{float(rating):.1f}"
            except Exception:
                pass

        info(f"Title : {title}")
        info(f"Price : ₹{price}")
        success(f"Accepted -> {title}")

        # Package all the information neatly and send it back
        return Product(
            platform="Flipkart", name=title, price=price, rating=rating,
            url=url, original_price=original_price, discount=discount, review_count=review_count
        )
    except Exception:
        return None


# ==========================================================
# INDIVIDUAL DATA POINT EXTRACTORS
# ==========================================================
# Below are the individual "tools" that know exactly where to look 
# inside Flipkart's HTML code to find specific pieces of text.

def extract_title(card):
    """Finds the name of the product."""
    # These are all the possible HTML classes Flipkart uses for titles
    for css in ["div.KzDlHZ", "a.WKTcLC", "a.wjcEIp", "a.CGtC98", "div._4rR01T", "div.syl9yP", "a[title]"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = element.text.strip()
                if len(text) > 20: return text.split('\n')[0]
                
                title = element.get_attribute("title")
                if title and len(title) > 20: return title.split('\n')[0]
        except Exception: pass
    
    # Fallback: Read raw text lines if the classes fail
    for line in card.text.split("\n"):
        line = line.strip()
        if len(line) > 20 and "₹" not in line and "%" not in line and "Free delivery" not in line.lower():
            return line
    return ""

def extract_price(card):
    """Finds the current active selling price."""
    for css in ["div.Nx9bqj", "div.Nx9bqj._4b5DiR", "div._30jeq3", "div[class*='Nx9bqj']", "div.cN1yYO div"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = element.text.strip()
                if not text: continue
                price = clean_price(text)
                if price > 0: return price
        except Exception: pass
        
    price = clean_price(card.text)
    if price > 0: return price
    return None

def extract_rating(card):
    """Finds the star rating out of 5 (e.g., 4.2)."""
    # Primary Class Checks
    for css in ["div.XQDdHH", "span.XQDdHH", "div._3LWZlK"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = (element.text or element.get_attribute("aria-label") or "").strip()
                rating = clean_rating(text)
                if rating != "Unrated": 
                    return rating
        except Exception: pass
        
    # Aggressive Plain Text Check
    try:
        text = card.text
        match = re.search(r"([1-5](?:\.\d)?)\s*(?:★)?\s*[\d,]+\s*(?:Ratings|Reviews)", text, re.IGNORECASE)
        if match:
            return match.group(1)
    except Exception: pass
        
    # HTML Inner Tag Fallback
    try:
        html = card.get_attribute("innerHTML")
        if html:
            for pattern in [
                r'>([1-5]\.\d)<', 
                r'>([1-5](?:\.\d)?)\s*★',
                r'aria-label="([1-5](?:\.\d)?)\s*★'
            ]:
                match = re.search(pattern, html, re.IGNORECASE)
                if match: return match.group(1)
    except Exception: pass
    
    return "Unrated"

def extract_url(card):
    """Finds the clickable link that takes the user to the purchase page."""
    for css in ["a.CGtC98", "a.WKTcLC", "a[href*='/p/']", "a"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                href = element.get_attribute("href")
                if href and "/p/" in href: return href
        except Exception: pass
    return ""

def extract_original_price(card, current_price=0):
    """Finds the crossed-out Maximum Retail Price."""
    for css in ["div.yRaY8j", "div._3I9_wc", "div[class*='yRaY8j']", "strike", "del"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                price = clean_price(element.text)
                if price and price > current_price: return price
        except Exception: pass
        
    try:
        matches = re.findall(r"₹\s*([\d,]+)", card.text)
        for match in matches:
            if ',' in match:
                parts = match.split(',')
                if len(parts[-1]) > 3: match = match[:-(len(parts[-1])-3)]
            val = int(match.replace(",", ""))
            if val > current_price: return val
    except Exception: pass
    return None

def extract_review_count(card):
    """
    Extracts the total number of customer ratings/reviews using HTML Boundary Parsing.
    This prevents whole-number ratings (like 4) from merging into the review count (like 429).
    """
    # 1. HTML Boundary Strategy (The Ultimate Fix for "Squished Text")
    # This searches the raw, underlying HTML so it is physically impossible for the numbers to merge.
    try:
        html = card.get_attribute("innerHTML")
        if html:
            # Pattern A: Looks for standard "429 Ratings" inside a single isolated HTML tag
            match_a = re.search(r'>([^<]*?[\d,]+[^<]*?(?:Ratings|ratings|Reviews|reviews)[^<]*?)<', html)
            if match_a:
                num_match = re.search(r"([\d,]+)", match_a.group(1))
                if num_match: 
                    return int(num_match.group(1).replace(",", ""))
                
            # Pattern B: Looks for numbers in parentheses like "(429)" inside a single isolated HTML tag
            match_b = re.search(r'>\s*\(\s*([\d,]+)\s*\)\s*<', html)
            if match_b:
                return int(match_b.group(1).replace(",", ""))
    except Exception: pass

    # 2. Standard CSS Selectors (If HTML boundary fails)
    for css in ["span.Wphh3N", "span._2_R_DZ", "div[class*='Wphh3N']", "span[class*='_38sUEc']"]:
        try:
            for element in card.find_elements(By.CSS_SELECTOR, css):
                text = element.text.strip()
                match = re.search(r"([\d,]+)\s*(?:Ratings|ratings|Reviews|reviews)", text)
                if match: return int(match.group(1).replace(",", ""))
                
                match = re.search(r"(?:\(|\|\s*)([\d,]+)\)?", text)
                if match: return int(match.group(1).replace(",", ""))
        except Exception: pass
        
    # 3. Safe Fallback
    try:
        text = card.text
        # ONLY match if safely separated by a star or newline (e.g. "4 ★ 429 Ratings" or "4\n429 Ratings")
        match = re.search(r"(?:[1-5](?:\.\d)?)\s*(?:★|\n)\s*([\d,]+)\s*(?:Ratings|ratings|Reviews|reviews)", text)
        if match: return int(match.group(1).replace(",", ""))
        
        # If it has a comma, it's safe because ratings don't have commas (e.g. "4,429 Ratings")
        match = re.search(r"([\d]+,[\d,]+)\s*(?:Ratings|ratings|Reviews|reviews)", text)
        if match: return int(match.group(1).replace(",", ""))
    except Exception: pass
    
    return 0