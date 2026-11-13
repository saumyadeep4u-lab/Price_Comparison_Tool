"""
data_processor.py
Enterprise Price Comparator

This file handles the final stage of the application. Once the scrapers 
have collected the data, this file sorts it, removes duplicates, prints a 
terminal summary, and exports the final Excel sheet and visual pricing chart.
"""

# ==========================================================
# IMPORTS
# ==========================================================

import matplotlib.pyplot as plt          # Used to draw the visual pricing chart
import matplotlib.patches as mpatches    # Used to create the color-coded legend in the chart
from openpyxl import Workbook            # Used to create and format the Excel (.xlsx) file
from openpyxl.styles import Font, PatternFill, Alignment # Used for styling the Excel spreadsheet
from src.logger import info, success


# ==========================================================
# REMOVE DUPLICATES
# ==========================================================

def remove_duplicates(products):
    """
    Cleans the final list of products by ensuring no exact duplicates 
    (same platform and same name) sneak into the final report.
    """
    unique = {}
    for product in products:
        if product is None:
            continue
        if not product.price:
            continue

        # Create a unique 'fingerprint' using the store name and product name
        key = (
            product.platform.lower().strip(),
            product.name.lower().strip()
        )
        
        # Only add the product if we haven't seen this exact fingerprint before
        if key not in unique:
            unique[key] = product

    info(f"{len(unique)} unique products retained.")
    return list(unique.values())


# ==========================================================
# SORT PRODUCTS
# ==========================================================

def sort_by_price(products):
    """
    Organizes the final product list from cheapest to most expensive.
    """
    return sorted(
        products,
        key=lambda product: product.price
    )


# ==========================================================
# CHEAPEST PRODUCT
# ==========================================================

def cheapest_product(products):
    """
    Identifies the single lowest-priced laptop in the entire list.
    """
    if not products:
        return None
    return min(
        products,
        key=lambda product: product.price
    )


# ==========================================================
# DISPLAY PRODUCTS
# ==========================================================

def display_products(products):
    """
    Prints a clean, formatted summary of all scraped products 
    directly into the command line/terminal for the developer to review.
    """
    if not products:
        print("\nNo products found.\n")
        return

    print()
    print("=" * 170)
    print(
        f"{'Platform':18}"
        f"{'Price':>12}"
        f"{'Rating':>10}"
        f"{'Rating Count':>14}" 
        f"{'Discount':>12}  "
        f"{'Product'}"
    )
    print("=" * 170)

    for product in products:
        print(
            f"{product.platform:18}"
            f"₹{product.price:>10}"
            f"{str(product.rating):>10}"
            f"{product.review_count:>14}"
            f"{str(product.discount or '-'):>12}  "
            f"{product.name}"
        )

    print("=" * 170)
    print(f"\nTotal Products : {len(products)}")


# ==========================================================
# EXPORT EXCEL
# ==========================================================

