"""
download_vision_jan_feb.py - FINAL VERSION
Uses the authenticated /current-affairs/download/{id} endpoint directly.
Downloads January & February 2026 monthly magazines to:
    D:\\upsc test series\\data\\Scrapper test\\
"""

import re, json, time, logging
import requests, fitz
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

SESSION_FILE = Path(__file__).parent / "vision_session.json"
OUT_DIR      = Path(r"D:\upsc test series\data\Scrapper test")
ARCHIVE_URL  = "https://visionias.in/current-affairs/monthly-magazine/archive"
DOWNLOAD_BASE = "https://visionias.in/current-affairs/download/"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(message)s")
log = logging.getLogger("vision_dl")

TARGET = {
    "january":  "2026",
    "february": "2026",
}
SKIP_KW = ["pt365","mains365","hindi","test series","budget","economy survey",
           "quiz","answer","writing","value added","abhyas"]


def get_pdf_download_ids(html: str) -> dict:
    """
    Extract {(month, year): download_id} from the archive page HTML.
    The page has JS like:
      fetch('https://visionias.in/current-affairs/download/14154')
    inside Alpine.js cards that also contain month/year text nearby.
    """
    # Find all fetch() download URLs
    fetch_urls = re.findall(
        r"fetch\(['\"]https://visionias\.in/current-affairs/download/(\d+)['\"]",
        html,
    )
    log.info(f"Download IDs found in page: {fetch_urls}")

    # Also find the pairing: which card (month/year) each ID belongs to
    # Strategy: find all Alpine.js x-data blocks or JS segments containing
    # a month+year AND a download ID nearby
    result = {}

    # Split HTML into ~card-sized chunks around each fetch URL
    # Each card contains "Month Year Monthly Current Affairs Magazine" + fetch ID
    pattern = re.compile(
        r"fetch\('https://visionias\.in/current-affairs/download/(\d+)'\)"
        r".*?a\.download\s*=\s*['\"]([^'\"]+)['\"]",
        re.S,
    )
    for m in pattern.finditer(html):
        dl_id    = m.group(1)
        filename = m.group(2)   # e.g. "February 2026 Monthly Current Affairs Magazine.pdf"
        # Extract month and year from filename
        m2 = re.search(
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s*(20\d{2})",
            filename, re.I,
        )
        if m2:
            month = m2.group(1).lower()
            year  = m2.group(2)
            result[(month, year)] = dl_id
            log.info(f"Mapped: {month.capitalize()} {year} → download ID {dl_id}")

    return result


def download_pdf(dl_id: str, month: str, year: str, cookies: list) -> tuple:
    url  = f"{DOWNLOAD_BASE}{dl_id}"
    dest = OUT_DIR / f"vision_{month}_{year}.pdf"

    if dest.exists():
        size_kb = dest.stat().st_size / 1024
        log.info(f"Already exists: {dest.name} ({size_kb/1024:.1f} MB)")
        return True, dest

    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
        "Referer":    ARCHIVE_URL,
        "Accept":     "application/pdf, application/octet-stream, */*",
    })
    for c in cookies:
        s.cookies.set(c["name"], c["value"], domain=c.get("domain", "visionias.in"))

    log.info(f"Downloading: {month.capitalize()} {year}  ←  {url}")
    r = s.get(url, stream=True, timeout=180)
    r.raise_for_status()

    ct = r.headers.get("Content-Type", "")
    if "html" in ct.lower():
        log.error(f"Got HTML instead of PDF (Content-Type: {ct}) — session may have expired")
        return False, None

    with open(dest, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)

    size_kb = dest.stat().st_size / 1024
    if size_kb < 200:
        log.error(f"File too small ({size_kb:.0f} KB) — wrong content")
        dest.unlink()
        return False, None

    # Validate with PyMuPDF
    try:
        doc   = fitz.open(dest)
        text  = " ".join(pg.get_text() for pg in doc)
        doc.close()
        words = len(text.split())
    except Exception as e:
        log.warning(f"Could not parse PDF: {e}"); words = 99999

    if words < 500:
        log.error(f"PDF has {words} words — probably wrong file"); dest.unlink(); return False, None

    log.info(f"✅ SAVED: {dest.name}  ({size_kb/1024:.1f} MB,  {words:,} words)")
    return True, dest


def main():
    if not SESSION_FILE.exists():
        log.error("vision_session.json not found — run vision_setup.py first"); return

    state   = json.loads(SESSION_FILE.read_text())
    cookies = state.get("cookies", [])
    log.info(f"Session loaded: {len(cookies)} cookies")

    # ── Step 1: Load archive page and extract download IDs ────────────────────
    log.info(f"Loading archive: {ARCHIVE_URL}")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            storage_state=str(SESSION_FILE),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )

        page.goto(ARCHIVE_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(8000)   # Give React time to render all cards

        if "login" in page.url.lower():
            log.error(f"Redirected to login: {page.url} — re-run vision_setup.py")
            browser.close(); return

        html = page.content()
        browser.close()

    log.info(f"Archive HTML: {len(html):,} chars")

    # ── Step 2: Parse download IDs ────────────────────────────────────────────
    id_map = get_pdf_download_ids(html)

    if not id_map:
        log.error("No download IDs parsed — saving debug HTML")
        (OUT_DIR / "vision_debug.html").write_text(html[:200000], encoding="utf-8")
        return

    # ── Step 3: Download target months ───────────────────────────────────────
    results = []
    for (month, year), dl_id in id_map.items():
        if month not in TARGET or TARGET[month] != year:
            continue
        ok, path = download_pdf(dl_id, month, year, cookies)
        if ok and path: results.append(path)
        time.sleep(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 58)
    print("  DOWNLOAD SUMMARY — VisionIAS Monthly Magazines")
    print("=" * 58)
    if results:
        for p in results:
            kb = p.stat().st_size // 1024
            print(f"  ✅  {p.name:<42}  {kb:>7,} KB")
    else:
        print("  ❌  No PDFs downloaded.")
    print("=" * 58)
    print(f"  Files saved to: {OUT_DIR}")
    print("=" * 58)


if __name__ == "__main__":
    main()
