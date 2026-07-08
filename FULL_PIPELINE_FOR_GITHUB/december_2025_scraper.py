"""
december_2025_scraper.py
Scrapes ALL 6 sources for December 2025 content.
Output: D:\\upsc test series\\data\\Scrapper test\\
Files:
  1. dec2025_drishti_ias.json
  2. dec2025_forumias_9pm.json
  3. dec2025_indian_express.json
  4. dec2025_the_hindu.json
  5. dec2025_vision_ias.pdf
  6. dec2025_insights_ias.pdf
"""

import re, json, time, logging
import requests, feedparser, fitz
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

OUT          = Path(r"D:\upsc test series\data\Scrapper test")
SESSION_FILE = Path(__file__).parent / "vision_session.json"
OUT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT / "dec2025_scrape_log.txt", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("dec2025")

S = requests.Session()
S.verify = False
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"})

NOISE_TAGS = ["script","style","nav","footer","header","aside","form","button","iframe"]
NOISE_CLS  = re.compile(r'ad[-_]?|banner|share-|social|popup|widget|sidebar|breadcrumb|newsletter', re.I)

def strip_noise(soup):
    for t in soup(NOISE_TAGS): t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLS}): t.decompose()

def validate(text, min_words=300):
    words = text.split()
    if len(words) < min_words: return False, f"too_short:{len(words)}"
    if any(e in text[:400].lower() for e in ("page not found","404","access denied")): return False, "error_page"
    return True, "ok"

def save_json(data, fname):
    p = OUT / fname
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    arts = data.get("articles", [data])
    wc   = sum(len(a.get("content","").split()) for a in arts)
    log.info(f"SAVED {fname}  ({p.stat().st_size//1024} KB, ~{wc:,} words, {len(arts)} articles)")

def is_december_2025(text: str) -> bool:
    return bool(re.search(r"dec(?:ember)?\s*2025|2025[-/]12", text, re.I))

# ─────────────────────────────────────────────────────────
# 1. DRISHTI IAS
# ─────────────────────────────────────────────────────────
def scrape_drishti():
    log.info("=== [1/6] DRISHTI IAS — December 2025 ===")
    base    = "https://www.drishtiias.com"
    results = []
    try:
        # Paginate the tag page to find December 2025 articles
        for page_num in range(1, 8):
            url  = f"{base}/tags/biodiversity-&-environment" + (f"?page={page_num}" if page_num > 1 else "")
            soup = BeautifulSoup(S.get(url, timeout=20).text, "lxml")
            links_found = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/daily-updates/" not in href: continue
                if len(a.get_text(strip=True)) < 5: continue
                full = href if href.startswith("http") else base + href
                if full in [r["url"] for r in results]: continue

                art = BeautifulSoup(S.get(full, timeout=20).text, "lxml")
                # Check date on article page
                date_tag = art.find(attrs={"class": re.compile(r"date|time|published", re.I)})
                date_text = date_tag.get_text(strip=True) if date_tag else ""
                # Also check meta tag
                meta_date = art.find("meta", {"name": re.compile(r"date|publish", re.I)})
                if meta_date: date_text += " " + meta_date.get("content","")

                if not is_december_2025(date_text):
                    # Check URL for date hint
                    if not is_december_2025(full):
                        # Check article text for date
                        preview = art.get_text()[:500]
                        if not is_december_2025(preview):
                            continue

                container = art.find("div", class_="ckeditor-content") or \
                            art.find("div", class_=re.compile(r"article-detail|detail-post", re.I))
                if not container: continue

                for bad in container.find_all(string=re.compile(r"Test Series|Join WhatsApp|Syllabus", re.I)):
                    if bad.parent: bad.parent.decompose()

                text = container.get_text("\n", strip=True)
                ok, reason = validate(text)
                if not ok: continue

                title_tag = art.find("h1") or art.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else full.split("/")[-1]
                results.append({"url": full, "title": title, "date": date_text, "content": text})
                log.info(f"  Drishti OK: {title[:65]}")
                links_found += 1
                time.sleep(0.3)
                if len(results) >= 10: break

            if len(results) >= 10: break
            # If this page had no Dec 2025 links at all, keep paginating
            # If page has no links at all, stop
            if not soup.find_all("a", href=lambda h: h and "/daily-updates/" in h):
                log.info(f"  Drishti: no more pages at page {page_num}")
                break
            time.sleep(0.5)

        if results:
            save_json({"source":"DrishtiIAS","month":"December 2025","articles":results},
                      "dec2025_drishti_ias.json")
        else:
            log.error("Drishti: no December 2025 articles found")
    except Exception as e:
        log.error(f"Drishti error: {e}")

