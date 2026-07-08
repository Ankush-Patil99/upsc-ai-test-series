"""
vision_scraper.py - Autonomous VisionIAS Monthly Magazine PDF Downloader.

Uses the saved session from vision_setup.py.
Run vision_setup.py ONCE first, then this script works forever autonomously.

Downloads monthly PDFs (English, main magazine only - no PT365/Mains365/Hindi).
Saves to: D:\\upsc test series\\data\\vision_pdfs\\
"""

import re
import json
import time
import logging
import requests
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3

urllib3.disable_warnings()

# ── Config ────────────────────────────────────────────────────────────────────
SESSION_FILE  = Path(__file__).parent / "vision_session.json"
OUT_DIR       = Path(r"D:\upsc test series\data\vision_pdfs")
MAGAZINE_URL  = "https://visionias.in/current-affairs/monthly-magazine/archive"
BASE_URL      = "https://visionias.in"

OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT_DIR / "vision_scrape_log.txt", mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("vision")

# ── Exclusion filters (skip non-main-magazine PDFs) ──────────────────────────
EXCLUDE_KEYWORDS = [
    "pt365", "mains365", "hindi", "test series", "economy survey",
    "budget", "annual", "quiz", "answer", "writing", "value added",
    "current affairs quiz",
]

# ── Month name map ─────────────────────────────────────────────────────────────
MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]

# ── Metadata registry (tracks already-downloaded PDFs) ────────────────────────
REGISTRY_FILE = OUT_DIR / "downloaded.json"

def load_registry() -> dict:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {}

def save_registry(registry: dict):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)

def is_downloaded(month: str, year: str, registry: dict) -> bool:
    key = f"{month.lower()}_{year}"
    return key in registry

def mark_downloaded(month: str, year: str, path: str, words: int, registry: dict):
    key = f"{month.lower()}_{year}"
    registry[key] = {
        "path": str(path),
        "words": words,
        "downloaded_at": datetime.now().isoformat(),
    }
    save_registry(registry)

