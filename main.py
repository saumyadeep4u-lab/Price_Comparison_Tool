"""
main.py
Enterprise Price Comparator

This is the main entry point of the command-line application. 
Running this file will start the entire scraping process, gather the data, 
and automatically export the final reports to your computer.
"""

# ==========================================================
# IMPORTS
# ==========================================================

from src.browser import create_driver
from src.scraper_engine import scrape_all
from src.data_processor import (
    sort_by_price,
    cheapest_product,
    display_products,
    export_excel,
    export_price_chart,
)
from src.config import OUTPUT_EXCEL
from src.logger import info, warning, success


# ==========================================================
# HEADER
# ==========================================================

def print_header():
    """
    Prints a welcoming header to the terminal when the script starts.
    """
    print("\n" + "=" * 60)
    print("ENTERPRISE PRICE COMPARATOR")
    print("=" * 60)


# ==========================================================
# FOOTER
# ==========================================================

def print_footer():
    """
    Prints a clean summary of the exported files before the script closes.
    """
    print("\n" + "=" * 60)
    print("FILES GENERATED")
    print("=" * 60)
    print(f"Excel File : {OUTPUT_EXCEL}")
    print("Chart File : price_comparison_chart.png")


# ==========================================================
# DRIVER CLEANUP
# ==========================================================

def close_driver(driver):
    """
    Safely shuts down the automated Chrome browser. 
    This prevents memory leaks on the user's computer.
    """
    if driver:
        try:
            driver.quit()
        except Exception:
            pass

# ==========================================================
# MAIN EXECUTION
# ==========================================================

def main():
    """
    The central controller of the program. It asks the user what to search for, 
    triggers the web scrapers, processes the data, and generates the final reports.
    """
    print_header()

    # Ask the user to type in the product they want to search for
    query = input("\nEnter Product Name : ").strip()

    # Prevent the program from running if the user didn't type anything
    if not query:
        warning("Product name cannot be empty.")
        return

    driver = None
    products = []

    try:
        # --------------------------------------------------
        # Launch Browser
        # --------------------------------------------------
        info("Launching browser...")
        driver = create_driver()

        # --------------------------------------------------
        # Start Scraping
        # --------------------------------------------------
        info(f"Searching for : {query}")
        
        # Trigger the master engine to scrape Amazon, Flipkart, and Reliance
        products = scrape_all(driver, query)

    # Allow the user to safely cancel the program at any time by pressing Ctrl+C
    except KeyboardInterrupt:
        warning("Process cancelled by user.")
        return

    # Catch any unexpected internet or browser crashes
    except Exception as e:
        warning(f"Unexpected error : {e}")
        return

    # Ensure the browser is always closed, even if an error occurred above
    finally:
        close_driver(driver)

    # --------------------------------------------------
    # Validate Results
    # --------------------------------------------------
    # If the scrapers couldn't find anything, notify the user and stop
    if not products:
        print("\nNo matching products found.")
        return

    info(f"Total Products Retrieved : {len(products)}")

    # --------------------------------------------------
    # Sort by Lowest Price
    # --------------------------------------------------
    # Organize the final list so the cheapest laptops are at the top
    products = sort_by_price(products)

    # --------------------------------------------------
    # Display Products
    # --------------------------------------------------
    # Print a clean text table of all found products directly in the terminal
    display_products(products)

    # --------------------------------------------------
    # Cheapest Product
    # --------------------------------------------------
    # Highlight the absolute best deal found across all platforms
    cheapest = cheapest_product(products)

    if cheapest:
        print("\n" + "=" * 60)
        print("CHEAPEST PRODUCT")
        print("=" * 60)
        print(f"Platform : {cheapest.platform}")
        print(f"Product  : {cheapest.name}")
        print(f"Price    : ₹{cheapest.price}")

        # Only display the rating if the product actually has one
        if cheapest.rating and cheapest.rating != "Unrated":
            print(f"Rating   : ⭐ {cheapest.rating}")

        # Display the discount percentage if applicable
        if cheapest.discount:
            print(f"Discount : {cheapest.discount}")

        # Display the total number of customer ratings
        if getattr(cheapest, "review_count", 0):
            print(f"Rating Count  : {cheapest.review_count}")

        # Provide the direct link to buy the product
        if cheapest.url:
            print(f"URL      : {cheapest.url}")

    # --------------------------------------------------
    # Export Files
    # --------------------------------------------------
    
    # Attempt to save the Excel Spreadsheet
    try:
        info("Exporting Excel...")
        export_excel(products, OUTPUT_EXCEL)
    except Exception as e:
        warning(f"Excel export failed : {e}")

    # Attempt to save the visual Bar Chart PNG
    try:
        info("Generating Price Chart...")
        export_price_chart(products, search_query=query)
    except Exception as e:
        warning(f"Chart export failed : {e}")

    # --------------------------------------------------
    # Finish
    # --------------------------------------------------
    print_footer()
    success("Comparison completed successfully.")


# ==========================================================
# ENTRY POINT
# ==========================================================

# This ensures the main() function only runs if this script is executed directly
if __name__ == "__main__":
    main()