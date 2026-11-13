"""
logger.py
Enterprise Price Comparator

This file acts as the "Black Box" or "Flight Recorder" for the application. 
It records every major action, success, and error that happens while the scrapers 
are running and saves them to a text file for easy troubleshooting later.
"""

import logging
import os
from pathlib import Path

# ==========================================================
# LOG DIRECTORY SETUP
# ==========================================================

# Determine the exact folder where this script is located
BASE_DIR = Path(__file__).resolve().parent

# Create a path for a dedicated "logs" folder
LOG_DIR = BASE_DIR / "logs"

# Ensure the "logs" folder exists. If it does not exist, create it automatically.
LOG_DIR.mkdir(exist_ok=True)

# Define the exact file where all the tracking messages will be saved
LOG_FILE = LOG_DIR / "scraper.log"

# ==========================================================
# LOGGER CONFIGURATION
# ==========================================================

# Create the main logging tool and give it a specific name
logger = logging.getLogger("EnterpriseComparator")

# Set the sensitivity level. 'INFO' means it will record general updates, warnings, and errors.
logger.setLevel(logging.INFO)

# Clear out any old default settings to prevent duplicate messages
logger.handlers.clear()

# Define exactly how each message should look (e.g., "Date Time | Error Level | Message")
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S"
)

# ==========================================================
# FILE HANDLER (Saves to Hard Drive)
# ==========================================================

# Set up the tool that writes the messages into the 'scraper.log' file
file_handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8"
)

# Apply the clean formatting rules defined above
file_handler.setFormatter(formatter)

# Attach this tool to the main logger
logger.addHandler(file_handler)

# ==========================================================
# CONSOLE HANDLER (Prints to Screen)
# ==========================================================

# Set up a second tool that prints the exact same messages live in the terminal
console_handler = logging.StreamHandler()

# Apply the clean formatting rules defined above
console_handler.setFormatter(formatter)

# Attach this tool to the main logger
logger.addHandler(console_handler)

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
# These are simple shortcuts used by the other files to easily record messages 
# without needing to understand the complex setup above.

def info(message):
    """Records a standard informational update (e.g., 'Starting Amazon Scraper')."""
    logger.info(message)

def warning(message):
    """Records a minor issue that did not crash the program (e.g., 'Page took too long')."""
    logger.warning(message)

def error(message):
    """Records a major failure (e.g., 'Unable to open browser')."""
    logger.error(message)

def success(message):
    """Records a positive outcome (e.g., 'Found 15 Laptops')."""
    logger.info(f"SUCCESS: {message}")