# ─────────────────────────────────────────────────────────
# 2. FORUM IAS - 9PM Briefs December 2025
# ─────────────────────────────────────────────────────────
def scrape_forumias():
    log.info("=== [2/6] FORUM IAS — December 2025 9PM Briefs ===")
    results = []
    try:
        # Get December 2025 article links from the 9PM hub
        hub   = "https://forumias.com/blog/9pm/"
        soup  = BeautifulSoup(S.get(hub, timeout=20).text, "lxml")
        dec_links = []
        for h2 in soup.find_all("h2"):
            if "2025" in h2.get_text():
                nxt = h2.find_next_sibling()
                while nxt:
                    for a in nxt.find_all("a", href=True):
                        href = a["href"]
                        text = a.get_text(strip=True).lower()
                        if ("9-pm-upsc" in href or "9-pm-brief" in href) and "december" in text:
                            dec_links.append(href)
                    nxt = nxt.find_next_sibling()
                    if nxt and nxt.name == "h2": break

        # Fallback: construct URLs for key December dates
        if not dec_links:
            for day in [1,5,10,15,20,25,30,31]:
                dec_links.append(
                    f"https://forumias.com/blog/9-pm-upsc-current-affairs-articles-{day}-december-2025/"
                )

        dec_links = list(dict.fromkeys(dec_links))
        log.info(f"  ForumIAS: {len(dec_links)} December links to try")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page    = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            for url in dec_links:
                if len(results) >= 5: break
                try:
                    page.goto(url, wait_until="networkidle", timeout=25000)
                    page.wait_for_timeout(2500)
                    art_soup = BeautifulSoup(page.content(), "lxml")

                    content_parts = []
                    for h in art_soup.find_all(["h2","h3","h4"]):
                        ht = h.get_text(" ", strip=True)
                        if not ht or len(ht) < 3: continue
                        if any(x in ht.lower() for x in ["previous editions","share this","click here","follow us"]): continue
                        content_parts.append(ht)
                        for sib in h.next_siblings:
                            if not hasattr(sib, "name"): continue
                            if sib.name in ["h2","h3","h4"]: break
                            txt = sib.get_text(" ", strip=True)
                            if len(txt.split()) > 5: content_parts.append(txt)

                    text = "\n\n".join(content_parts)
                    ok, reason = validate(text)
                    if not ok:
                        log.warning(f"  ForumIAS REJECT {url}: {reason}"); continue

                    title_tag = art_soup.find("h1") or art_soup.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-"," ").title()
                    results.append({"url": url, "title": title, "content": text})
                    log.info(f"  ForumIAS OK: {title[:65]} ({len(text.split())} words)")
                except Exception as e:
                    log.warning(f"  ForumIAS error {url}: {e}")
            browser.close()

        if results:
            save_json({"source":"ForumIAS","month":"December 2025","articles":results},
                      "dec2025_forumias_9pm.json")
        else:
            log.error("ForumIAS: no December 2025 articles found")
    except Exception as e:
        log.error(f"ForumIAS error: {e}")

