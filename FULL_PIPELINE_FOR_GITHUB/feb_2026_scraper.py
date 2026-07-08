"""
feb_2026_scraper.py - Fixed scraper for ALL 7 sources, February 2026 data.
Outputs to: D:\\upsc test series\\data\\Scrapper test\\feb_2026\\
"""

import os, re, json, time, logging
import requests, feedparser, fitz
from pathlib import Path
from datetime import datetime, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

# ── Setup ─────────────────────────────────────────────────────────────────────
OUT = Path(r"D:\upsc test series\data\Scrapper test\feb_2026")
OUT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUT / "scrape_log.txt", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("feb2026")

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"})
S.verify = False

NOISE_TAGS = ["script","style","nav","footer","header","aside","form","button","iframe"]
NOISE_CLS  = re.compile(r'ad[-_]?|banner|share-|social|popup|widget|promo|sidebar|breadcrumb|related|newsletter|login|subscribe', re.I)
BLOCK_TEXT = re.compile(r'\b(sign in|subscribe|test series|join whatsapp|syllabus|login|captcha|verification|awswaf)\b', re.I)

# ── Helpers ───────────────────────────────────────────────────────────────────
def strip_noise(soup):
    for t in soup(NOISE_TAGS): t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLS}): t.decompose()
    for t in soup.find_all(attrs={"id": NOISE_CLS}): t.decompose()
    return soup

def validate(text, source, min_words=300):
    words = text.split()
    if len(words) < min_words:
        return False, f"too_short:{len(words)}_words"
    if any(e in text[:500].lower() for e in ("page not found","404 error","access denied")):
        return False, "error_page"
    if any(e in text.lower() for e in ("captcha","awswaf","cf-turnstile")):
        return False, "captcha_detected"
    noise = len(BLOCK_TEXT.findall(text))
    if noise / max(1, len(words)) > 0.15:
        return False, f"noise_ratio_high:{noise}/{len(words)}"
    first5 = " ".join(words[:40]).lower()
    nav_words = ["home","polity","economy","environment","science","geography","history","current affairs","test series"]
    nav_hits = sum(1 for w in nav_words if w in first5)
    if nav_hits >= 3:
        return False, "navigation_text_at_top"
    return True, "ok"

def save_json(data, filename):
    p = OUT / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info(f"SAVED {filename} ({p.stat().st_size//1024} KB)")
    return p

