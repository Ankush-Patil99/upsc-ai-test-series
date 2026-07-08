"""
master_scraper_pipeline.py

Unified, Production-Ready UPSC Current Affairs Scraper.
Designed to be pushed to Git for the Question Generation team.

Key Features:
1. Unified Output: ALL text articles from all sources are merged into a SINGLE 
   `articles_master.json` file. No more file clutter.
2. Deduplication: Maintains a `scrape_registry.json` to never scrape the same URL twice.
3. Comprehensive: For ForumIAS, it checks ALL days of the month (no arbitrary limits).
4. Dual Mode: Can be run for the `latest` daily news or a specific `historical` month.
5. PDFs: Saved neatly into a dedicated `pdfs/` directory.

Sources: Drishti IAS, ForumIAS, Indian Express, The Hindu, Vision IAS, Insights IAS.
"""

import os, re, json, time, logging, argparse
import requests, feedparser, fitz
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3

urllib3.disable_warnings()

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = Path(r"D:\upsc test series\data\Scraper_Pipeline")
PDF_DIR  = BASE_DIR / "pdfs"
JSON_OUT = BASE_DIR / "articles_master.json"
REGISTRY = BASE_DIR / "scrape_registry.json"
SESSION_FILE = Path(__file__).parent / "vision_session.json"

BASE_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "pipeline_log.txt", mode="a", encoding="utf-8")
    ]
)
log = logging.getLogger("pipeline")

S = requests.Session()
S.verify = False
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"})

NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "button", "iframe"]
NOISE_CLS  = re.compile(r'ad[-_]?|banner|share-|social|popup|widget|sidebar|breadcrumb|newsletter', re.I)

# ─── Helper Functions ─────────────────────────────────────────────────────────

def strip_noise(soup):
    for t in soup(NOISE_TAGS): t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLS}): t.decompose()

def validate(text, min_words=300):
    words = text.split()
    if len(words) < min_words: return False, f"too_short:{len(words)}"
    if any(e in text[:400].lower() for e in ("page not found", "404", "access denied")): return False, "error_page"
    return True, "ok"

def load_registry():
    if REGISTRY.exists():
        try: return json.loads(REGISTRY.read_text(encoding="utf-8"))
        except: return {"urls": [], "pdfs": []}
    return {"urls": [], "pdfs": []}

def save_registry(reg):
    REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")

def is_scraped(url, reg, type_="urls"):
    return url in reg[type_]

def mark_scraped(url, reg, type_="urls"):
    if url not in reg[type_]:
        reg[type_].append(url)
        save_registry(reg)

def append_article(source, title, date, url, content):
    """Appends an article to the single master JSON file."""
    if JSON_OUT.exists():
        try:
            data = json.loads(JSON_OUT.read_text(encoding="utf-8"))
        except:
            data = []
    else:
        data = []
    
    data.append({
        "source": source,
        "title": title.strip(),
        "date": date.strip(),
        "url": url,
        "content": content.strip(),
        "scraped_at": datetime.now().isoformat()
    })
    
    JSON_OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"[{source}] SAVED: {title[:60]}... ({len(content.split())} words)")


def matches_month_year(text: str, target_month: str, target_year: str) -> bool:
    """Check if the text contains the target month and year."""
    if not target_month or not target_year: return True
    pattern = rf"(?i)({target_month[:3]}[a-z]*)[^a-zA-Z0-9]*({target_year})"
    return bool(re.search(pattern, text))

