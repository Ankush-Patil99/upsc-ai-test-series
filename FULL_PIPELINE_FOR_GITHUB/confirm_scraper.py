"""
confirm_scraper.py - Final validation scraper for all 6 sources.
Saves latest available content from each to:
D:\\upsc test series\\data\\Scrapper test\\latest_check\\
"""

import os, re, json, time, logging
import requests, feedparser, fitz
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

OUT = Path(r"D:\upsc test series\data\Scrapper test\latest_check")
OUT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT / "scrape_log.txt", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("confirm")

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"})
S.verify = False

NOISE_TAGS = ["script","style","nav","footer","header","aside","form","button","iframe"]
NOISE_CLS  = re.compile(r'ad[-_]?|banner|share-|social|popup|widget|promo|sidebar|breadcrumb|related|newsletter', re.I)

def strip_noise(soup):
    for t in soup(NOISE_TAGS): t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLS}): t.decompose()

def save(data, fname):
    p = OUT / fname
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    wc = len(data.get("content","").split()) if "content" in data else sum(len(a.get("content","").split()) for a in data.get("articles",[]))
    log.info(f"SAVED {fname} ({p.stat().st_size//1024} KB, ~{wc:,} words)")
    return p

def validate(text, min_words=300):
    words = text.split()
    if len(words) < min_words: return False, f"too_short:{len(words)}"
    if any(e in text[:400].lower() for e in ("page not found","404","access denied")): return False, "error_page"
    return True, "ok"

# ─────────────────────────────────────────────────────────
# 1. DRISHTI IAS - Environment tag page (requests works!)
# ─────────────────────────────────────────────────────────
def scrape_drishti():
    log.info("=== [1/6] DRISHTI IAS ===")
    tag_url = "https://www.drishtiias.com/tags/biodiversity-&-environment"
    base    = "https://www.drishtiias.com"
    results = []
    try:
        soup = BeautifulSoup(S.get(tag_url, timeout=20).text, "lxml")
        links = list(dict.fromkeys([
            a["href"] if a["href"].startswith("http") else base + a["href"]
            for a in soup.find_all("a", href=True)
            if "/daily-updates/" in a.get("href","") and len(a.get_text(strip=True)) > 5
        ]))
        log.info(f"Drishti: {len(links)} article links found")
        for url in links[:3]:
            r = S.get(url, timeout=20)
            art_soup = BeautifulSoup(r.text, "lxml")
            # Use the confirmed container: div.ckeditor-content
            container = art_soup.find("div", class_="ckeditor-content")
            if not container:
                # Fallback: article-detail
                container = art_soup.find("div", class_=re.compile(r"article-detail|detail-post", re.I))
            if not container:
                log.warning(f"Drishti: no container at {url}"); continue
            # Remove noise from inside container
            for bad in container.find_all(string=re.compile(r"Test Series|Join WhatsApp|Syllabus|Mains Practice|PYQ", re.I)):
                if bad.parent: bad.parent.decompose()
            text = container.get_text("\n", strip=True)
            # Validate first 5 lines are NOT nav
            first_lines = "\n".join(text.split("\n")[:5]).lower()
            if sum(1 for w in ["home","economy","polity","test series"] if w in first_lines) >= 2:
                log.warning(f"Drishti REJECT {url}: nav_at_top"); continue
            ok, reason = validate(text)
            if not ok: log.warning(f"Drishti REJECT {url}: {reason}"); continue
            title_tag = art_soup.find("h1") or art_soup.find("h2")
            title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]
            results.append({"url": url, "title": title, "content": text})
            log.info(f"Drishti OK: {title[:65]}")
            time.sleep(0.3)
        if results:
            save({"source":"DrishtiIAS","tag":"biodiversity-environment","articles":results}, "drishti_latest.json")
        else:
            log.error("Drishti FAIL: no valid articles")
    except Exception as e:
        log.error(f"Drishti error: {e}")

