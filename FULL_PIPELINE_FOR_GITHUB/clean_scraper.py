"""
clean_scraper.py — Strict & Validated Current Affairs Scraper
=============================================================
Focuses ONLY on clean scraping of Daily Sources and Monthly PDFs.
NO LLM generation or MCQs included.
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright
import feedparser

# ── Config & Setup ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "pipeline_data" / "clean_extraction"
DAILY_OUT_DIR = OUTPUT_DIR / "daily"
MONTHLY_OUT_DIR = OUTPUT_DIR / "monthly_pdfs"
LOG_DIR = BASE_DIR / "logs"
REGISTRY_PATH = OUTPUT_DIR / "pdf_registry.json"
DAILY_REG_PATH = OUTPUT_DIR / "daily_registry.json"

for d in [DAILY_OUT_DIR, MONTHLY_OUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "clean_scraper.log", mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("clean_scraper")

def load_registry(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_registry(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

PDF_REGISTRY = load_registry(REGISTRY_PATH)
DAILY_REGISTRY = load_registry(DAILY_REG_PATH)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"})
SESSION.verify = False  # To handle PIB SSL issues if any
import urllib3
urllib3.disable_warnings()

# ── Validation Rules: Daily Sources ───────────────────────────────────────

def clean_html(html_content: str) -> tuple[str, BeautifulSoup]:
    soup = BeautifulSoup(html_content, "lxml")
    # Remove standard noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
        tag.decompose()
    
    # Remove ads and share buttons based on common classes/ids
    noise_classes = re.compile(r'ad-|ad_|-ad|banner|share|social|newsletter|popup|widget|promo|comment|login', re.I)
    for tag in soup.find_all(attrs={"class": noise_classes}): tag.decompose()
    for tag in soup.find_all(attrs={"id": noise_classes}): tag.decompose()
    
    text = soup.get_text(separator="\n", strip=True)
    return text, soup

def validate_daily_page(url: str, text: str, soup: BeautifulSoup) -> tuple[bool, str]:
    if not text:
        return False, "Empty or null text"
    
    words = text.split()
    if len(words) < 300:
        return False, f"Content length < 300 words (Found: {len(words)})"
        
    error_texts = ["page not found", "404", "no content available"]
    text_lower = text.lower()
    for et in error_texts:
        if et in text_lower[:500]:
            return False, f"Error text detected: {et}"

    noise_keywords = ["test series", "login", "subscribe", "join now", "learn more", "copyright"]
    noise_count = sum(text_lower.count(k) for k in noise_keywords)
    if (noise_count / max(1, len(words))) > 0.3:
        return False, "Noise ratio > 30%"

    paragraphs = soup.find_all("p")
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    
    valid_paras = [p for p in paragraphs if len(p.get_text(strip=True).split()) > 10]
    
    if len(valid_paras) < 3 and (len(headings) < 2 or len(valid_paras) < 1):
        return False, f"Structure check failed: paras={len(valid_paras)}, headings={len(headings)}"

    return True, "Valid"

# ── Daily Scrapers ────────────────────────────────────────────────────────

def process_daily_article(source, url, title, date_str, html):
    if title in DAILY_REGISTRY:
        logger.info(f"[{source}] SKIP duplicate: {title}")
        return
        
    text, soup = clean_html(html)
    is_valid, reason = validate_daily_page(url, text, soup)
    
    if not is_valid:
        logger.warning(f"[{source}] REJECT page: {url} | Reason: {reason}")
        return

    out_data = {
        "source": source,
        "title": title,
        "date": date_str,
        "content": text
    }
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50].strip()
    out_path = DAILY_OUT_DIR / f"{source}_{safe_title}_{int(datetime.now().timestamp())}.json"
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
        
    DAILY_REGISTRY[title] = True
    save_registry(DAILY_REGISTRY, DAILY_REG_PATH)
    logger.info(f"[{source}] SUCCESS extracted: {title}")

def scrape_daily_rss(source_name, rss_url):
    logger.info(f"Scraping {source_name}...")
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:5]: # Limit to latest 5 for now
            title = entry.title
            date_str = entry.get('published', datetime.now().isoformat())
            html = SESSION.get(entry.link, timeout=30).text
            process_daily_article(source_name, entry.link, title, date_str, html)
    except Exception as e:
        logger.error(f"[{source_name}] Failed to scrape: {e}")

def scrape_forumias_daily():
    logger.info("Scraping ForumIAS 9PM Brief...")
    url = "https://blog.forumias.com/category/9-pm-brief/"
    try:
        html = SESSION.get(url, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            if "9-pm-brief" in a["href"].lower() and len(a["href"]) > 25:
                title = a.get_text(strip=True)
                if not title: continue
                date_str = datetime.now().isoformat()
                page_html = SESSION.get(a["href"], timeout=30).text
                process_daily_article("ForumIAS", a["href"], title, date_str, page_html)
    except Exception as e:
        logger.error(f"[ForumIAS] Failed: {e}")

def scrape_pib_daily():
    logger.info("Scraping PIB...")
    url = "https://pib.gov.in/indexd.aspx"
    try:
        html = SESSION.get(url, timeout=30, verify=False).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            if "PressReleasePage" in a["href"]:
                title = a.get_text(strip=True) or "PIB Release"
                link = f"https://pib.gov.in/{a['href']}" if not a['href'].startswith('http') else a['href']
                page_html = SESSION.get(link, timeout=30, verify=False).text
                process_daily_article("PIB", link, title, datetime.now().isoformat(), page_html)
    except Exception as e:
        logger.error(f"[PIB] Failed: {e}")

def scrape_drishti_daily():
    logger.info("Scraping Drishti IAS...")
    url = "https://www.drishtiias.com/current-affairs-news-analysis-editorials"
    try:
        html = SESSION.get(url, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            if "daily-updates" in a["href"]:
                title = a.get_text(strip=True) or "Drishti Daily Update"
                if len(title) < 5: continue
                link = a["href"] if a["href"].startswith("http") else f"https://www.drishtiias.com{a['href']}"
                page_html = SESSION.get(link, timeout=30).text
                process_daily_article("DrishtiIAS", link, title, datetime.now().isoformat(), page_html)
    except Exception as e:
        logger.error(f"[DrishtiIAS] Failed: {e}")


# ── Validation Rules: Monthly PDFs ────────────────────────────────────────

def download_and_validate_pdf(url: str, filename: str) -> Path | None:
    filepath = MONTHLY_OUT_DIR / filename
    try:
        resp = SESSION.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)
                
        # Validate Size (>500KB)
        size_kb = os.path.getsize(filepath) / 1024
        if size_kb < 500:
            logger.warning(f"REJECT PDF {filename}: Size too small ({size_kb:.1f} KB)")
            filepath.unlink()
            return None
            
        # Validate opens correctly
        try:
            doc = fitz.open(filepath)
            if doc.page_count == 0:
                raise ValueError("No pages")
            first_page_text = doc[0].get_text()
            if not first_page_text.strip():
                logger.warning(f"REJECT PDF {filename}: First page empty or unreadable")
                doc.close()
                filepath.unlink()
                return None
            doc.close()
            return filepath
        except Exception as e:
            logger.warning(f"REJECT PDF {filename}: Corrupted file ({e})")
            filepath.unlink()
            return None
            
    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        if filepath.exists(): filepath.unlink()
        return None

def clean_pdf_text(text: str) -> str:
    # Remove common PDF watermarks, headers, page numbers
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        line_s = line.strip()
        if re.match(r'^\d+$', line_s): continue # Page numbers
        if "vision ias" in line_s.lower() and len(line_s) < 30: continue
        if "www.visionias.in" in line_s.lower(): continue
        if "insightsonindia" in line_s.lower(): continue
        if line_s.startswith("©"): continue
        clean_lines.append(line)
    return "\n".join(clean_lines)

def parse_and_validate_pdf(filepath: Path, source: str, month: str, year: str):
    doc = fitz.open(filepath)
    full_text = ""
    sections = []
    
    current_heading = "General"
    current_content = []
    
    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            text = b[4].strip()
            if not text: continue
            
            # Simple heuristic for headings: Short, no period at end, capital letters
            if len(text) < 100 and "\n" not in text and not text.endswith(".") and text.istitle():
                if current_content:
                    sections.append({"heading": current_heading, "content": clean_pdf_text("\n".join(current_content))})
                    current_content = []
                current_heading = text
            else:
                current_content.append(text)
            full_text += text + "\n"
            
    if current_content:
        sections.append({"heading": current_heading, "content": clean_pdf_text("\n".join(current_content))})
        
    doc.close()
    
    full_text = clean_pdf_text(full_text)
    words = full_text.split()
    
    # Validation
    if len(words) < 5000:
        logger.warning(f"REJECT PDF CONTENT {filepath.name}: < 5000 words ({len(words)})")
        return
        
    index_ad_ratio = sum(1 for w in words if w.lower() in ["index", "advertisement", "subscribe", "test series"]) / max(1, len(words))
    if index_ad_ratio > 0.1:
        logger.warning(f"REJECT PDF CONTENT {filepath.name}: High index/ad ratio")
        return
        
    if len(sections) < 3:
        logger.warning(f"REJECT PDF CONTENT {filepath.name}: No clear headings detected")
        return

    out_data = {
        "source": source,
        "month": month,
        "year": year,
        "sections": sections
    }
    
    out_path = MONTHLY_OUT_DIR / f"{source}_{month}_{year}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    logger.info(f"[{source}] SUCCESS parsed PDF: {month} {year}")


# ── Monthly Scrapers ──────────────────────────────────────────────────────

def scrape_vision_playwright():
    logger.info("Scraping VisionIAS using Playwright...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://visionias.in/resources/monthly_magazine.php", timeout=60000)
            
            # Wait for content to load
            page.wait_for_timeout(5000)
            
            links = page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors.map(a => ({href: a.href, text: a.innerText}));
            }''')
            
            browser.close()
            
            for item in links:
                href = item['href']
                text = item['text'].lower()
                
                if not href.endswith('.pdf'): continue
                if "pt365" in text or "mains365" in text or "test" in text: continue
                if "hindi" in text: continue
                
                # Extract month/year
                match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})', text)
                if not match:
                    match = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-_]*(20\d{2})', href.lower())
                
                if match:
                    month, year = match.groups()
                    registry_key = f"vision_{month.lower()}_{year}"
                    
                    if registry_key in PDF_REGISTRY:
                        continue
                        
                    logger.info(f"[VisionIAS] Found PDF: {month} {year}")
                    fname = f"VisionIAS_{month}_{year}.pdf"
                    filepath = download_and_validate_pdf(href, fname)
                    if filepath:
                        parse_and_validate_pdf(filepath, "vision", month, year)
                        PDF_REGISTRY[registry_key] = True
                        save_registry(PDF_REGISTRY, REGISTRY_PATH)

    except Exception as e:
        logger.error(f"[VisionIAS] Playwright scrape failed: {e}")

def scrape_insights_monthly():
    logger.info("Scraping InsightsIAS...")
    url = "https://www.insightsonindia.com/current-affairs-downloads/"
    try:
        html = SESSION.get(url, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text().lower()
            if "magazine" in text and ("quiz" not in text and "secure" not in text and "answer" not in text):
                match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})', text)
                if match:
                    month, year = match.groups()
                    registry_key = f"insights_{month.lower()}_{year}"
                    if registry_key in PDF_REGISTRY: continue
                    
                    post_url = a["href"]
                    post_html = SESSION.get(post_url, timeout=30).text
                    post_soup = BeautifulSoup(post_html, "lxml")
                    for link in post_soup.find_all("a", href=True):
                        if link["href"].endswith(".pdf") and "combined" in link.get_text().lower():
                            logger.info(f"[InsightsIAS] Found PDF: {month} {year}")
                            fname = f"InsightsIAS_{month}_{year}.pdf"
                            filepath = download_and_validate_pdf(link["href"], fname)
                            if filepath:
                                parse_and_validate_pdf(filepath, "insights", month, year)
                                PDF_REGISTRY[registry_key] = True
                                save_registry(PDF_REGISTRY, REGISTRY_PATH)
                            break
    except Exception as e:
        logger.error(f"[InsightsIAS] Failed: {e}")

def main():
    logger.info("=== STARTING CLEAN EXTRACTION PHASE ===")
    
    # 1. Daily Sources
    scrape_daily_rss("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss")
    scrape_daily_rss("Indian Express", "https://indianexpress.com/section/india/feed/")
    scrape_forumias_daily()
    scrape_pib_daily()
    scrape_drishti_daily()
    
    # 2. Monthly PDFs
    scrape_vision_playwright()
    scrape_insights_monthly()
    
    logger.info("=== EXTRACTION COMPLETE ===")

if __name__ == "__main__":
    main()