# ─── 1. DRISHTI IAS ───────────────────────────────────────────────────────────
def scrape_drishti(target_month=None, target_year=None, reg=None):
    log.info("--- DRISHTI IAS ---")
    base = "https://www.drishtiias.com"
    count = 0
    max_pages = 10 if target_month else 2
    
    try:
        for page_num in range(1, max_pages + 1):
            url = f"{base}/tags/biodiversity-&-environment" + (f"?page={page_num}" if page_num > 1 else "")
            r = S.get(url, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.text, "lxml")
            links = []
            
            for a in soup.find_all("a", href=True):
                if "/daily-updates/" in a["href"] and len(a.get_text(strip=True)) > 5:
                    full = a["href"] if a["href"].startswith("http") else base + a["href"]
                    if not is_scraped(full, reg): links.append(full)
            
            links = list(dict.fromkeys(links))
            if not links: continue

            for link in links:
                if target_month and count >= 30: break # Safey limit per run
                elif not target_month and count >= 5: break
                
                try:
                    art_r = S.get(link, timeout=20)
                    art_soup = BeautifulSoup(art_r.text, "lxml")
                    
                    # Date verification
                    date_tag = art_soup.find(attrs={"class": re.compile(r"date|time|published", re.I)})
                    date_text = date_tag.get_text(strip=True) if date_tag else ""
                    if target_month and not matches_month_year(date_text + " " + link, target_month, target_year):
                        continue

                    container = art_soup.find("div", class_="ckeditor-content") or \
                                art_soup.find("div", class_=re.compile(r"article-detail|detail-post", re.I))
                    if not container: continue

                    for bad in container.find_all(string=re.compile(r"Test Series|Join WhatsApp|Syllabus", re.I)):
                        if bad.parent: bad.parent.decompose()

                    text = container.get_text("\n", strip=True)
                    ok, _ = validate(text)
                    if not ok: continue

                    title_tag = art_soup.find("h1") or art_soup.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else link.split("/")[-1]
                    
                    append_article("DrishtiIAS", title, date_text, link, text)
                    mark_scraped(link, reg)
                    count += 1
                    time.sleep(0.3)
                except Exception as e:
                    log.debug(f"Drishti article error {link}: {e}")
                    
            if (not target_month and count >= 5) or (target_month and count >= 30): break
    except Exception as e:
        log.error(f"Drishti error: {e}")
    log.info(f"Drishti: {count} articles processed.")

# ─── 2. FORUM IAS (Playwright) ────────────────────────────────────────────────
def scrape_forumias(target_month=None, target_year=None, reg=None):
    log.info("--- FORUM IAS (9PM Briefs) ---")
    urls_to_try = []
    
    if target_month and target_year:
        # Generate ALL days for the target month
        # This fixes the issue of missing days!
        for day in range(1, 32):
            slug = f"9-pm-upsc-current-affairs-articles-{day}-{target_month.lower()}-{target_year}"
            urls_to_try.append(f"https://forumias.com/blog/{slug}/")
    else:
        # Latest mode: Just try the last 5 days
        for delta in range(0, 5):
            d = datetime.now() - timedelta(days=delta)
            slug = f"9-pm-upsc-current-affairs-articles-{d.day}-{d.strftime('%B').lower()}-{d.year}"
            urls_to_try.append(f"https://forumias.com/blog/{slug}/")

    # Filter out already scraped
    urls_to_try = [u for u in urls_to_try if not is_scraped(u, reg)]
    if not urls_to_try:
        log.info("ForumIAS: No new URLs to check.")
        return

    count = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
        
        for url in urls_to_try:
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=25000)
                if resp.status == 404: 
                    continue # Day might not have an article (e.g. Sunday)
                page.wait_for_timeout(2500)
                art_soup = BeautifulSoup(page.content(), "lxml")

                content_parts = []
                for h in art_soup.find_all(["h2", "h3", "h4"]):
                    ht = h.get_text(" ", strip=True)
                    if not ht or len(ht) < 3: continue
                    if any(x in ht.lower() for x in ["previous editions", "share this", "click here", "follow us"]): continue
                    content_parts.append(ht)
                    for sib in h.next_siblings:
                        if not hasattr(sib, "name"): continue
                        if sib.name in ["h2", "h3", "h4"]: break
                        txt = sib.get_text(" ", strip=True)
                        if len(txt.split()) > 5: content_parts.append(txt)

                text = "\n\n".join(content_parts)
                ok, _ = validate(text)
                if not ok: continue

                title_tag = art_soup.find("h1") or art_soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-", " ").title()
                
                # Derive date from URL
                date_match = re.search(r"articles-(\d+)-([a-z]+)-(\d{4})", url, re.I)
                date_str = f"{date_match.group(1)} {date_match.group(2).capitalize()} {date_match.group(3)}" if date_match else ""

                append_article("ForumIAS", title, date_str, url, text)
                mark_scraped(url, reg)
                count += 1
            except Exception as e:
                log.debug(f"ForumIAS error {url}: {e}")
        browser.close()
    log.info(f"ForumIAS: {count} briefs processed.")