# ─────────────────────────────────────────────────────────
# 2. FORUM IAS - Playwright (JS-rendered content)
# ─────────────────────────────────────────────────────────
def scrape_forumias():
    log.info("=== [2/6] FORUM IAS (Playwright) ===")
    # Get article URLs from the 9pm hub page - look for 2026 section
    index_url = "https://forumias.com/blog/9pm/"
    results   = []
    try:
        # Step 1: find URLs from the archive hub (requests is enough for index)
        soup = BeautifulSoup(S.get(index_url, timeout=20).text, "lxml")
        # Find links in the 2026 section
        article_links = []
        for h2 in soup.find_all("h2"):
            if "2026" in h2.get_text():
                nxt = h2.find_next_sibling()
                while nxt:
                    for a in nxt.find_all("a", href=True):
                        t = a.get_text(strip=True)
                        l = a["href"]
                        if ("9-pm-upsc-current-affairs" in l or "9-pm-brief" in l.lower()) and len(t) > 10:
                            article_links.append(l)
                    nxt = nxt.find_next_sibling()
                    if nxt and nxt.name == "h2": break
        article_links = list(dict.fromkeys(article_links))
        # Fallback: directly build today & yesterday's URL
        if not article_links:
            from datetime import date, timedelta
            for delta in range(0, 5):
                d = date.today() - timedelta(days=delta)
                slug = f"9-pm-upsc-current-affairs-articles-{d.day}-{d.strftime('%B').lower()}-{d.year}"
                article_links.append(f"https://forumias.com/blog/{slug}/")
        log.info(f"ForumIAS: {len(article_links)} article URLs to try")

        # Step 2: use Playwright to render JS content
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            for url in article_links[:3]:
                try:
                    page.goto(url, wait_until="networkidle", timeout=25000)
                    page.wait_for_timeout(2500)
                    art_soup = BeautifulSoup(page.content(), "lxml")
                    # ForumIAS content is split across tabs gated by JS
                    # Extract ALL text from headings (h2/h3) and their following siblings
                    content_parts = []
                    for h in art_soup.find_all(["h2","h3","h4"]):
                        heading_text = h.get_text(" ", strip=True)
                        if not heading_text or len(heading_text) < 3: continue
                        # Skip obvious nav/UI headings
                        # Keep GS Paper labels as section markers; skip pure UI noise only
                        if any(x in heading_text.lower() for x in ["previous editions","share this","click here","follow us"]): continue
                        content_parts.append(heading_text)
                        # Get text from next siblings until next heading
                        for sib in h.next_siblings:
                            if not hasattr(sib, 'name'): continue
                            if sib.name in ["h2","h3","h4"]: break
                            txt = sib.get_text(" ", strip=True)
                            if len(txt.split()) > 5:
                                content_parts.append(txt)
                    text = "\n\n".join(content_parts)
                    ok, reason = validate(text)
                    if not ok: log.warning(f"ForumIAS REJECT {url}: {reason}"); continue
                    title_tag = art_soup.find("h1") or art_soup.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-"," ").title()
                    results.append({"url": url, "title": title, "content": text})
                    log.info(f"ForumIAS OK: {title[:65]} ({len(text.split())} words)")
                    if len(results) >= 1: break
                except Exception as e:
                    log.warning(f"ForumIAS article error {url}: {e}")
            browser.close()
        if results:
            save({"source":"ForumIAS","articles":results}, "forumias_latest.json")
        else:
            log.error("ForumIAS FAIL: no valid articles extracted")
    except Exception as e:
        log.error(f"ForumIAS error: {e}")

