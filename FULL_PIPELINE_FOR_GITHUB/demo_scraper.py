"""
demo_scraper.py - Validated Demo Download for All 7 Sources
============================================================
Uses SAME validation logic as clean_scraper.py.
Saves ONE validated sample from each source to:
  D:/upsc test series/data/Scrapper test/

Sources:
  1. VisionIAS        - Monthly PDF    (Playwright)
  2. InsightsIAS      - Monthly PDF    (requests + BS4)
  3. ForumIAS         - Daily HTML     (requests + BS4)
  4. The Hindu        - Daily RSS      (feedparser)
  5. Indian Express   - Daily RSS      (feedparser)
  6. PIB              - Press Release  (requests + BS4)
  7. Drishti IAS      - Daily Analysis (requests + BS4)
"""

import os, re, json, time, hashlib, sys, shutil
import requests, feedparser
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

# ── Output Directory ─────────────────────────────────────────────────────────
OUT = Path(r"D:\upsc test series\data\Scrapper test")
OUT.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
SESSION.verify = False

# ── ANSI colours for pretty terminal output ──────────────────────────────────
OK    = "[OK]"
FAIL  = "[FAIL]"
WARN  = "[WARN]"
INFO  = "[INFO]"

def log(tag, source, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {ts} | {tag} | [{source}] {msg}")

# ── Validation Helpers ────────────────────────────────────────────────────────

NOISE_RE = re.compile(
    r'\b(test series|login|subscribe|sign in|register|join now|learn more|'
    r'advertisement|cookie|newsletter|copyright)\b', re.I
)
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "button"]
NOISE_CLASSES = re.compile(
    r'ad[-_]?|[-_]?ad\b|banner|share|social|popup|widget|promo|comment|login|sidebar|breadcrumb',
    re.I
)

def clean_html_to_text(html: str) -> tuple[str, BeautifulSoup]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    for tag in soup.find_all(attrs={"class": NOISE_CLASSES}):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": NOISE_CLASSES}):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text, soup

def validate_article(text: str, soup: BeautifulSoup) -> tuple[bool, str]:
    """Return (is_valid, reason)."""
    if not text or not text.strip():
        return False, "Empty text"
    words = text.split()
    wcount = len(words)
    if wcount < 300:
        return False, f"Too short: {wcount} words (min 300)"
    for err in ("page not found", "404 error", "no content available"):
        if err in text[:400].lower():
            return False, f"Error page detected: '{err}'"
    noise_hits = len(NOISE_RE.findall(text))
    if noise_hits / max(1, wcount) > 0.30:
        return False, f"Noise ratio too high: {noise_hits}/{wcount}"
    paras  = [p for p in soup.find_all("p")  if len(p.get_text(strip=True).split()) > 10]
    heads  = soup.find_all(["h1","h2","h3","h4"])
    if len(paras) < 3 and not (len(heads) >= 2 and len(paras) >= 1):
        return False, f"Structure fail: {len(paras)} paras, {len(heads)} headings"
    return True, "OK"

def save_json(data: dict, filename: str):
    path = OUT / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path