# ─── 3. INDIAN EXPRESS ────────────────────────────────────────────────────────
def scrape_indianexpress(target_month=None, target_year=None, reg=None):
    log.info("--- INDIAN EXPRESS ---")
    candidate_urls = []
    
    try:
        if target_month and target_year:
            # Month lookup via sitemap (Sample every day to get enough articles)
            month_map = {"january":"01","february":"02","march":"03","april":"04","may":"05","june":"06",
                         "july":"07","august":"08","september":"09","october":"10","november":"11","december":"12"}
            mm = month_map.get(target_month.lower(), "01")
            for day in range(1, 32, 2):
                sm_url = f"https://indianexpress.com/sitemap.xml?yyyy={target_year}&mm={mm}&dd={day:02d}"
                r = S.get(sm_url, timeout=10)
                if r.status_code == 200:
                    candidate_urls.extend(re.findall(r"<loc>(https://indianexpress\.com/article/[^<]+)</loc>", r.text))
        else:
            # Latest lookup via RSS
            feed = feedparser.parse("https://indianexpress.com/section/india/feed/")
            candidate_urls = [entry.link for entry in feed.entries]

        candidate_urls = list(dict.fromkeys(u for u in candidate_urls if not is_scraped(u, reg)))
        
        count = 0
        for url in candidate_urls[:100]:
            if (not target_month and count >= 5) or (target_month and count >= 15): break
            try:
                r = S.get(url, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                
                date_meta = soup.find("meta", {"property": "article:published_time"})
                date_str = date_meta.get("content", "") if date_meta else ""
                
                if target_month and not matches_month_year(date_str, target_month, target_year):
                    continue

                article = soup.find("div", class_=re.compile(r"full-details|article-body|story-content|ie-content", re.I)) or soup.find("article")
                if not article: continue
                
                strip_noise(article)
                for phrase in ["Written by", "Trending", "Follow Us", "Advertisement"]:
                    for tag in article.find_all(string=re.compile(phrase, re.I)):
                        if tag.parent: tag.parent.decompose()
                
                text = article.get_text("\n", strip=True)
                for cutoff in ["Related Stories", "Also Read"]:
                    cut = text.find(cutoff)
                    if cut > 0: text = text[:cut]; break
                
                ok, _ = validate(text)
                if not ok: continue
                
                title_tag = soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2]
                
                append_article("IndianExpress", title, date_str, url, text)
                mark_scraped(url, reg)
                count += 1
                time.sleep(0.3)
            except Exception as e:
                pass
    except Exception as e:
        log.error(f"IE error: {e}")
    log.info(f"IndianExpress: {count} articles processed.")

