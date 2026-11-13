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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_EXCEL = os.path.join(BASE_DIR, "price_comparison.xlsx")
CHART_FILENAME = os.path.join(BASE_DIR, "price_comparison_chart.png")

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

def parse_price_value(val):
    """Safely extracts integer price from numbers or formatted currency strings."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    match = re.search(r"\d[\d,]*", str(val))
    if match:
        return int(match.group(0).replace(",", ""))
    return None


def sanitize_for_arrow(df):
    """Ensures unique column names and strict types so PyArrow / st.dataframe never crashes."""
    if df is None or df.empty:
        return None

    # 1. Remove any duplicate column names
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # 2. Keep only the expected dashboard columns in clean order
    expected_cols = ["Platform", "Product", "Price", "Discount", "Rating", "Rating Count", "URL"]
    available_cols = [c for c in expected_cols if c in df.columns]
    if available_cols:
        df = df[available_cols].copy()

    # 3. Enforce strict types for PyArrow compatibility
    if "Price" in df.columns:
        df["Price"] = df["Price"].apply(parse_price_value)
        df = df.dropna(subset=["Price"])
        df["Price"] = df["Price"].astype(int)

    for col in df.columns:
        if col != "Price":
            df[col] = df[col].fillna("N/A").astype(str)

    return df.reset_index(drop=True)


def load_cached_dataset(excel_path):
    """Loads price_comparison.xlsx and extracts clean URLs from HYPERLINK formulas."""
    if not os.path.exists(excel_path):
        if os.path.exists("price_comparison.xlsx"):
            excel_path = "price_comparison.xlsx"
        else:
            return None

    try:
        wb = openpyxl.load_workbook(excel_path, data_only=False)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=False))
        if not rows:
            return None

        headers = [
            str(cell.value).strip() if cell.value is not None else f"Col_{i}"
            for i, cell in enumerate(rows[0])
        ]

        records = []
        for row in rows[1:]:
            if all(cell.value is None for cell in row):
                continue
            record = {}
            for header, cell in zip(headers, row):
                val = cell.value
                if cell.hyperlink and cell.hyperlink.target:
                    val = cell.hyperlink.target
                elif isinstance(val, str) and ("HYPERLINK" in val.upper() or "http" in val.lower()):
                    match = re.search(r'https?://[^\s"\',)]+', val)
                    if match:
                        val = match.group(0)
                record[header] = val
            records.append(record)

        df = pd.DataFrame(records)
        if df.empty:
            return None

        # Map columns cleanly without collisions
        new_columns = []
        used_targets = set()

        for i, col in enumerate(df.columns):
            col_lower = str(col).lower()
            target = None
            if ("url" in col_lower or "link" in col_lower) and "URL" not in used_targets:
                target = "URL"
            elif ("platform" in col_lower or "source" in col_lower or "store" in col_lower or "site" in col_lower) and "Platform" not in used_targets:
                target = "Platform"
            elif ("count" in col_lower or "review" in col_lower) and "Rating Count" not in used_targets:
                target = "Rating Count"
            elif "rating" in col_lower and "Rating" not in used_targets:
                target = "Rating"
            elif "discount" in col_lower and "Discount" not in used_targets:
                target = "Discount"
            elif "price" in col_lower and "Price" not in used_targets:
                target = "Price"
            elif ("product" in col_lower or "title" in col_lower or "name" in col_lower) and "Product" not in used_targets:
                target = "Product"

            if target:
                new_columns.append(target)
                used_targets.add(target)
            else:
                new_columns.append(f"Extra_{i}")

        df.columns = new_columns
        return sanitize_for_arrow(df)
    except Exception as e:
        st.warning(f"Error reading cached Excel file: {e}")
        return None

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

if "scraped_df" not in st.session_state:
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

            st.session_state.scraped_df = sanitize_for_arrow(pd.DataFrame(data))
            status.success("Scan Completed Successfully!")

    except Exception:
        cached_df = load_cached_dataset(OUTPUT_EXCEL)
        if cached_df is not None and not cached_df.empty:
            st.session_state.scraped_df = cached_df
            status.success(
                f"⚡ Cloud Demo Mode: Loaded the validated {len(cached_df)}-item dataset across Amazon, Flipkart & Reliance Digital."
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
    df = sanitize_for_arrow(df_source)

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
            df["Rating"].astype(str).str.extract(r"(\d+\.?\d*)")[0],
            errors="coerce"
        ).fillna(0)
        df = df.sort_values("Temp_Rating", ascending=False).drop(columns=["Temp_Rating"])

    df = df.reset_index(drop=True)

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
                    file_name="price_comparison_chart.png",
                    mime="image/png",
                    use_container_width=True
                )