# ─────────────────────────────────────────────────────────
# 3. INDIAN EXPRESS - RSS + clean extraction
# ─────────────────────────────────────────────────────────
def scrape_indianexpress():
    log.info("=== [3/6] INDIAN EXPRESS ===")
    results = []
    try:
        feed = feedparser.parse("https://indianexpress.com/section/india/feed/")
        for entry in feed.entries:
            if len(results) >= 3: break   # Collect up to 3 articles per run
            r = S.get(entry.link, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            article = (soup.find("div", class_=re.compile(r"full-details|article-body|story-content|ie-content|nation", re.I))
                       or soup.find("article"))
            if not article: continue
            strip_noise(article)
            for phrase in ["Written by","Trending","Follow Us","Related Articles","Advertisement"]:
                for tag in article.find_all(string=re.compile(phrase, re.I)):
                    if tag.parent: tag.parent.decompose()
            text = article.get_text("\n", strip=True)
            for cutoff in ["Related Stories","Also Read","Catch up"]:
                cut = text.find(cutoff)
                if 0 < cut: text = text[:cut]; break
            ok, reason = validate(text)
            if not ok: log.warning(f"IE REJECT {entry.link}: {reason}"); continue
            title_tag = soup.find("h1")
            title = title_tag.get_text(strip=True) if title_tag else entry.title
            results.append({"title": title, "date": entry.get("published",""),
                            "url": entry.link, "content": text})
            log.info(f"IE OK: {title[:65]}")
            time.sleep(0.3)
        if results:
            save({"source":"IndianExpress","articles":results}, "indianexpress_latest.json")
        else:
            log.error("IndianExpress FAIL: no valid articles")
    except Exception as e:
        log.error(f"IndianExpress error: {e}")

# ─────────────────────────────────────────────────────────
# 4. THE HINDU - AMP bypass
# ─────────────────────────────────────────────────────────
def scrape_thehindu():
    log.info("=== [4/6] THE HINDU (AMP) ===")
    feeds = [
        "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
        "https://www.thehindu.com/opinion/feeder/default.rss",
    ]
    try:
        for rss_url in feeds:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                amp_url = entry.link.rstrip("/") + "?amp=true"
                r = S.get(amp_url, timeout=20)
                soup = BeautifulSoup(r.text, "lxml")
                paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")
                         if len(p.get_text(strip=True).split()) > 8]
                text  = "\n\n".join(paras)
                # Remove paywall noise
                for phrase in ["Sign in","Subscribe","Related stories","Also Read"]:
                    cut = text.find(phrase)
                    if 0 < cut: text = text[:cut]; break
                if re.search(r"\bsign in\b|\bsubscribe\b", text[:300], re.I): continue
                ok, reason = validate(text)
                if not ok: log.warning(f"Hindu REJECT {entry.link}: {reason}"); continue
                save({"source":"TheHindu","title":entry.title,"date":entry.get("published",""),
                      "url":entry.link,"amp_url":amp_url,"content":text}, "thehindu_latest.json")
                return
        log.error("Hindu FAIL: no valid article via AMP")
    except Exception as e:
        log.error(f"Hindu error: {e}")

# ─────────────────────────────────────────────────────────
# 5. VISION IAS - Session-based download (proven working)
# ─────────────────────────────────────────────────────────
VISION_SESSION = Path(__file__).parent / "vision_session.json"
VISION_ARCHIVE = "https://visionias.in/current-affairs/monthly-magazine/archive"
VISION_DL_BASE = "https://visionias.in/current-affairs/download/"

def _vision_get_dl_ids(html: str) -> dict:
    """Extract {(month, year): download_id} from the Alpine.js fetch() calls in HTML."""
    result = {}
    pattern = re.compile(
        r"fetch\('https://visionias\.in/current-affairs/download/(\d+)'\)"
        r".*?a\.download\s*=\s*['\"]([^'\"]+)['\"]",
        re.S,
    )
    for m in pattern.finditer(html):
        dl_id, filename = m.group(1), m.group(2)
        m2 = re.search(
            r"(january|february|march|april|may|june|july|august|"
            r"september|october|november|december)\s*(20\d{2})",
            filename, re.I,
        )
        if m2:
            result[(m2.group(1).lower(), m2.group(2))] = dl_id
    return result