# ─── 4. THE HINDU ─────────────────────────────────────────────────────────────
def scrape_thehindu(target_month=None, target_year=None, reg=None):
    log.info("--- THE HINDU (Editorials) ---")
    candidate_urls = []
    
    try:
        if target_month and target_year:
            # Note: The Hindu paywalls content >30 days old. We try archive pages but expect failures.
            for day in [1, 5, 10, 15, 20, 25, 28]:
                month_num = datetime.strptime(target_month, "%B").month
                archive = f"https://www.thehindu.com/archive/web/{target_year}/{month_num:02d}/{day:02d}/"
                try:
                    r = S.get(archive, timeout=10)
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        if "opinion/editorial" in a["href"]:
                            href = a["href"] if a["href"].startswith("http") else "https://www.thehindu.com" + a["href"]
                            candidate_urls.append(href)
                except: pass
        else:
            # Latest RSS
            feeds = ["https://www.thehindu.com/opinion/editorial/feeder/default.rss"]
            for rss in feeds:
                feed = feedparser.parse(rss)
                candidate_urls.extend([e.link for e in feed.entries])

        candidate_urls = list(dict.fromkeys(u for u in candidate_urls if not is_scraped(u, reg)))
        
        count = 0
        for url in candidate_urls[:30]:
            if (not target_month and count >= 5) or (target_month and count >= 15): break
            try:
                amp_url = url.rstrip("/") + "?amp=true" # AMP bypass
                r = S.get(amp_url, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                
                paras = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True).split()) > 5]
                text = "\n\n".join(paras)
                
                for phrase in ["Sign in", "Subscribe", "Related stories"]:
                    cut = text.find(phrase)
                    if cut > 0: text = text[:cut]; break
                if re.search(r"\bsign in\b|\bsubscribe\b", text[:300], re.I): continue
                
                ok, _ = validate(text)
                if not ok: continue
                
                title_tag = soup.find("h1") or soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-", " ").title()
                
                append_article("TheHindu", title, "", url, text)
                mark_scraped(url, reg)
                count += 1
                time.sleep(0.3)
            except Exception as e:
                pass
    except Exception as e:
        log.error(f"Hindu error: {e}")
    log.info(f"TheHindu: {count} articles processed.")

# ─── 5. VISION IAS (PDF) ──────────────────────────────────────────────────────
def scrape_visionias(target_month=None, target_year=None, reg=None):
    log.info("--- VISION IAS (PDFs) ---")
    if not SESSION_FILE.exists():
        log.error("vision_session.json not found! Please run vision_setup.py first.")
        return

    try:
        state = json.loads(SESSION_FILE.read_text())
        cookies = state.get("cookies", [])
        
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                storage_state=str(SESSION_FILE),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
            )
            page = ctx.new_page()
            page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
            page.goto("https://visionias.in/current-affairs/monthly-magazine/archive", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)
            html = page.content()
            browser.close()

        pattern = re.compile(
            r"fetch\('https://visionias\.in/current-affairs/download/(\d+)'\).*?a\.download\s*=\s*['\"]([^'\"]+)['\"]", re.S
        )
        
        found = False
        for m in pattern.finditer(html):
            dl_id, filename = m.group(1), m.group(2)
            m2 = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})", filename, re.I)
            if not m2: continue
            
            m_name, m_year = m2.group(1).lower(), m2.group(2)
            
            if target_month and target_year:
                if m_name != target_month.lower() or m_year != target_year: continue
            
            pdf_id = f"vision_{m_name}_{m_year}"
            if is_scraped(pdf_id, reg, type_="pdfs"): continue

            dest = PDF_DIR / f"{pdf_id}.pdf"
            
            # Download via session
            vs = requests.Session()
            vs.verify = False
            vs.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0", "Referer": "https://visionias.in/current-affairs/monthly-magazine/archive"})
            for c in cookies: vs.cookies.set(c["name"], c["value"], domain=c.get("domain", "visionias.in"))
            
            r = vs.get(f"https://visionias.in/current-affairs/download/{dl_id}", stream=True, timeout=180)
            if "html" in r.headers.get("Content-Type", "").lower():
                log.error("VisionIAS session expired. Re-run vision_setup.py")
                return

            with open(dest, "wb") as f:
                for chunk in r.iter_content(1024*1024): f.write(chunk)
            
            kb = dest.stat().st_size / 1024
            if kb > 500:
                log.info(f"VisionIAS SAVED: {dest.name} ({kb/1024:.1f} MB)")
                mark_scraped(pdf_id, reg, type_="pdfs")
                found = True
            else:
                dest.unlink()
                
            if target_month: break # Only need one if specific month targeted

        if not found and target_month:
            log.warning(f"VisionIAS: No PDF found for {target_month} {target_year}")
            
    except Exception as e:
        log.error(f"VisionIAS error: {e}")

