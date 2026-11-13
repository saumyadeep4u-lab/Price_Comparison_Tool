"""
scraper_engine.py
Enterprise Price Comparator

This file is the "Master Controller" for the scrapers. Instead of running 
Amazon, Flipkart, and Reliance separately, this engine groups them together, 
runs them one by one, and tallies up the final results into a clean summary.
"""

# ==========================================================
# IMPORTS
# ==========================================================

from src.logger import (
    info,
    success,
    warning,
)

# Import the individual scraper functions we built for each platform
from src.amazon_scraper import scrape_amazon
from src.flipkart_scraper import scrape_flipkart
from src.reliance_scraper import scrape_reliance


# ==========================================================
# SCRAPER REGISTRY
# ==========================================================

# A master list of all the platforms we want to scan. 
# If you ever want to add a new website (like Croma), you just add it to this list!
SCRAPERS = [
    ("Amazon", scrape_amazon),
    ("Flipkart", scrape_flipkart),
    ("Reliance Digital", scrape_reliance),
]


# ==========================================================
# RUN SINGLE SCRAPER
# ==========================================================

def scrape_site(
    driver,
    site_name,
    scraper,
    query
):
    """
    A helper function that runs a single platform's scraper (e.g., just Amazon).
    It safely handles the process and prevents the entire program from crashing 
    if one specific website goes down or blocks the scraper.
    """
    info("\n" + "=" * 60)
    info(f"Starting {site_name} Scraper")
    info("=" * 60)

    try:
        # Launch the specific scraper for the given website
        products = scraper(
            driver,
            query
        )

        # Check if the scraper successfully found items
        if products:
            success(
                f"{site_name} completed successfully "
                f"({len(products)} products)."
            )
        else:
            warning(
                f"{site_name} returned 0 products."
            )

        return products

    # If the user presses Ctrl+C to cancel, stop the process immediately
    except KeyboardInterrupt:
        raise

    # If the website crashes or blocks us, print a warning but keep the program alive
    except Exception as e:
        warning(
            f"{site_name} scraper failed : {e}"
        )
        # Return an empty list so the next website can still be scanned
        return []


# ==========================================================
# RUN ALL SCRAPERS
# ==========================================================

def scrape_all(
    driver,
    query
):
    """
    The main engine function. It loops through the Scraper Registry above, 
    runs every website back-to-back, and combines all the found laptops 
    into one massive list.
    """
    all_products = []
    site_totals = {}

    # Loop through each store in our registry (Amazon, then Flipkart, then Reliance)
    for site_name, scraper in SCRAPERS:
        
        # Run the helper function to scan the current store
        products = scrape_site(
            driver,
            site_name,
            scraper,
            query
        )

        # Record how many products we found on this specific store
        site_totals[site_name] = len(products)

        # If we found products, add them to our master list
        if products:
            all_products.extend(products)

    # ------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------
    # Print a clean, easy-to-read scoreboard of everything we just found

    info("\n" + "=" * 60)
    info("SCRAPING SUMMARY")
    info("=" * 60)

    for site, total in site_totals.items():
        info(
            f"{site:<20} : {total}"
        )

    info("-" * 60)
    
    success(
        f"TOTAL PRODUCTS SCRAPED : "
        f"{len(all_products)}"
    )
    
    info("=" * 60)

    # Hand the master list of products back to the main app for sorting and Excel export
    return all_products