def download_pdf(url: str, filename: str) -> Path | None:
    path = OUT / filename
    try:
        resp = SESSION.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(1024 * 1024):
                f.write(chunk)
        # Size check
        size_kb = path.stat().st_size / 1024
        if size_kb < 500:
            log(FAIL, "PDF", f"{filename}: Too small ({size_kb:.0f} KB < 500 KB) — deleting")
            path.unlink()
            return None
        # Corruption check
        doc = fitz.open(path)
        if doc.page_count == 0 or not doc[0].get_text().strip():
            log(FAIL, "PDF", f"{filename}: Corrupt / unreadable first page — deleting")
            doc.close(); path.unlink(); return None
        words = " ".join(p.get_text() for p in doc).split()
        doc.close()
        if len(words) < 5000:
            log(FAIL, "PDF", f"{filename}: Content < 5000 words ({len(words)}) — deleting")
            path.unlink(); return None
        log(OK, "PDF", f"{filename}  ({size_kb/1024:.1f} MB, {len(words):,} words)")
        return path
    except Exception as e:
        log(FAIL, "PDF", f"{filename}: {e}")
        if path.exists(): path.unlink()
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. VISION IAS  — Playwright (JS-rendered archive page)
# ─────────────────────────────────────────────────────────────────────────────
def demo_visionias():
    print("\n" + "-"*60)
    print("  [1/7]  VISION IAS — Monthly PDF  (Playwright)")
    print("-"*60)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://visionias.in/resources/monthly_magazine.php", timeout=60_000, wait_until="networkidle")
            page.wait_for_timeout(4000)

            # Grab all <a> elements
            links = page.evaluate("""() =>
                Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({href: a.href, text: (a.innerText || '').toLowerCase().trim()}))
            """)
            browser.close()

        found = []
        for item in links:
            href = item["href"]
            text = item["text"]
            if not href: continue
            # Only monthly current affairs PDFs in English
            if not (".pdf" in href.lower()): continue
            if any(x in text for x in ["pt365","mains365","hindi","test","budget","economy"]): continue
            if any(x in href.lower() for x in ["pt365","mains365","hindi","test"]): continue
            m = re.search(
                r'(january|february|march|april|may|june|july|august|'
                r'september|october|november|december)\s*(20\d{2})',
                text + " " + href.lower()
            )
            if m:
                found.append((m.group(1), m.group(2), href))

        if not found:
            log(WARN, "VisionIAS", "No dated monthly PDFs found in JS-rendered page — trying direct URL pattern")
            # Fallback: Vision IAS typically hosts PDFs at predictable paths
            candidates = [
                ("january", "2026", "https://visionias.in/resources/download?id=monthly_magazine&month=jan-2026"),
                ("december", "2025", "https://visionias.in/resources/download?id=monthly_magazine&month=dec-2025"),
            ]
            for month, year, url in candidates:
                fname = f"VisionIAS_{month}_{year}_demo.pdf"
                if download_pdf(url, fname):
                    return
            log(FAIL, "VisionIAS", "Could not retrieve monthly PDF — site requires authentication for direct download")
            # Save a diagnostic HTML dump instead so the user can inspect
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("https://visionias.in/resources/monthly_magazine.php", wait_until="networkidle")
                page.wait_for_timeout(4000)
                html_dump = page.content()
                browser.close()
            dump_path = OUT / "VisionIAS_page_diagnostic.html"
            dump_path.write_text(html_dump, encoding="utf-8")
            log(INFO, "VisionIAS", f"Saved full rendered HTML to {dump_path.name} for manual inspection")
            return

        # Download the most recent one found
        month, year, url = found[0]
        log(INFO, "VisionIAS", f"Found: {month} {year} → {url[:70]}...")
        fname = f"VisionIAS_{month}_{year}_demo.pdf"
        download_pdf(url, fname)

    except Exception as e:
        log(FAIL, "VisionIAS", f"Playwright error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. INSIGHTS IAS — Monthly PDF
# ─────────────────────────────────────────────────────────────────────────────
def demo_insightsias():
    print("\n" + "-"*60)
    print("  [2/7]  INSIGHTS IAS — Monthly PDF")
    print("-"*60)
    url = "https://www.insightsonindia.com/current-affairs-downloads/"
    PRIORITY_MONTHS = {"january 2026", "december 2025"}
    try:
        html = SESSION.get(url, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz","secure","answer","writing","hindi"]): continue
            m = re.search(
                r'(january|february|march|april|may|june|july|august|'
                r'september|october|november|december)\s*(20\d{2})', text
            )
            if not m: continue
            label = f"{m.group(1)} {m.group(2)}"
            # Prefer Jan 2026 or Dec 2025
            if label not in PRIORITY_MONTHS and len(OUT.glob("InsightsIAS_*.pdf")) > 0:
                continue
            post_url = a["href"]
            log(INFO, "InsightsIAS", f"Checking post: {label} → {post_url[:60]}...")
            post_html = SESSION.get(post_url, timeout=30).text
            post_soup = BeautifulSoup(post_html, "lxml")
            for link in post_soup.find_all("a", href=True):
                href = link["href"]
                link_text = link.get_text(" ", strip=True).lower()
                if href.endswith(".pdf") and "combined" in link_text:
                    fname = f"InsightsIAS_{m.group(1)}_{m.group(2)}_demo.pdf"
                    if download_pdf(href, fname):
                        return  # Got one valid PDF — enough for demo
            time.sleep(0.5)
    except Exception as e:
        log(FAIL, "InsightsIAS", f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. FORUM IAS — Daily 9PM Brief (HTML article)
# ─────────────────────────────────────────────────────────────────────────────
def demo_forumias():
    print("\n" + "-"*60)
    print("  [3/7]  FORUM IAS — Daily 9PM Brief")
    print("-"*60)
    base = "https://blog.forumias.com"
    cat  = f"{base}/category/9-pm-brief/"
    try:
        html = SESSION.get(cat, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Category link itself or very short slug → skip
            if href.rstrip("/") == cat.rstrip("/"): continue
            if "9-pm-brief" not in href: continue
            if len(href) < 35: continue
            title = a.get_text(strip=True) or "ForumIAS 9PM Brief"
            if len(title) < 5: continue
            full = urljoin(base, href)
            log(INFO, "ForumIAS", f"Fetching: {title[:60]}")
            page_html = SESSION.get(full, timeout=30).text
            text, s = clean_html_to_text(page_html)
            valid, reason = validate_article(text, s)
            if not valid:
                log(WARN, "ForumIAS", f"REJECTED — {reason}")
                continue
            out = {"source": "ForumIAS", "title": title,
                   "date": datetime.now().isoformat(), "content": text}
            p = save_json(out, "ForumIAS_9pm_brief_demo.json")
            log(OK, "ForumIAS", f"Saved {p.stat().st_size//1024} KB → {p.name}")
            return
        log(FAIL, "ForumIAS", "No valid 9PM Brief article found")
    except Exception as e:
        log(FAIL, "ForumIAS", f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. THE HINDU — Daily RSS Article (Editorials/Opinions — full text available)
# ─────────────────────────────────────────────────────────────────────────────
def demo_thehindu():
    print("\n" + "-"*60)
    print("  [4/7]  THE HINDU — Daily Editorial/Opinion Article")
    print("-"*60)
    # Try multiple feeds in order — editorial/opinion feeds tend to have full text
    rss_feeds = [
        "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
        "https://www.thehindu.com/opinion/feeder/default.rss",
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ]
    try:
        for rss in rss_feeds:
            feed = feedparser.parse(rss)
            for entry in feed.entries:
                log(INFO, "The Hindu", f"Trying: {entry.title[:60]}")
                html = SESSION.get(entry.link, timeout=30).text
                text, s = clean_html_to_text(html)
                # The Hindu paywall gives partial text; check if summary from RSS is richer
                # Supplement with RSS summary text if article text is too short
                if len(text.split()) < 300 and hasattr(entry, 'summary'):
                    rss_text = BeautifulSoup(entry.get('summary', ''), 'lxml').get_text(" ", strip=True)
                    text = text + "\n" + rss_text
                valid, reason = validate_article(text, s)
                if not valid:
                    log(WARN, "The Hindu", f"REJECTED -- {reason}")
                    continue
                out = {"source": "The Hindu", "title": entry.title,
                       "date": entry.get("published", datetime.now().isoformat()),
                       "content": text}
                p = save_json(out, "TheHindu_article_demo.json")
                log(OK, "The Hindu", f"Saved {p.stat().st_size//1024} KB -> {p.name}")
                return
        log(FAIL, "The Hindu", "No valid article found (paywall limits content on all feeds)")
    except Exception as e:
        log(FAIL, "The Hindu", f"Error: {e}")



# ─────────────────────────────────────────────────────────────────────────────
# 5. INDIAN EXPRESS — Daily RSS feed → article
# ─────────────────────────────────────────────────────────────────────────────
def demo_indianexpress():
    print("\n" + "-"*60)
    print("  [5/7]  INDIAN EXPRESS — Daily RSS Article")
    print("-"*60)
    rss = "https://indianexpress.com/section/india/feed/"
    try:
        feed = feedparser.parse(rss)
        for entry in feed.entries:
            log(INFO, "IndianExpress", f"Trying: {entry.title[:60]}")
            html = SESSION.get(entry.link, timeout=30).text
            text, s = clean_html_to_text(html)
            valid, reason = validate_article(text, s)
            if not valid:
                log(WARN, "IndianExpress", f"REJECTED — {reason}")
                continue
            out = {"source": "Indian Express", "title": entry.title,
                   "date": entry.get("published", datetime.now().isoformat()),
                   "content": text}
            p = save_json(out, "IndianExpress_article_demo.json")
            log(OK, "IndianExpress", f"Saved {p.stat().st_size//1024} KB → {p.name}")
            return
        log(FAIL, "IndianExpress", "No valid article found in RSS feed")
    except Exception as e:
        log(FAIL, "IndianExpress", f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. PIB — Press Release
# ─────────────────────────────────────────────────────────────────────────────
def demo_pib():
    print("\n" + "-"*60)
    print("  [6/7]  PIB -- Press Release")
    print("-"*60)
    # Try PIB's Search API which returns structured JSON with full PR content
    api_url = "https://pib.gov.in/allRel.aspx"
    index   = "https://pib.gov.in/indexd.aspx"
    tried_urls = set()
    try:
        html = SESSION.get(index, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "PressReleasePage" not in href: continue
            full = urljoin("https://pib.gov.in/", href)
            if full in tried_urls: continue
            tried_urls.add(full)
            title = a.get_text(strip=True) or "PIB Press Release"
            log(INFO, "PIB", f"Fetching: {title[:60]}")
            page_html = SESSION.get(full, timeout=30).text
            text, s = clean_html_to_text(page_html)
            # PIB PRs are naturally 150-500 words; relax structure check for them
            words = text.split()
            if len(words) < 150:
                log(WARN, "PIB", f"REJECTED -- Too short: {len(words)} words")
                continue
            for err in ("page not found", "404", "no content available"):
                if err in text[:200].lower():
                    log(WARN, "PIB", f"REJECTED -- error page")
                    break
            else:
                out = {"source": "PIB", "title": title,
                       "date": datetime.now().isoformat(), "content": text}
                p = save_json(out, "PIB_press_release_demo.json")
                log(OK, "PIB", f"Saved {p.stat().st_size//1024} KB -> {p.name}")
                return
        log(FAIL, "PIB", "No valid press release found on index page")
    except Exception as e:
        log(FAIL, "PIB", f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. DRISHTI IAS — Daily Analysis article
# ─────────────────────────────────────────────────────────────────────────────
def demo_drishtiias():
    print("\n" + "-"*60)
    print("  [7/7]  DRISHTI IAS — Daily Analysis")
    print("-"*60)
    base = "https://www.drishtiias.com"
    index = f"{base}/current-affairs-news-analysis-editorials"
    try:
        html = SESSION.get(index, timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "daily-updates" not in href: continue
            full = href if href.startswith("http") else f"{base}{href}"
            title = a.get_text(strip=True) or "Drishti Daily Update"
            if len(title) < 5: continue
            log(INFO, "DrishtiIAS", f"Fetching: {title[:60]}")
            page_html = SESSION.get(full, timeout=30).text
            text, s = clean_html_to_text(page_html)
            valid, reason = validate_article(text, s)
            if not valid:
                log(WARN, "DrishtiIAS", f"REJECTED — {reason}")
                continue
            out = {"source": "DrishtiIAS", "title": title,
                   "date": datetime.now().isoformat(), "content": text}
            p = save_json(out, "DrishtiIAS_daily_analysis_demo.json")
            log(OK, "DrishtiIAS", f"Saved {p.stat().st_size//1024} KB → {p.name}")
            return
        log(FAIL, "DrishtiIAS", "No valid article found")
    except Exception as e:
        log(FAIL, "DrishtiIAS", f"Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  UPSC SCRAPER — DEMO VALIDATION RUN (All 7 Sources)")
    print(f"  Output: {OUT}")
    print("="*60)

    t0 = time.time()
    demo_visionias()
    demo_insightsias()
    demo_forumias()
    demo_thehindu()
    demo_indianexpress()
    demo_pib()
    demo_drishtiias()

    elapsed = time.time() - t0
    files = list(OUT.glob("*"))
    print("\n" + "="*60)
    print(f"  DONE in {elapsed:.0f}s   |   Files saved: {len(files)}")
    print(f"  Location: {OUT}")
    for f in sorted(files):
        kb = f.stat().st_size / 1024
        print(f"    {f.name:<55}  {kb:>7.0f} KB")
    print("="*60)
