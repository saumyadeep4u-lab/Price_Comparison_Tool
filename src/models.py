"""
models.py
Enterprise Price Comparator

This file acts as the blueprint for the scraped data. It defines the 'Product' 
structure, ensuring that every laptop scraped from Amazon, Flipkart, or Reliance 
is organized in the exact same way before being saved to the final reports.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    """
    The Product blueprint. Every time a scraper finds a laptop, 
    it creates one of these objects to neatly store all the extracted details.
    """
    
    # Required Information (The scraper MUST find these details)
    platform: str        # The store name (e.g., 'Amazon', 'Flipkart')
    name: str            # The full title of the laptop
    price: int           # The current selling price as a clean number (e.g., 65000)
    rating: str          # The star rating (e.g., '4.5' or 'Unrated')
    
    # Optional Information (Defaults are provided if the scraper cannot find them)
    url: str = ""                         # The direct web link to buy the laptop
    original_price: Optional[int] = None  # The crossed-out MRP (Maximum Retail Price)
    discount: Optional[str] = None        # The calculated discount percentage (e.g., '15%')
    review_count: int = 0                 # The total number of customer ratings