"""
app.py
Enterprise Price Comparator Web App

This is the main frontend file for the application. It generates the user interface 
using Streamlit, allowing the user to search for products, view live comparisons, 
apply filters, and download the final reports.
"""

import os
import re
import streamlit as st
import pandas as pd
import openpyxl

# Import our custom project modules responsible for background operations
from src.browser import create_driver
from src.scraper_engine import scrape_all
from src.data_processor import (
    sort_by_price,
    export_excel,
    export_price_chart
)

# Standardized filenames for the exportable reports
OUTPUT_EXCEL = "price_comparison.xlsx"
CHART_FILENAME = "price_comparison_chart.png"

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Price Comparison Tool",
    page_icon="💻",
    layout="wide"
)

st.title("💻 Price Comparison Tool")
st.caption("Live Price Comparison across Amazon, Flipkart & Reliance Digital")

st.divider()

# =====================================================
# HELPER: LOAD PRE-VALIDATED EXCEL DATASET (CLOUD FALLBACK)
# =====================================================

def load_cached_dataset(excel_path):
    """Loads price_comparison.xlsx and extracts clean URLs from HYPERLINK formulas."""
    if not os.path.exists(excel_path):
        return None

    try:
        wb = openpyxl.load_workbook(excel_path, data_only=False)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=False))
        if not rows:
            return None

        headers = [str(cell.value).strip() if cell.value is not None else f"Col_{i}" for i, cell in enumerate(rows[0])]
        records = []

        for row in rows[1:]:
            record = {}
            for header, cell in zip(headers, row):
                val = cell.value
                if cell.hyperlink and cell.hyperlink.target:
                    val = cell.hyperlink.target
                elif isinstance(val, str) and ("HYPERLINK" in val.upper() or "http" in val.lower()):
                    match = re.search(r'https?://[^\s"\')]+', val)
                    if match:
                        val = match.group(0)
                record[header] = val
            records.append(record)

        df = pd.DataFrame(records)

        # Standardize column names to match dashboard schema
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if "platform" in col_lower or "source" in col_lower or "store" in col_lower:
                rename_map[col] = "Platform"
            elif "product" in col_lower or "title" in col_lower or "name" in col_lower:
                rename_map[col] = "Product"
            elif "price" in col_lower:
                rename_map[col] = "Price"
            elif "discount" in col_lower:
                rename_map[col] = "Discount"
            elif "count" in col_lower or "review" in col_lower:
                rename_map[col] = "Rating Count"
            elif "rating" in col_lower:
                rename_map[col] = "Rating"
            elif "url" in col_lower or "link" in col_lower:
                rename_map[col] = "URL"

        df = df.rename(columns=rename_map)

        if "Price" in df.columns:
            df["Price"] = pd.to_numeric(
                df["Price"].astype(str).str.replace(r"[^\d.]", "", regex=True),
                errors="coerce"
            )
            df = df.dropna(subset=["Price"])
            df["Price"] = df["Price"].astype(int)

        return df
    except Exception:
        return None

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

if "scraped_df" not in st.session_state:
    # Pre-load the validated dataset so the dashboard is populated on startup
    st.session_state.scraped_df = load_cached_dataset(OUTPUT_EXCEL)
if "search_query" not in st.session_state:
    st.session_state.search_query = "HP Pavilion"

# =====================================================
# SEARCH BOX
# =====================================================

search_query = st.text_input(
    "Enter Product Name",
    value=st.session_state.search_query,
    placeholder="Example: HP Pavilion"
)

scan = st.button("🚀 Start Live Scan")

# =====================================================
# SCAN EXECUTION (HYBRID LOCAL SCRAPER + CLOUD FALLBACK)
# =====================================================

