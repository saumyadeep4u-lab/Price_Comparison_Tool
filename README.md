# 🛒 E-Commerce Price Comparison & ETL Pipeline

An enterprise-grade, automated **Data Engineering and Web Scraping ETL pipeline** engineered to extract, clean, validate, and visualize live pricing data for consumer electronics ("HP Pavilion" laptops) across three major retail networks: **Amazon**, **Flipkart**, and **Reliance Digital**. Powered by stealth Selenium automation, regex-powered data cleaning, and an interactive **Streamlit** web dashboard.

---

## 🚀 Key Features
- 🕵️‍♂️ **Stealth Web Scraping (`undetected_chromedriver`):** Bypasses aggressive bot-detection algorithms and anti-scraping firewalls using human-like randomized scrolling intervals and lazy-load navigation.
- 🛡️ **Resilient Fallback DOM Traversal:** Multi-tiered CSS selector arrays and raw-text regex parsing (`utils.py`) ensure 100% data extraction even when target e-commerce front-ends update their layouts.
- 🔍 **Dual-Extraction Rating Engine:** Safely opens secondary browser tabs (`rating_engine.py`) to scrape hidden review counts and ratings that are omitted from search result grids.
- 🧹 **Advanced Data Cleaning & Validation:** Actively filters out "Ghost Listings", dead URLs, malformed server error pages (`undefined`), and out-of-stock items (such as Reliance Digital's unpurchasable inventory tags).
- 📊 **Interactive Dashboard & Excel Export (`app.py`):** Deploys a live Streamlit web app featuring dynamic KPIs, visual price matrices, custom Matplotlib color-coded charts (`price_comparison_chart.png`), and clean Excel exports (`price_comparison.xlsx`) with clickable hyperlink formulas.
- 📝 **Comprehensive Logging (`logs/scraper.log`):** Records runtime execution states, error handling, and extraction metrics for auditing.

---

## 🛠️ Tech Stack & Architecture
- **Web Scraping:** Selenium, `undetected_chromedriver`
- **Data Manipulation & Parsing:** Pandas, NumPy, Regex (Regular Expressions)
- **Visualization:** Matplotlib, Streamlit
- **Environment & Configuration:** Python, Centralized Config Management (`config.py`)

---

## 📂 Project Directory Structure

```text
Price_Comparison_Tool/
├── src/
│   ├── logs/
│   │   └── scraper.log              # Execution and error tracking log
│   ├── amazon_scraper.py            # Amazon-specific extraction logic
│   ├── browser.py                   # Stealth WebDriver configuration
│   ├── config.py                    # Centralized scraping parameters & target URLs
│   ├── data_processor.py            # ETL transformation, cleaning & Excel exporter
│   ├── flipkart_scraper.py          # Flipkart scraper & HTML boundary parser
│   ├── logger.py                    # Logging utility module
│   ├── models.py                    # Data structures / schemas
│   ├── rating_engine.py             # Secondary tab rating & review extractor
│   ├── reliance_scraper.py          # Reliance Digital scraper & ghost-listing filter
│   ├── scraper_engine.py            # Orchestrator for multi-platform extraction
│   └── utils.py                     # Regex text cleaning & currency parsing helpers
├── app.py                           # Interactive Streamlit dashboard
├── main.py                          # Pipeline entry point (Runs the full ETL)
├── price_comparison.xlsx            # Cleaned & validated output dataset with hyperlinks
├── price_comparison_chart.png       # Generated comparative pricing visualization chart
├── Summary Document.pdf             # Detailed technical project report
├── requirements.txt                 # Project dependencies
└── README.md                        # Project documentation
```

---

## 📈 Real-World Challenges Addressed
1. **Ghost Listings & Server Redirects:** Automatically detects dead-end search cards on Reliance Digital where out-of-stock items redirect to the homepage, silencing and discarding them.
2. **The "Undefined" Database Bug:** Identifies backend programming flaws on retail portals that display deleted products as broken URLs containing the keyword `undefined`, classifying them as unrated/invalid.
3. **The Flipkart "Squash Bug":** Solves fused integer ratings and review counts (e.g., parsing `4429 Ratings`) using precise HTML boundary regex extraction to guarantee data integrity.

---

## 💻 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/saumyadeep4u-lab/Price_Comparison_Tool.git
   ```
2. **Open the project folder:**
   ```bash
   cd Price_Comparison_Tool
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the ETL Pipeline (Scraper & Data Processing):**
   ```bash
   python main.py
   ```
5. **Launch the Interactive Streamlit Dashboard:**
   ```bash
   streamlit run app.py
   ```

---

## 👨‍💻 Developer
**Saumyadeep Bardhan**