# ─────────────────────────────────────────────────────────
# 3. INDIAN EXPRESS — December 2025
# ─────────────────────────────────────────────────────────
def scrape_indianexpress():
    log.info("=== [3/6] INDIAN EXPRESS — December 2025 ===")
    results = []
    try:
        # Use their sitemap to find December 2025 articles
        sitemap_url = "https://indianexpress.com/sitemap.xml?yyyy=2025&mm=12"
        r = S.get(sitemap_url, timeout=30)
        urls = re.findall(r"<loc>(https://indianexpress\.com/article/[^<]+)</loc>", r.text)

        # Fallback: search page
        if not urls:
            search = S.get("https://indianexpress.com/search/current-affairs/?daterange=12/01/2025-12/31/2025", timeout=20)
            soup   = BeautifulSoup(search.text, "lxml")
            urls   = [a["href"] for a in soup.find_all("a", href=re.compile(r"indianexpress\.com/article/"))
                      if is_december_2025(a.get("href",""))]

        # Further fallback: UPSC-tagged articles
        if not urls:
            cat = BeautifulSoup(S.get("https://indianexpress.com/section/upsc-current-affairs/", timeout=20).text, "lxml")
            urls = [a["href"] for a in cat.find_all("a", href=re.compile(r"/article/")) if len(a.get_text(strip=True)) > 10]

        log.info(f"  IE: {len(urls)} candidate URLs")

        for url in urls[:30]:
            if len(results) >= 5: break
            try:
                r    = S.get(url, timeout=20)
                soup = BeautifulSoup(r.text, "lxml")
                # Must be December 2025
                date_meta = soup.find("meta", {"property": "article:published_time"})
                date_str  = date_meta["content"] if date_meta else ""
                if date_str and not is_december_2025(date_str):
                    continue

                article = (soup.find("div", class_=re.compile(r"full-details|article-body|story-content|ie-content", re.I))
                           or soup.find("article"))
                if not article: continue
                strip_noise(article)
                for phrase in ["Written by","Trending","Follow Us","Advertisement"]:
                    for tag in article.find_all(string=re.compile(phrase, re.I)):
                        if tag.parent: tag.parent.decompose()
                text = article.get_text("\n", strip=True)
                for cutoff in ["Related Stories","Also Read"]:
                    cut = text.find(cutoff)
                    if cut > 0: text = text[:cut]; break
                ok, reason = validate(text)
                if not ok: continue
                title_tag = soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2]
                results.append({"url": url, "title": title, "date": date_str, "content": text})
                log.info(f"  IE OK: {title[:65]}")
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"  IE error {url}: {e}")

        if results:
            save_json({"source":"IndianExpress","month":"December 2025","articles":results},
                      "dec2025_indian_express.json")
        else:
            log.error("IndianExpress: no December 2025 articles found")
    except Exception as e:
        log.error(f"IndianExpress error: {e}")