# ─── 6. INSIGHTS IAS (PDF) ────────────────────────────────────────────────────
def scrape_insightsias(target_month=None, target_year=None, reg=None):
    log.info("--- INSIGHTS IAS (PDFs) ---")
    try:
        html = S.get("https://www.insightsonindia.com/current-affairs-downloads/", timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        found = False
        
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz", "secure", "answer", "writing", "hindi", "test"]): continue
            
            m2 = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})", text)
            if not m2: continue
            
            m_name, m_year = m2.group(1).lower(), m2.group(2)
            if target_month and target_year:
                if m_name != target_month.lower() or m_year != target_year: continue

            pdf_id = f"insights_{m_name}_{m_year}"
            if is_scraped(pdf_id, reg, type_="pdfs"): continue

            post = BeautifulSoup(S.get(a["href"], timeout=30).text, "lxml")
            for lnk in post.find_all("a", href=True):
                if lnk["href"].endswith(".pdf") and "combined" in lnk.get_text(" ", strip=True).lower():
                    dest = PDF_DIR / f"{pdf_id}.pdf"
                    r = S.get(lnk["href"], stream=True, timeout=120)
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(1024*1024): f.write(chunk)
                    
                    kb = dest.stat().st_size / 1024
                    if kb > 500:
                        log.info(f"InsightsIAS SAVED: {dest.name} ({kb/1024:.1f} MB)")
                        mark_scraped(pdf_id, reg, type_="pdfs")
                        found = True
                        break
                    else:
                        dest.unlink()
            if target_month: break

        if not found and target_month:
            log.warning(f"InsightsIAS: No PDF found for {target_month} {target_year}")

    except Exception as e:
        log.error(f"InsightsIAS error: {e}")

# ─── MAIN PIPELINE RUNNER ─────────────────────────────────────────────────────

def run_pipeline(mode="latest", target_month=None, target_year=None):
    log.info("=" * 70)
    log.info(f"UPSC SCRAPER PIPELINE STARTED | Mode: {mode.upper()}")
    if mode == "historical":
        log.info(f"Target: {target_month.capitalize()} {target_year}")
    log.info(f"Output JSON: {JSON_OUT}")
    log.info(f"Output PDFs: {PDF_DIR}")
    log.info("=" * 70)
    
    t0 = time.time()
    reg = load_registry()
    
    scrape_drishti(target_month, target_year, reg)
    scrape_forumias(target_month, target_year, reg)
    scrape_indianexpress(target_month, target_year, reg)
    scrape_thehindu(target_month, target_year, reg)
    scrape_visionias(target_month, target_year, reg)
    scrape_insightsias(target_month, target_year, reg)
    
    log.info("=" * 70)
    log.info(f"PIPELINE COMPLETE in {time.time()-t0:.0f}s")
    
    # Print quick stats
    if JSON_OUT.exists():
        data = json.loads(JSON_OUT.read_text(encoding="utf-8"))
        log.info(f"Total articles in Master JSON: {len(data)}")
    
    pdfs = list(PDF_DIR.glob("*.pdf"))
    log.info(f"Total downloaded PDFs in vault: {len(pdfs)}")
    log.info("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UPSC Current Affairs Scraper Pipeline")
    parser.add_argument("--mode", choices=["latest", "historical"], default="latest", help="Scrape latest news or historical month.")
    parser.add_argument("--month", type=str, help="Month name (e.g., December) for historical mode.")
    parser.add_argument("--year", type=str, help="Year (e.g., 2025) for historical mode.")
    args = parser.parse_args()

    if args.mode == "historical" and (not args.month or not args.year):
        print("Error: --month and --year are required for historical mode.")
        exit(1)

    run_pipeline(args.mode, args.month, args.year)
