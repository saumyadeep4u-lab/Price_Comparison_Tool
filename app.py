"""
app.py
Enterprise Price Comparator Web App

This is the main frontend file for the application. It generates the user interface 
using Streamlit, allowing the user to search for products, view live comparisons, 
apply filters, and download the final reports.
"""

import streamlit as st
import pandas as pd
import os

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

# Setup the basic properties of the web page (Title, Icon, and Screen Layout)
st.set_page_config(
    page_title="Price Comparison Tool",
    page_icon="💻",
    layout="wide"
)

st.title("💻 Price Comparison Tool")
st.caption("Live Price Comparison across Amazon, Flipkart & Reliance Digital")

st.divider()

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
# Streamlit refreshes the page every time a user clicks a button. 
# 'Session State' acts as a temporary memory bank so our scraped data 
# doesn't get erased when the user applies a filter or sorts a column.
if "scraped_products" not in st.session_state:
    st.session_state.scraped_products = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# =====================================================
# SEARCH BOX
# =====================================================

# Creates the input bar where the user types the product they want to find
search_query = st.text_input(
    "Enter Product Name",
    placeholder="Example: HP Pavilion "
)

# Creates the primary action button to begin the scraping engine
scan = st.button("🚀 Start Live Scan")

# =====================================================
# SCAN EXECUTION
# =====================================================

# This block triggers when the user clicks the "Start Live Scan" button
if scan:
    # Validation: Prevent the scanner from running if the search box is empty
    if search_query.strip() == "":
        st.error("Please enter a product name.")
        st.stop()

    st.session_state.search_query = search_query
    
    # Create a dynamic status text to keep the user informed of the background progress
    status = st.empty()
    status.info("Initializing Browser & Scrapers...")

    driver = None
    try:
        # Launch the invisible, automated browser
        driver = create_driver()
        
        status.info(f"Scanning Amazon, Flipkart & Reliance Digital for: {search_query}...")
        
        # Trigger the master scraper function to search all 3 platforms
        products = scrape_all(driver, search_query)
        
        if not products:
            status.error("No products found. Please try a different search term.")
            st.session_state.scraped_products = []
        else:
            status.info("Processing Results & Generating Visuals...")
            
            # Sort the freshly gathered data from cheapest to most expensive
            products = sort_by_price(products)
            
            # Save the results into the permanent memory bank so the UI can display it
            st.session_state.scraped_products = products
            
            # Generate the downloadable Excel and PNG chart files in the background
            export_excel(products, OUTPUT_EXCEL)
            export_price_chart(products, search_query=search_query, filename=CHART_FILENAME)
            
            status.success("Scan Completed Successfully!")
            
    except Exception as e:
        # If the web-scraper crashes due to internet issues, show an error
        status.error(f"An unexpected error occurred: {e}")
    finally:
        # Security Measure: Always close the automated browser to free up computer memory
        if driver:
            driver.quit()

# =====================================================
# SHOW RESULTS & UI
# =====================================================

# Retrieve the data from the memory bank
products = st.session_state.scraped_products

if products:
    st.divider()
    st.subheader("📊 Summary")

    # Convert our Python 'Product' objects into a structured dictionary 
    # so Pandas can easily turn them into a data table
    data = []
    for p in products:
        data.append({
            "Platform": p.platform,
            "Product": p.name,
            "Price": p.price,
            "Discount": p.discount,
            "Rating": p.rating,
            "Rating Count": p.review_count,
            "URL": p.url
        })
    
    df = pd.DataFrame(data)

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
        # Dropdown to isolate a specific store
        platform_filter = st.selectbox(
            "Platform", 
            ["All", "Amazon", "Flipkart", "Reliance Digital"]
        )
    with col2:
        # Dropdown to organize the data table
        sort_by = st.selectbox(
            "Sort By", 
            ["Lowest Price", "Highest Price", "Highest Rating"]
        )

    # Apply the user's platform choice
    if platform_filter != "All":
        df = df[df["Platform"] == platform_filter]

    # Apply the user's sorting choice
    if sort_by == "Lowest Price":
        df = df.sort_values("Price")
    elif sort_by == "Highest Price":
        df = df.sort_values("Price", ascending=False)
    else:
        # To sort by rating, we temporarily change "Unrated" text to the number 0 
        # so the computer can mathematically rank them.
        df["Temp_Rating"] = pd.to_numeric(df["Rating"].replace("Unrated", "0"), errors="coerce")
        df = df.sort_values("Temp_Rating", ascending=False).drop(columns=["Temp_Rating"])

    # -----------------------------------
    # DATAFRAME (THE DATA TABLE)
    # -----------------------------------
    st.subheader("📋 Price Comparison")
    
    st.dataframe(
        df,
        width="stretch",
        column_config={
            "Price": st.column_config.NumberColumn(format="₹%d"),
            "URL": st.column_config.LinkColumn("Product Link") # Renders the raw URL as a clickable blue link
        },
        hide_index=True
    )

    # -----------------------------------
    # CHART VISUALIZATION
    # -----------------------------------
    # If the background chart was successfully created, display it here
    if os.path.exists(CHART_FILENAME):
        st.subheader("📈 Visualization")
        st.image(CHART_FILENAME, width="stretch")

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
                    width="stretch"
                )
                
    with dl2:
        if os.path.exists(CHART_FILENAME):
            with open(CHART_FILENAME, "rb") as file:
                st.download_button(
                    label="📥 Download Chart Image",
                    data=file,
                    file_name=CHART_FILENAME,
                    mime="image/png",
                    width="stretch"
                )