# ─────────────────────────────────────────────────────────
# 4. THE HINDU — December 2025 Editorials
# ─────────────────────────────────────────────────────────
def scrape_thehindu():
    log.info("=== [4/6] THE HINDU — December 2025 Editorials ===")
    results = []
    try:
        # The Hindu archive by month
        archive_url = "https://www.thehindu.com/opinion/editorial/?date=2025-12"
        r    = S.get(archive_url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")
        links = list(dict.fromkeys([
            a["href"] for a in soup.find_all("a", href=True)
            if "/opinion/editorial/" in a["href"] and "2025" in a["href"]
        ]))

        # Fallback: RSS-based approach for December articles
        if not links:
            feed = feedparser.parse("https://www.thehindu.com/opinion/editorial/feeder/default.rss")
            for entry in feed.entries:
                if is_december_2025(entry.get("published","")):
                    links.append(entry.link)

        log.info(f"  Hindu: {len(links)} December editorial links")

        for url in links[:10]:
            if len(results) >= 5: break
            try:
                amp_url = url.rstrip("/") + "?amp=true"
                r       = S.get(amp_url, timeout=20)
                soup2   = BeautifulSoup(r.text, "lxml")
                paras   = [p.get_text(" ", strip=True) for p in soup2.find_all("p")
                           if len(p.get_text(strip=True).split()) > 5]
                text    = "\n\n".join(paras)
                for phrase in ["Sign in","Subscribe","Related stories","Also Read"]:
                    cut = text.find(phrase)
                    if 0 < cut: text = text[:cut]; break
                if re.search(r"\bsign in\b|\bsubscribe\b", text[:300], re.I): continue
                ok, reason = validate(text)
                if not ok: continue
                # Find title
                title_tag = soup2.find("h1") or soup2.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-"," ").title()
                results.append({"url": url, "title": title, "content": text})
                log.info(f"  Hindu OK: {title[:65]}")
                time.sleep(0.3)
            except Exception as e:
                log.warning(f"  Hindu error {url}: {e}")

        if results:
            save_json({"source":"TheHindu","month":"December 2025","articles":results},
                      "dec2025_the_hindu.json")
        else:
            log.error("TheHindu: no December 2025 articles found")
    except Exception as e:
        log.error(f"Hindu error: {e}")

# ─────────────────────────────────────────────────────────
# 5. VISION IAS — December 2025 PDF (ID: 13245)
# ─────────────────────────────────────────────────────────
def scrape_visionias():
    log.info("=== [5/6] VISION IAS — December 2025 PDF ===")
    dest = OUT / "dec2025_vision_ias.pdf"
    if dest.exists():
        log.info(f"  Already exists: {dest.name}"); return

    if not SESSION_FILE.exists():
        log.error("  vision_session.json not found — run vision_setup.py first"); return

    try:
        state   = json.loads(SESSION_FILE.read_text())
        cookies = state.get("cookies", [])

        # Load archive to discover December 2025 ID
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
            ctx  = browser.new_context(
                storage_state=str(SESSION_FILE),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
            )
            page = ctx.new_page()
            page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
            page.goto("https://visionias.in/current-affairs/monthly-magazine/archive",
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(8000)
            html = page.content()
            browser.close()

        # Parse ID for December 2025
        pattern = re.compile(
            r"fetch\('https://visionias\.in/current-affairs/download/(\d+)'\)"
            r".*?a\.download\s*=\s*['\"]([^'\"]+)['\"]", re.S,
        )
        dl_id = None
        for m in pattern.finditer(html):
            if is_december_2025(m.group(2)):
                dl_id = m.group(1)
                log.info(f"  Vision IAS December 2025 → ID {dl_id}")
                break

        if not dl_id:
            log.error("  VisionIAS: December 2025 ID not found in archive page"); return

        vs = requests.Session()
        vs.verify = False
        vs.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
            "Referer": "https://visionias.in/current-affairs/monthly-magazine/archive",
        })
        for c in cookies:
            vs.cookies.set(c["name"], c["value"], domain=c.get("domain","visionias.in"))

        r = vs.get(f"https://visionias.in/current-affairs/download/{dl_id}", stream=True, timeout=180)
        r.raise_for_status()
        if "html" in r.headers.get("Content-Type","").lower():
            log.error("  VisionIAS: got HTML — session may have expired"); return

        with open(dest, "wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)

        kb = dest.stat().st_size / 1024
        doc = fitz.open(dest)
        wc  = len(" ".join(pg.get_text() for pg in doc).split()); doc.close()
        log.info(f"  VisionIAS SAVED: {dest.name} ({kb/1024:.1f} MB, {wc:,} words)")
    except Exception as e:
        log.error(f"VisionIAS error: {e}")

# ─────────────────────────────────────────────────────────
# 6. INSIGHTS IAS — December 2025 PDF
# ─────────────────────────────────────────────────────────
def scrape_insightsias():
    log.info("=== [6/6] INSIGHTS IAS — December 2025 PDF ===")
    dest = OUT / "dec2025_insights_ias.pdf"
    if dest.exists():
        log.info(f"  Already exists: {dest.name}"); return
    try:
        html = S.get("https://www.insightsonindia.com/current-affairs-downloads/", timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz","secure","answer","writing","hindi","test"]): continue
            if not is_december_2025(text): continue

            post = BeautifulSoup(S.get(a["href"], timeout=30).text, "lxml")
            for lnk in post.find_all("a", href=True):
                if not lnk["href"].endswith(".pdf"): continue
                if "combined" not in lnk.get_text(" ", strip=True).lower(): continue

                r = S.get(lnk["href"], stream=True, timeout=120)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1024*1024): f.write(chunk)
                kb = dest.stat().st_size / 1024
                if kb < 500: dest.unlink(); continue

                doc = fitz.open(dest)
                wc  = len(" ".join(pg.get_text() for pg in doc).split()); doc.close()
                if wc < 5000: dest.unlink(); continue

                log.info(f"  InsightsIAS SAVED: {dest.name} ({kb/1024:.1f} MB, {wc:,} words)")
                return
        log.error("InsightsIAS: December 2025 PDF not found")
    except Exception as e:
        log.error(f"InsightsIAS error: {e}")

# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time as _time
    log.info("=" * 65)
    log.info("DECEMBER 2025 — Full Scrape (All 6 Sources)")
    log.info(f"Output: {OUT}")
    log.info("=" * 65)
    t0 = _time.time()

    scrape_drishti()
    scrape_forumias()
    scrape_indianexpress()
    scrape_thehindu()
    scrape_visionias()
    scrape_insightsias()

    files = [f for f in OUT.glob("dec2025_*") if f.is_file()]
    log.info("=" * 65)
    log.info(f"DONE in {_time.time()-t0:.0f}s | {len(files)}/6 files created")
    for f in sorted(files):
        log.info(f"  {f.name:<45} {f.stat().st_size//1024:>7,} KB")
    log.info("=" * 65)