def export_excel(products, filename="price_comparison.xlsx"):
    """
    Generates a professional Excel spreadsheet containing all the scraped data.
    Automatically applies colors, bold headers, auto-adjusts column widths, 
    and converts URLs into clickable blue hyperlinks.
    """
    info(f"Saving Excel -> {filename}")
    
    # Create a fresh Excel workbook and name the first tab
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Price Comparison"

    # Define the column titles
    headers = [
        "Platform",
        "Product",
        "Price",
        "Original Price",
        "Discount",
        "Rating",
        "Rating Count",
        "URL"
    ]
    sheet.append(headers)

    # ------------------------------------------------------
    # HEADER STYLE
    # ------------------------------------------------------
    # Apply a professional blue background and white text to the header row
    header_fill = PatternFill(
        fill_type="solid",
        fgColor="4F81BD" # Professional Microsoft Blue
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # ------------------------------------------------------
    # WRITE DATA & APPLY HYPERLINKS
    # ------------------------------------------------------
    for product in products:
        # Add the product data to a new row in the spreadsheet
        sheet.append([
            product.platform,
            product.name,
            product.price,
            product.original_price,
            product.discount,
            product.rating,
            product.review_count,
            product.url
        ])
        
        # Make the URL cell clickable and format it like a standard web link
        if product.url:
            url_cell = sheet.cell(row=sheet.max_row, column=8)
            url_cell.hyperlink = product.url
            url_cell.font = Font(color="0563C1", underline="single") 

    # ------------------------------------------------------
    # FREEZE HEADER & AUTO WIDTH
    # ------------------------------------------------------
    # Lock the top row so it stays visible when scrolling down
    sheet.freeze_panes = "A2"

    # Automatically stretch the columns so the text isn't squished
    for column in sheet.columns:
        max_length = 0
        letter = column[0].column_letter
        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        # Set a maximum width of 60 so extremely long titles don't stretch forever
        sheet.column_dimensions[letter].width = min(max_length + 3, 60)

    # Save the file to the hard drive
    workbook.save(filename)
    success("Excel exported successfully.")


# ==========================================================
# EXPORT PRICE CHART (PNG)
# ==========================================================

def export_price_chart(products, search_query="Laptops", filename="price_comparison_chart.png"):
    """
    Generates a beautiful, color-coded horizontal bar chart showing 
    the prices of all scraped laptops across the different platforms.
    """
    if not products:
        return

    info(f"Creating chart -> {filename}")

    # Sort from Lowest Price to Highest Price
    products = sorted(products, key=lambda product: product.price)

    labels = []
    prices = []
    colors = []
    ratings = []

    # Format the data for the chart
    for product in products:
        # 1. Generate Short Names (Max 55 chars) so text doesn't overflow
        short_name = product.name
        if len(short_name) > 55:
            short_name = short_name[:52] + "..."
        
        labels.append(short_name)
        prices.append(product.price)

        # 2. Format ratings cleanly (or leave as 'Unrated')
        rating_val = str(product.rating).strip()
        if rating_val.lower() == "unrated":
            ratings.append("Unrated")
        else:
            try:
                ratings.append(f"★ {float(rating_val):.1f}")
            except Exception:
                ratings.append("Unrated")

        # 3. Assign Official Brand Colors for the bars
        platform_lower = product.platform.lower()
        if "amazon" in platform_lower:
            colors.append("#FF9900")   # Amazon Orange
        elif "flipkart" in platform_lower:
            colors.append("#2874F0")   # Flipkart Blue
        else:
            colors.append("#E31E24")   # Reliance Red

    # 4. Generate Chart Dimensions (Dynamically grows based on product count)
    height = max(6, len(products) * 0.55)
    plt.figure(figsize=(13, height))

    # 5. Plot the Horizontal Bars
    bars = plt.barh(labels, prices, color=colors)
    
    # Invert Y-axis so the cheapest laptop sits at the top of the chart
    plt.gca().invert_yaxis()

    # Eliminate the vertical gap between the lowest bar and the X-axis
    plt.ylim(len(labels) - 0.5, -0.5)

    max_price = max(prices) if prices else 0
    offset = max_price * 0.015

    # Extend X-axis limit by 25% to give the text plenty of room inside the box
    plt.xlim(0, max_price * 1.25)

    # 6. Add Text labels to the end of the Bars (Price + Rating/Unrated)
    for bar, rating in zip(bars, ratings):
        width = bar.get_width()
        plt.text(
            width + offset,
            bar.get_y() + bar.get_height() / 2,
            f"₹{int(width):,} | {rating}",
            va="center",
            fontsize=9
        )

    # 7. Add Main Title and Specific Subtitle based on the user's search
    plt.suptitle(f"Live Price Comparison : {search_query}", fontsize=14, weight="bold", y=0.98)
    plt.title("★ represents Rating out of 5", fontsize=10, style='italic', pad=15)
    
    # Format the bottom axis
    plt.xlabel("Price (₹)", labelpad=5)
    plt.grid(axis="x", linestyle="--", alpha=0.4)
    
    # 8. Create Custom Legend for Platforms at the bottom
    legend_patches = [
        mpatches.Patch(color='#FF9900', label='Amazon'),
        mpatches.Patch(color='#2874F0', label='Flipkart'),
        mpatches.Patch(color='#E31E24', label='Reliance Digital')
    ]
    
    # Place legend immediately below the X-axis label
    plt.legend(
        handles=legend_patches, 
        loc='upper center', 
        bbox_to_anchor=(0.5, -0.05), 
        ncol=3, 
        frameon=False,
        fontsize=10
    )

    # 9. Polish Layout to Ensure the Full Image is Captured Perfectly without getting cut off
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12, top=0.90, right=0.95) 
    
    # Save the chart as a high-quality PNG image
    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.close()

    success(f"Chart exported -> {filename}")