if scan:
    if search_query.strip() == "":
        st.error("Please enter a product name.")
        st.stop()

    st.session_state.search_query = search_query

    status = st.empty()
    status.info("Initializing Browser & Scrapers...")

    driver = None
    try:
        # Launch the automated Chrome browser (works on local machines with Chrome installed)
        driver = create_driver()

        status.info(f"Scanning Amazon, Flipkart & Reliance Digital for: {search_query}...")
        products = scrape_all(driver, search_query)

        if not products:
            status.error("No products found. Please try a different search term.")
        else:
            status.info("Processing Results & Generating Visuals...")
            products = sort_by_price(products)

            export_excel(products, OUTPUT_EXCEL)
            export_price_chart(products, search_query=search_query, filename=CHART_FILENAME)

            data = [{
                "Platform": p.platform,
                "Product": p.name,
                "Price": p.price,
                "Discount": p.discount,
                "Rating": p.rating,
                "Rating Count": p.review_count,
                "URL": p.url
            } for p in products]

            st.session_state.scraped_df = pd.DataFrame(data)
            status.success("Scan Completed Successfully!")

    except Exception:
        # Cloud Fallback when running on headless Streamlit Community Cloud without Chrome binary
        cached_df = load_cached_dataset(OUTPUT_EXCEL)
        if cached_df is not None and not cached_df.empty:
            st.session_state.scraped_df = cached_df
            status.info(
                "⚡ **Cloud Demo Mode:** Live headless Chrome scraping requires a local desktop environment. "
                "Displaying the validated 28-item dataset (`HP Pavilion` across Amazon, Flipkart & Reliance Digital)."
            )
        else:
            status.error("Live browser automation is unavailable in this cloud container and no cached dataset was found.")
    finally:
        if driver:
            driver.quit()

# =====================================================
# SHOW RESULTS & UI
# =====================================================

df_source = st.session_state.scraped_df

if df_source is not None and not df_source.empty:
    df = df_source.copy()

    st.divider()
    st.subheader("📊 Summary")

    # -----------------------------------
    # TOP METRICS DASHBOARD
    # -----------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Products", len(df))
    c2.metric("Lowest Price", f"₹{int(df['Price'].min()):,}")
    c3.metric("Highest Price", f"₹{int(df['Price'].max()):,}")
    c4.metric("Average Price", f"₹{int(df['Price'].mean()):,}")

    st.divider()

    # -----------------------------------
    # INTERACTIVE FILTERS
    # -----------------------------------
    col1, col2 = st.columns(2)
    with col1:
        platform_filter = st.selectbox(
            "Platform",
            ["All", "Amazon", "Flipkart", "Reliance Digital"]
        )
    with col2:
        sort_by = st.selectbox(
            "Sort By",
            ["Lowest Price", "Highest Price", "Highest Rating"]
        )

    if platform_filter != "All" and "Platform" in df.columns:
        df = df[df["Platform"] == platform_filter]

    if sort_by == "Lowest Price" and "Price" in df.columns:
        df = df.sort_values("Price")
    elif sort_by == "Highest Price" and "Price" in df.columns:
        df = df.sort_values("Price", ascending=False)
    elif "Rating" in df.columns:
        df["Temp_Rating"] = pd.to_numeric(
            df["Rating"].astype(str).str.replace("Unrated", "0", case=False),
            errors="coerce"
        ).fillna(0)
        df = df.sort_values("Temp_Rating", ascending=False).drop(columns=["Temp_Rating"])

    # -----------------------------------
    # DATAFRAME (THE DATA TABLE)
    # -----------------------------------
    st.subheader("📋 Price Comparison")

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="₹%d"),
            "URL": st.column_config.LinkColumn("Product Link")
        },
        hide_index=True
    )

    # -----------------------------------
    # CHART VISUALIZATION
    # -----------------------------------
    if os.path.exists(CHART_FILENAME):
        st.subheader("📈 Visualization")
        st.image(CHART_FILENAME, use_container_width=True)

    st.divider()

    # -----------------------------------
    # DOWNLOAD BUTTONS
    # -----------------------------------
    dl1, dl2 = st.columns(2)

    with dl1:
        if os.path.exists(OUTPUT_EXCEL):
            with open(OUTPUT_EXCEL, "rb") as file:
                st.download_button(
                    label="📥 Download Excel File",
                    data=file,
                    file_name="price_comparison.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    with dl2:
        if os.path.exists(CHART_FILENAME):
            with open(CHART_FILENAME, "rb") as file:
                st.download_button(
                    label="📥 Download Chart Image",
                    data=file,
                    file_name=CHART_FILENAME,
                    mime="image/png",
                    use_container_width=True
                )