# ── PDF Downloader ─────────────────────────────────────────────────────────────
def download_pdf(url: str, dest: Path, session_cookies: list) -> tuple[bool, int]:
    """Download PDF using requests with session cookies. Returns (success, word_count)."""
    try:
        # Build requests session with VisionIAS cookies
        s = requests.Session()
        s.verify = False
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
            "Referer": MAGAZINE_URL,
        })
        for cookie in session_cookies:
            s.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", "visionias.in"),
            )

        r = s.get(url, stream=True, timeout=120)
        r.raise_for_status()

        # Check content type is actually a PDF
        content_type = r.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            log.warning(f"Non-PDF response: Content-Type={content_type} — session may have expired")
            return False, 0

        with open(dest, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)

        size_kb = dest.stat().st_size / 1024
        if size_kb < 200:
            log.warning(f"PDF too small: {size_kb:.0f} KB — likely a login redirect page")
            dest.unlink()
            return False, 0

        # Validate PDF word count
        doc = fitz.open(dest)
        text = " ".join(page.get_text() for page in doc)
        doc.close()
        word_count = len(text.split())
        if word_count < 3000:
            log.warning(f"PDF has only {word_count} words — may not be correct file")
            dest.unlink()
            return False, 0

        log.info(f"PDF OK: {dest.name} ({size_kb/1024:.1f} MB, {word_count:,} words)")
        return True, word_count

    except Exception as e:
        log.error(f"Download failed {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False, 0


# ── Main Scraper ───────────────────────────────────────────────────────────────
def scrape_vision_pdfs(
    target_months: list[str] = None,
    target_years:  list[str] = None,
    max_pdfs: int = 6,
):
    """
    Scrape VisionIAS monthly magazine PDFs.

    Args:
        target_months: List of month names to download, e.g. ['january', 'february']
                       If None, downloads the most recent available PDFs.
        target_years:  List of years, e.g. ['2026', '2025']
                       If None, uses current + previous year.
        max_pdfs:      Maximum number of PDFs to download per run.
    """
    # Check session file exists
    if not SESSION_FILE.exists():
        log.error(f"Session file not found: {SESSION_FILE}")
        log.error("Please run vision_setup.py first to authenticate.")
        return []

    with open(SESSION_FILE) as f:
        session_state = json.load(f)
    cookies = session_state.get("cookies", [])
    log.info(f"Loaded session: {len(cookies)} cookies")

    # Set default year targets
    if target_years is None:
        current_year = datetime.now().year
        target_years = [str(current_year), str(current_year - 1)]

    registry = load_registry()
    downloaded = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            storage_state=str(SESSION_FILE),   # Inject saved session
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="en-US",
        )
        page = context.new_page()

        log.info(f"Navigating to {MAGAZINE_URL} ...")
        page.goto(MAGAZINE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        html = page.content()

        # Check for CAPTCHA / login wall
        if any(x in html.lower() for x in ["captcha", "awswaf", "cf-turnstile"]):
            log.error("CAPTCHA detected — session may have expired. Re-run vision_setup.py.")
            browser.close()
            return []

        # Check if we got logged out
        if "login" in page.url.lower() or "sign-in" in page.url.lower():
            log.error("Redirected to login page — session expired. Re-run vision_setup.py.")
            browser.close()
            return []

        log.info(f"Page loaded. URL: {page.url}")

        # Parse PDF links from page
        soup = BeautifulSoup(html, "lxml")
        pdf_entries = []

        for a in soup.find_all("a", href=True):
            href  = a["href"]
            text  = a.get_text(" ", strip=True).lower()
            title = a.get_text(" ", strip=True)

            # Must be a PDF link
            if ".pdf" not in href.lower():
                continue

            # Skip excluded types
            if any(kw in text for kw in EXCLUDE_KEYWORDS):
                continue

            # Must contain a recognizable month + year
            m = re.search(
                r"(january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s*(20\d{2})",
                text + " " + href.lower(),
                re.IGNORECASE,
            )
            if not m:
                continue

            month = m.group(1).lower()
            year  = m.group(2)
            full_url = href if href.startswith("http") else urljoin(BASE_URL, href)

            pdf_entries.append({
                "month": month,
                "year":  year,
                "url":   full_url,
                "title": title,
            })

        log.info(f"Found {len(pdf_entries)} monthly magazine PDF links")
        for e in pdf_entries:
            log.info(f"  {e['month'].capitalize()} {e['year']} — {e['url'][:70]}")

        browser.close()

    # ── Download PDFs ─────────────────────────────────────────────────────────
    if not pdf_entries:
        log.error("No PDF links found on magazine page. Check session or page structure.")
        # Save debug HTML
        (OUT_DIR / "magazine_debug.html").write_text(html[:80000], encoding="utf-8")
        log.info("Saved debug HTML to magazine_debug.html")
        return []

    count = 0
    for entry in pdf_entries:
        if count >= max_pdfs:
            break

        month = entry["month"]
        year  = entry["year"]

        # Filter by targets if specified
        if target_months and month not in [m.lower() for m in target_months]:
            continue
        if target_years and year not in target_years:
            continue

        # Skip if already downloaded
        if is_downloaded(month, year, registry):
            log.info(f"SKIP (already downloaded): {month.capitalize()} {year}")
            continue

        dest = OUT_DIR / f"vision_{month}_{year}.pdf"
        log.info(f"Downloading: {month.capitalize()} {year} — {entry['url'][:70]}")

        success, word_count = download_pdf(entry["url"], dest, cookies)

        if success:
            mark_downloaded(month, year, dest, word_count, registry)
            downloaded.append(str(dest))
            count += 1
            time.sleep(1)  # Be polite between downloads
        else:
            log.error(f"FAILED: {month.capitalize()} {year}")

    log.info(f"Done. {len(downloaded)} PDFs downloaded this run.")
    return downloaded


# ── CLI Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    log.info("=" * 60)
    log.info("VisionIAS Monthly Magazine PDF Scraper")
    log.info("=" * 60)

    # Example: download last 18 months (1.5 years as required)
    current_year = datetime.now().year
    results = scrape_vision_pdfs(
        target_months=None,    # All months
        target_years=[str(current_year), str(current_year - 1)],
        max_pdfs=18,
    )

    log.info("=" * 60)
    if results:
        log.info(f"Downloaded {len(results)} PDF(s):")
        for p in results:
            pth = Path(p)
            log.info(f"  {pth.name}  ({pth.stat().st_size//1024:,} KB)")
    else:
        log.info("No new PDFs downloaded (all up to date or session issue).")
    log.info("=" * 60)
