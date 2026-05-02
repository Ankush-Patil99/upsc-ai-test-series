# UPSC Current Affairs Scraper Pipeline

This repository contains the definitive, autonomous scraping pipeline for UPSC Current Affairs. It extracts daily and monthly data from six major sources and perfectly formats it for the Question Generation Engine.

## Sources Covered
1. **Drishti IAS** (Daily articles)
2. **ForumIAS** (9PM Briefs)
3. **Indian Express** (Daily UPSC articles)
4. **The Hindu** (Editorials)
5. **Vision IAS** (Monthly PDFs)
6. **Insights IAS** (Monthly PDFs)

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **One-Time VisionIAS Setup:**
   VisionIAS requires a logged-in session to bypass CAPTCHAs. Run the setup script ONCE to save your session.
   ```bash
   python vision_setup.py
   ```
   Follow the on-screen prompts to log in. This creates `vision_session.json` (ignored in Git).

## Usage

### 1. Daily Autopull (Latest News)
Scrapes the latest available articles from all sources.
```bash
python master_scraper_pipeline.py --mode latest
```

### 2. Historical Month Scrape
Extracts ALL content for a specific past month.
```bash
python master_scraper_pipeline.py --mode historical --month December --year 2025
```

## Data Output

To prevent file clutter, all text data is appended to a **single master file**.

* **Text Data:** `data/articles_master.json`
* **PDF Vault:** `data/pdfs/`
* **State Management:** `data/scrape_registry.json` ensures no URL or PDF is ever scraped twice.