def scrape_visionias():
    log.info("=== [5/6] VISION IAS (session-based PDF download) ===")
    if not VISION_SESSION.exists():
        log.error("vision_session.json not found — run vision_setup.py first"); return
    try:
        state   = json.loads(VISION_SESSION.read_text())
        cookies = state.get("cookies", [])
        log.info(f"VisionIAS: session loaded ({len(cookies)} cookies)")

        # Load archive page with saved session
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                storage_state=str(VISION_SESSION),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )
            page.goto(VISION_ARCHIVE, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)  # React needs time to render cards

            if "login" in page.url.lower():
                log.error(f"VisionIAS: session expired (redirected to {page.url[:60]}) — re-run vision_setup.py")
                browser.close(); return

            html = page.content()
            browser.close()

        # Parse download IDs
        id_map = _vision_get_dl_ids(html)
        if not id_map:
            log.error("VisionIAS FAIL: no download IDs found — archive page may have changed")
            (OUT / "vision_debug.html").write_text(html[:150000], encoding="utf-8")
            return

        log.info(f"VisionIAS: {len(id_map)} monthly PDFs found")
        for (month, year), dl_id in id_map.items():
            log.info(f"  {month.capitalize()} {year} → ID {dl_id}")

        # Download most recent PDF
        (month, year), dl_id = next(iter(id_map.items()))
        url  = f"{VISION_DL_BASE}{dl_id}"
        path = OUT / f"vision_{month}_{year}.pdf"

        if path.exists():
            log.info(f"VisionIAS: {path.name} already exists, skipping")
            return

        # Use cookie-authenticated requests session
        vs = requests.Session()
        vs.verify = False
        vs.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
                           "Referer": VISION_ARCHIVE})
        for c in cookies:
            vs.cookies.set(c["name"], c["value"], domain=c.get("domain","visionias.in"))

        r = vs.get(url, stream=True, timeout=180)
        r.raise_for_status()
        ct = r.headers.get("Content-Type","")
        if "html" in ct.lower():
            log.error(f"VisionIAS: got HTML not PDF — session may have expired"); return

        with open(path, "wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)

        kb = path.stat().st_size / 1024
        if kb < 200:
            log.warning(f"VisionIAS: file too small ({kb:.0f} KB)"); path.unlink(); return

        doc = fitz.open(path)
        wc  = len(" ".join(pg.get_text() for pg in doc).split()); doc.close()
        log.info(f"VisionIAS SAVED: {path.name} ({kb/1024:.1f} MB, {wc:,} words)")
    except Exception as e:
        log.error(f"VisionIAS error: {e}")


# ─────────────────────────────────────────────────────────
# 6. INSIGHTS IAS - Latest monthly PDF
# ─────────────────────────────────────────────────────────
def scrape_insightsias():
    log.info("=== [6/6] INSIGHTS IAS ===")
    try:
        html = S.get("https://www.insightsonindia.com/current-affairs-downloads/", timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz","secure","answer","writing","hindi","test"]): continue
            m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})", text)
            if not m: continue
            post = BeautifulSoup(S.get(a["href"], timeout=30).text, "lxml")
            for lnk in post.find_all("a", href=True):
                if lnk["href"].endswith(".pdf") and "combined" in lnk.get_text(" ", strip=True).lower():
                    path = OUT / f"insights_{m.group(1)}_{m.group(2)}.pdf"
                    r = S.get(lnk["href"], stream=True, timeout=90)
                    r.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(1024*1024): f.write(chunk)
                    kb = path.stat().st_size / 1024
                    if kb < 500: path.unlink(); continue
                    doc = fitz.open(path)
                    wc  = len(" ".join(pg.get_text() for pg in doc).split()); doc.close()
                    if wc < 5000: path.unlink(); continue
                    log.info(f"InsightsIAS SAVED: {path.name} ({kb/1024:.1f} MB, {wc:,} words)")
                    return
            time.sleep(0.3)
        log.error("InsightsIAS FAIL: no valid monthly PDF found")
    except Exception as e:
        log.error(f"InsightsIAS error: {e}")

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 65)
    log.info("UPSC SCRAPER CONFIRMATION RUN - Latest News from All 6 Sources")
    log.info(f"Output: {OUT}")
    log.info("=" * 65)
    t0 = time.time()

    scrape_drishti()
    scrape_forumias()
    scrape_indianexpress()
    scrape_thehindu()
    scrape_visionias()
    scrape_insightsias()

    files = sorted(OUT.glob("*"))
    log.info("=" * 65)
    log.info(f"DONE in {time.time()-t0:.0f}s | {len(files)} files saved")
    for f in files:
        log.info(f"  {f.name:<55} {f.stat().st_size//1024:>7} KB")
    log.info("=" * 65)