def dl_pdf(url, fname, min_words=5000):
    p = OUT / fname
    if p.exists():
        log.info(f"SKIP (already exists): {fname}")
        return p
    try:
        r = S.get(url, stream=True, timeout=90)
        r.raise_for_status()
        with open(p, "wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)
        kb = p.stat().st_size / 1024
        if kb < 500:
            log.warning(f"REJECT_PDF {fname}: {kb:.0f} KB < 500 KB"); p.unlink(); return None
        doc = fitz.open(p)
        txt = " ".join(pg.get_text() for pg in doc); doc.close()
        if len(txt.split()) < min_words:
            log.warning(f"REJECT_PDF {fname}: {len(txt.split())} words < {min_words}"); p.unlink(); return None
        log.info(f"SAVED_PDF {fname} ({kb/1024:.1f} MB, {len(txt.split()):,} words)")
        return p
    except Exception as e:
        log.error(f"FAIL_PDF {fname}: {e}")
        if p.exists(): p.unlink()
        return None

# -- 1. DRISHTI IAS (Playwright - JS-rendered archive) -----------------------
def scrape_drishti():
    log.info("=== [1/7] DRISHTI IAS ===")
    archive = "https://www.drishtiias.com/daily-updates/current-affairs/february-2026"
    base    = "https://www.drishtiias.com"
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            page.goto(archive, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            soup = BeautifulSoup(html, "lxml")
            links = list(dict.fromkeys([
                a["href"] if a["href"].startswith("http") else base + a["href"]
                for a in soup.find_all("a", href=True)
                if "/daily-updates/" in a["href"]
                and any(x in a["href"] for x in ["daily-news","current-affairs"])
                and "february-2026" not in a["href"]
            ]))
            log.info(f"Drishti: found {len(links)} Feb 2026 article links")
            for url in links[:5]:
                page.goto(url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                art_html = page.content()
                art_soup = BeautifulSoup(art_html, "lxml")
                # Extract ONLY the article body - Drishti uses 'wrapper' but we need the content section
                # Find the main content by getting all <p> tags outside nav/menu
                strip_noise(art_soup)
                # Remove Drishti-specific noise
                for bad in art_soup.find_all(string=re.compile(r'Test Series|Join WhatsApp|Syllabus|Mains Practice', re.I)):
                    if bad.parent: bad.parent.decompose()
                paras = [p.get_text(" ", strip=True) for p in art_soup.find_all("p")
                         if len(p.get_text(strip=True).split()) > 10]
                text = "\n".join(paras)
                # Validate first 5 lines are not navigation
                first5 = "\n".join(paras[:5]).lower()
                nav_check = sum(1 for w in ["home","polity","economy","test series","current affairs quiz"]
                                if w in first5)
                if nav_check >= 2:
                    log.warning(f"Drishti REJECT {url}: navigation_at_top"); continue
                title_tag = art_soup.find("h1") or art_soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]
                ok, reason = validate(text, "DrishtiIAS")
                if not ok:
                    log.warning(f"Drishti REJECT {url}: {reason}"); continue
                results.append({"url": url, "title": title, "content": text})
                log.info(f"Drishti OK: {title[:60]}")
            browser.close()
        if results:
            save_json({"source":"DrishtiIAS","month":"february","year":"2026","articles":results},
                      "drishti_feb_2026.json")
        else:
            log.error("Drishti FAIL: no valid articles extracted")
    except Exception as e:
        log.error(f"Drishti error: {e}")

# -- 2. FORUM IAS (Playwright - JS-rendered articles) -------------------------
def scrape_forumias():
    log.info("=== [2/7] FORUM IAS ===")
    archive = "https://blog.forumias.com/?cat=9-pm-brief&m=202602"
    results = []
    try:
        # Get URLs from archive (requests works here)
        soup = BeautifulSoup(S.get(archive, timeout=20).text, "lxml")
        links = list(dict.fromkeys([
            a["href"] for a in soup.find_all("a", href=True)
            if "9-pm-upsc-current-affairs" in a["href"] and "2026" in a["href"] and "february" in a["href"]
        ]))
        log.info(f"ForumIAS: found {len(links)} Feb 2026 briefs")
        # Use Playwright to render article content (JS-rendered)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            for url in links[:3]:
                try:
                    page.goto(url, wait_until="networkidle", timeout=25000)
                    page.wait_for_timeout(2000)
                    art_html = page.content()
                    art_soup = BeautifulSoup(art_html, "lxml")
                    strip_noise(art_soup)
                    # ForumIAS article content is in the post body
                    paras = [p.get_text(" ", strip=True) for p in art_soup.find_all("p")
                             if len(p.get_text(strip=True).split()) > 10]
                    text = "\n".join(paras)
                    title_tag = art_soup.find("h1") or art_soup.find("h2")
                    title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-", " ")
                    ok, reason = validate(text, "ForumIAS")
                    if not ok:
                        log.warning(f"ForumIAS REJECT {url}: {reason}"); continue
                    results.append({"url": url, "title": title, "content": text})
                    log.info(f"ForumIAS OK: {title[:60]}")
                except Exception as e:
                    log.error(f"ForumIAS article error {url}: {e}")
            browser.close()
        if results:
            save_json({"source":"ForumIAS","month":"february","year":"2026","articles":results},
                      "forumias_feb_2026.json")
        else:
            log.error("ForumIAS FAIL: no valid briefs extracted")
    except Exception as e:
        log.error(f"ForumIAS error: {e}")

# ── 3. INDIAN EXPRESS ─────────────────────────────────────────────────────────
def scrape_indianexpress():
    log.info("=== [3/7] INDIAN EXPRESS ===")
    # IE archive search for Feb 2026
    search_url = "https://indianexpress.com/?s=india+february+2026&orderby=date"
    try:
        soup = BeautifulSoup(S.get(search_url, timeout=20).text, "lxml")
        links = list(dict.fromkeys([
            a["href"] for a in soup.find_all("a", href=True)
            if "indianexpress.com" in a["href"] and "/india/" in a["href"]
            and "2026/02" in a["href"]
        ]))
        # Fallback: use RSS and filter
        if not links:
            feed = feedparser.parse("https://indianexpress.com/section/india/feed/")
            links = [e.link for e in feed.entries if "indianexpress.com" in e.link]
        log.info(f"IndianExpress: {len(links)} candidates")
        results = []
        for url in links[:5]:
            try:
                r = S.get(url, timeout=20)
                page = BeautifulSoup(r.text, "lxml")
                # STRICTLY extract only the article body
                article = (page.find("div", class_=re.compile(r'full-details|article[_-]body|story[-_]?content|ie-content', re.I))
                           or page.find("article"))
                if not article:
                    log.warning(f"IE: no article container at {url}"); continue
                strip_noise(article)
                # Remove IE-specific noise
                for bad_text in ["Written by","Trending","Follow Us","Related Articles"]:
                    for tag in article.find_all(string=re.compile(bad_text, re.I)):
                        if tag.parent: tag.parent.decompose()
                # Remove numbered news lists (01 / 02 / 03)
                for tag in article.find_all(string=re.compile(r'^\s*\d{2}\s*/\s*\d{2}', re.M)):
                    if tag.parent: tag.parent.decompose()
                title_tag = page.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else "Indian Express Article"
                text  = article.get_text("\n", strip=True)
                # Clean trailing noise
                cut = text.find("Related Stories")
                if cut > 300: text = text[:cut]
                ok, reason = validate(text, "IndianExpress")
                if not ok:
                    log.warning(f"IE REJECT {url}: {reason}"); continue
                results.append({"url": url, "title": title, "content": text})
                log.info(f"IE OK: {title[:60]}")
            except Exception as e:
                log.error(f"IE article error {url}: {e}")
            time.sleep(0.3)
        if results:
            save_json({"source":"IndianExpress","month":"february","year":"2026","articles":results},
                      "indianexpress_feb_2026.json")
        else:
            log.error("IndianExpress FAIL: no valid articles extracted")
    except Exception as e:
        log.error(f"IndianExpress error: {e}")

# -- 4. PIB (Playwright with JS wait + search by text link) -------------------
def scrape_pib():
    log.info("=== [4/7] PIB (Playwright) ===")
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
            page.goto("https://pib.gov.in/indexd.aspx", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            soup = BeautifulSoup(html, "lxml")
            # After JS render, look for any <a> pointing to press releases
            pr_links = list(dict.fromkeys([
                urljoin("https://pib.gov.in/", a["href"])
                for a in soup.find_all("a", href=True)
                if "PressReleasePage" in a.get("href", "") or "pib.gov.in" in a.get("href", "")
            ]))
            # Also find links by text content
            text_links = list(dict.fromkeys([
                urljoin("https://pib.gov.in/", a["href"])
                for a in soup.find_all("a", href=True)
                if a.get_text(strip=True) and len(a.get_text(strip=True)) > 20
                and a["href"] and ".aspx" in a["href"]
                and "PressRelease" in a.get("href", "")
            ]))
            all_links = list(dict.fromkeys(pr_links + text_links))
            log.info(f"PIB: found {len(all_links)} press release links after JS render")
            visited = set()
            for url in all_links[:8]:
                if url in visited: continue
                visited.add(url)
                page.goto(url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                pr_soup = BeautifulSoup(page.content(), "lxml")
                strip_noise(pr_soup)
                # PIB content is in <div class='innner'> or all <p> tags
                content_div = pr_soup.find("div", class_=re.compile(r'innner|Inner|release|content', re.I))
                if content_div:
                    text = content_div.get_text("\n", strip=True)
                else:
                    paras = [p.get_text(" ", strip=True) for p in pr_soup.find_all("p")
                             if len(p.get_text(strip=True).split()) > 15]
                    text = "\n".join(paras)
                if len(text.split()) < 100:
                    log.warning(f"PIB REJECT {url}: {len(text.split())} words"); continue
                title_tag = pr_soup.find("h1") or pr_soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else "PIB Press Release"
                ministry_tag = pr_soup.find(string=re.compile(r'Ministry|Department', re.I))
                ministry = ministry_tag.strip() if ministry_tag else ""
                results.append({"url": url, "title": title, "ministry": ministry, "content": text})
                log.info(f"PIB OK: {title[:60]}")
                if len(results) >= 3: break
            browser.close()
        if results:
            save_json({"source":"PIB","month":"february","year":"2026","articles":results},
                      "pib_feb_2026.json")
        else:
            log.error("PIB FAIL: no valid press releases extracted")
    except Exception as e:
        log.error(f"PIB error: {e}")

# ── 5. THE HINDU (AMP bypass) ─────────────────────────────────────────────────
def scrape_thehindu():
    log.info("=== [5/7] THE HINDU (AMP bypass) ===")
    # AMP version bypasses paywall — confirmed 1534 words in probe
    feeds = [
        "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
        "https://www.thehindu.com/opinion/feeder/default.rss",
    ]
    results = []
    for rss_url in feeds:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            amp_url = entry.link.rstrip("/") + "?amp=true"
            try:
                r = S.get(amp_url, timeout=20)
                soup = BeautifulSoup(r.text, "lxml")
                # AMP pages have clean structure
                article = (soup.find("div", class_=re.compile(r'amp-article|article-content|content-body', re.I))
                           or soup.find("article")
                           or soup.find("main"))
                if not article:
                    # Fallback: get all <p> tags
                    paras = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True).split()) > 8]
                    text = "\n".join(paras)
                else:
                    strip_noise(article)
                    text = article.get_text("\n", strip=True)
                # Remove paywall noise
                for phrase in ["Sign in", "Subscribe", "Related stories", "Also read"]:
                    cut = text.find(phrase)
                    if 0 < cut < len(text) - 200: text = text[:cut]
                # Validate: no login text
                if re.search(r'\bsign in\b|\bsubscribe\b', text[:200], re.I):
                    log.warning(f"Hindu REJECT {entry.link}: login_text_present"); continue
                ok, reason = validate(text, "TheHindu")
                if not ok:
                    log.warning(f"Hindu REJECT {entry.link}: {reason}"); continue
                results.append({"url": entry.link, "amp_url": amp_url,
                                "title": entry.title, "date": entry.get("published",""),
                                "content": text})
                log.info(f"Hindu OK: {entry.title[:60]}")
                if len(results) >= 3:
                    break
            except Exception as e:
                log.error(f"Hindu article error {entry.link}: {e}")
        if len(results) >= 3:
            break
    if results:
        save_json({"source":"TheHindu","month":"february","year":"2026","articles":results},
                  "thehindu_feb_2026.json")
    else:
        log.error("Hindu FAIL: no valid articles via AMP")

# -- 6. VISION IAS (Playwright - anti-detection) ------------------------------
def scrape_visionias():
    log.info("=== [6/7] VISION IAS (Playwright anti-detection) ===")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, slow_mo=150)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                },
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )
            page = context.new_page()
            # Navigate slowly to avoid bot detection
            page.goto("https://visionias.in/", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            page.goto("https://visionias.in/current-affairs/monthly-magazine/archive",
                      wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)
            html = page.content()
            # CAPTCHA / bot-block detection
            if any(x in html.lower() for x in ["captcha","awswaf","cf-turnstile","verification required"]):
                log.error("VisionIAS FAIL: CAPTCHA/bot-block detected — site requires manual login")
                # Save diagnostic HTML
                (OUT / "vision_captcha_diagnostic.html").write_text(html[:50000], encoding="utf-8")
                browser.close()
                return
            soup = BeautifulSoup(html, "lxml")
            found = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(" ", strip=True).lower()
                if ".pdf" not in href.lower(): continue
                if any(x in text for x in ["pt365","mains365","hindi","test series"]): continue
                m = re.search(r'(february)\s*(2026)', text + " " + href.lower())
                if m:
                    full = urljoin("https://visionias.in/", href)
                    found.append((m.group(1), m.group(2), full))
                    log.info(f"VisionIAS: found PDF: {m.group(1)} {m.group(2)} -> {full[:70]}")
            browser.close()
            if found:
                month, year, url = found[0]
                dl_pdf(url, f"vision_{month}_{year}.pdf")
            else:
                log.error("VisionIAS FAIL: no February 2026 PDF found — site likely requires login for PDF links")
    except Exception as e:
        log.error(f"VisionIAS error: {e}")


# ── 7. INSIGHTS IAS (Feb 2026 PDF) ────────────────────────────────────────────
def scrape_insightsias():
    log.info("=== [7/7] INSIGHTS IAS ===")
    target_month = "february"
    target_year  = "2026"
    try:
        html = S.get("https://www.insightsonindia.com/current-affairs-downloads/", timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz","secure","answer","writing","hindi","test"]): continue
            m = re.search(r'(february)\s*(2026)', text)
            if not m: continue
            post_url = a["href"]
            log.info(f"InsightsIAS: checking post {post_url[:70]}")
            post = BeautifulSoup(S.get(post_url, timeout=30).text, "lxml")
            for lnk in post.find_all("a", href=True):
                href = lnk["href"]
                lt   = lnk.get_text(" ", strip=True).lower()
                if href.endswith(".pdf") and "combined" in lt:
                    if dl_pdf(href, f"insights_{target_month}_{target_year}.pdf"):
                        return
            time.sleep(0.5)
        log.error("InsightsIAS FAIL: no February 2026 combined PDF found")
    except Exception as e:
        log.error(f"InsightsIAS error: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 60)
    log.info("UPSC FEB 2026 SCRAPER - DEBUGGING PHASE")
    log.info(f"Output: {OUT}")
    log.info("=" * 60)
    t0 = time.time()

    scrape_drishti()
    scrape_forumias()
    scrape_indianexpress()
    scrape_pib()
    scrape_thehindu()
    scrape_visionias()
    scrape_insightsias()

    files = sorted(OUT.glob("*"))
    log.info("=" * 60)
    log.info(f"DONE in {time.time()-t0:.0f}s | Files saved: {len(files)}")
    for f in files:
        log.info(f"  {f.name:<55} {f.stat().st_size//1024:>6} KB")
    log.info("=" * 60)
