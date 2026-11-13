"""
utils.py
Enterprise Price Comparator

This file contains the core helper functions used across all scrapers.
It is responsible for cleaning up text formatting, extracting numbers, 
validating product titles, and preventing duplicate entries.
"""

import re
from difflib import SequenceMatcher

# ==========================================================
# CLEAN PRICE
# ==========================================================
def clean_price(text):
    """
    Removes currency symbols and formatting from the price text, 
    extracting just the pure numerical value (e.g., '₹ 64,990' -> 64990).
    """
    if not text:
        return 0

    text = str(text)

    # First attempt: Look for a number immediately following the ₹ symbol
    match_symbol = re.search(r"₹\s*([\d,]+)", text)
    if match_symbol:
        val_str = match_symbol.group(1)
        # Handle cases where commas are placed incorrectly in the text
        if ',' in val_str:
            parts = val_str.split(',')
            if len(parts[-1]) > 3:
                val_str = val_str[:-(len(parts[-1])-3)]
        try:
            return int(val_str.replace(",", ""))
        except:
            pass

    # Second attempt: Look for any continuous block of 3 or more digits (with optional commas)
    match_digits = re.search(r"([\d,]{3,})", text)
    if match_digits:
        val_str = match_digits.group(1)
        if ',' in val_str:
            parts = val_str.split(',')
            if len(parts[-1]) > 3:
                val_str = val_str[:-(len(parts[-1])-3)]
        try:
            return int(val_str.replace(",", ""))
        except:
            pass

    return 0
    
# ==========================================================
# CLEAN RATING (STRICT MODE)
# ==========================================================
def clean_rating(text):
    """
    Extracts the numerical rating (e.g., '4.5') from messy text strings.
    Returns 'Unrated' if no valid rating pattern is found.
    """
    if not text:
        return "Unrated"

    text = str(text).strip()

    # 1. Matches standard rating formats like "4.5 ★", "4.5 Star", or "4.5 out of 5"
    match = re.search(r"([1-5](?:\.\d)?)\s*(?:★|star|out of)", text, re.IGNORECASE)
    if match:
        return str(float(match.group(1)))

    # 2. Exact match for a standalone number (e.g., "4.5" or "4")
    # Strict matching prevents random specifications (like "USB 2.0") from being read as a rating.
    match_exact = re.match(r"^([1-5](?:\.\d)?)$", text)
    if match_exact:
        return str(float(match_exact.group(1)))

    return "Unrated"

# ==========================================================
# TITLE MATCHES
# ==========================================================
def title_matches(title, query):
    """
    Validates if the found product title sufficiently matches the user's search query.
    Uses word-by-word comparison and a scoring system to ensure accuracy.
    """
    if not title:
        return False

    title = title.lower()
    query = query.lower()

    # Remove special characters to ensure clean word comparison
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    query = re.sub(r"[^a-z0-9 ]", " ", query)

    # Break the text down into individual words (sets ensure we only count unique words)
    title_words = set(title.split())
    query_words = set(query.split())

    # If every word in the search query is in the title, it's a perfect match
    if query_words.issubset(title_words):
        return True

    # If not a perfect match, calculate a similarity score
    common = len(title_words & query_words)
    score = common * 100 / max(len(query_words), 1)

    # Accept the product if it matches at least 30% of the required search terms
    return score >= 30

# ==========================================================
# IS DUPLICATE
# ==========================================================
def is_duplicate(products, name):
    """
    Checks if a product is already in our list to prevent duplicate entries.
    Uses both exact name matching and fuzzy string matching.
    """
    name = name.lower()
    for product in products:
        existing_name = product.name.lower()
        
        # Check for an exact name match
        if existing_name == name:
            return True
            
        # Check for a highly similar name (90% match) to catch slight typographical variations
        similarity = SequenceMatcher(None, existing_name, name).ratio()
        if similarity >= 0.90:
            return True
            
    return False