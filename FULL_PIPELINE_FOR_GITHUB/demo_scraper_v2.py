"""
demo_scraper_v2.py - Final validated demo for all 7 sources.
Saves one sample to D:\\upsc test series\\data\\Scrapper test
NOTE: The Hindu is paywalled; we save the richest available RSS metadata as the demo.
"""

import os, re, json, time, sys
import requests, feedparser
import fitz
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import urllib3
urllib3.disable_warnings()

OUT = Path(r"D:\upsc test series\data\Scrapper test")
OUT.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
SESSION.verify = False

def log(status, source, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  {ts} | {status:6s} | [{source}] {msg}")

NOISE_TAGS   = ["script","style","nav","footer","header","aside","form","button"]
NOISE_CLS_RE = re.compile(r'ad[-_]?|banner|share|social|popup|widget|promo|sidebar|breadcrumb', re.I)
NOISE_TXT_RE = re.compile(r'\b(test series|login|subscribe|sign in|join now|advertisement|cookie|newsletter)\b', re.I)

def clean(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(NOISE_TAGS): t.decompose()
    for t in soup.find_all(attrs={"class": NOISE_CLS_RE}): t.decompose()
    for t in soup.find_all(attrs={"id": NOISE_CLS_RE}): t.decompose()
    return soup.get_text("\n", strip=True), soup

def validate(text, soup, min_words=300):
    words = text.split()
    if len(words) < min_words:
        return False, f"Too short: {len(words)} words (min {min_words})"
    for err in ("page not found","404 error","no content available"):
        if err in text[:400].lower(): return False, f"Error page: {err}"
    noise = len(NOISE_TXT_RE.findall(text))
    if noise / max(1,len(words)) > 0.30: return False, f"Noise ratio: {noise}/{len(words)}"
    paras = [p for p in soup.find_all("p") if len(p.get_text(strip=True).split()) > 10]
    heads = soup.find_all(["h1","h2","h3","h4"])
    if len(paras) < 3 and not (len(heads) >= 2 and len(paras) >= 1):
        return False, f"Structure: {len(paras)} paras, {len(heads)} heads"
    return True, "OK"

def save(data, fname):
    p = OUT / fname
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return p

def download_pdf(url, fname):
    p = OUT / fname
    try:
        r = SESSION.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(p,"wb") as f:
            for chunk in r.iter_content(1024*1024): f.write(chunk)
        kb = p.stat().st_size / 1024
        if kb < 500:
            log("FAIL","PDF",f"{fname}: {kb:.0f} KB < 500 KB"); p.unlink(); return None
        doc = fitz.open(p)
        if not doc[0].get_text().strip():
            log("FAIL","PDF",f"{fname}: first page unreadable"); doc.close(); p.unlink(); return None
        words = " ".join(pg.get_text() for pg in doc).split()
        doc.close()
        if len(words) < 5000:
            log("FAIL","PDF",f"{fname}: {len(words)} words < 5000"); p.unlink(); return None
        log("OK","PDF",f"{fname}  ({kb/1024:.1f} MB, {len(words):,} words)")
        return p
    except Exception as e:
        log("FAIL","PDF",f"{fname}: {e}")
        if p.exists(): p.unlink()
        return None

# ---------------------------------------------------------------------------
# 1. VISION IAS  (Playwright)
# ---------------------------------------------------------------------------
def demo_visionias():
    print("\n[1/7] VISION IAS - Monthly PDF (Playwright)")
    print("-"*55)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            pg = b.new_page()
            pg.goto("https://visionias.in/resources/monthly_magazine.php", timeout=60000, wait_until="networkidle")
            pg.wait_for_timeout(4000)
            links = pg.evaluate("""() =>
                Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({href: a.href, text:(a.innerText||'').toLowerCase().trim()}))
            """)
            html_dump = pg.content()
            b.close()

        found = []
        for item in links:
            href, text = item["href"], item["text"]
            if ".pdf" not in href.lower(): continue
            if any(x in text for x in ["pt365","mains365","hindi","test series"]): continue
            m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})',
                          text + " " + href.lower())
            if m: found.append((m.group(1), m.group(2), href))

        if found:
            month, year, url = found[0]
            log("INFO","VisionIAS",f"Found PDF link: {month} {year}")
            if download_pdf(url, f"VisionIAS_{month}_{year}_demo.pdf"):
                return

        # Fallback: save the rendered HTML for inspection
        dump_p = OUT / "VisionIAS_page_rendered.html"
        dump_p.write_text(html_dump, encoding="utf-8")
        log("INFO","VisionIAS",f"PDFs require login. Saved rendered HTML ({dump_p.stat().st_size//1024} KB) for inspection.")
        log("INFO","VisionIAS","Open VisionIAS_page_rendered.html in a browser to see what the scraper sees.")
    except Exception as e:
        log("FAIL","VisionIAS",f"Playwright error: {e}")

# ---------------------------------------------------------------------------
# 2. INSIGHTS IAS  (requests)
# ---------------------------------------------------------------------------
def demo_insightsias():
    print("\n[2/7] INSIGHTS IAS - Monthly PDF")
    print("-"*55)
    targets = ["january 2026", "december 2025", "march 2026", "february 2026"]
    try:
        html = SESSION.get("https://www.insightsonindia.com/current-affairs-downloads/", timeout=30).text
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            if "magazine" not in text: continue
            if any(x in text for x in ["quiz","secure","answer","writing","hindi"]): continue
            m = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s*(20\d{2})', text)
            if not m: continue
            label = f"{m.group(1)} {m.group(2)}"
            log("INFO","InsightsIAS",f"Checking: {label}")
            post = BeautifulSoup(SESSION.get(a["href"], timeout=30).text, "lxml")
            for lnk in post.find_all("a", href=True):
                href = lnk["href"]
                lt   = lnk.get_text(" ", strip=True).lower()
                if href.endswith(".pdf") and "combined" in lt:
                    fname = f"InsightsIAS_{m.group(1)}_{m.group(2)}_demo.pdf"
                    if download_pdf(href, fname): return
            time.sleep(0.3)
        log("FAIL","InsightsIAS","No combined monthly PDF found")
    except Exception as e:
        log("FAIL","InsightsIAS",f"Error: {e}")

# ---------------------------------------------------------------------------
# 3. FORUM IAS  (9PM Brief)
# ---------------------------------------------------------------------------
def demo_forumias():
    print("\n[3/7] FORUM IAS - 9PM Daily Brief")
    print("-"*55)
    base = "https://blog.forumias.com"
    try:
        soup = BeautifulSoup(SESSION.get(f"{base}/category/9-pm-brief/", timeout=30).text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "9-pm-brief" not in href or len(href) < 36: continue
            title = a.get_text(strip=True) or "ForumIAS 9PM Brief"
            if len(title) < 5: continue
            full = urljoin(base, href)
            log("INFO","ForumIAS",f"Fetching: {title[:60]}")
            text, s = clean(SESSION.get(full, timeout=30).text)
            ok, reason = validate(text, s)
            if not ok: log("WARN","ForumIAS",f"REJECT: {reason}"); continue
            p = save({"source":"ForumIAS","title":title,"date":datetime.now().isoformat(),"content":text},
                     "ForumIAS_9pm_brief_demo.json")
            log("OK","ForumIAS",f"Saved {p.stat().st_size//1024} KB -> {p.name}"); return
        log("FAIL","ForumIAS","No valid article found")
    except Exception as e:
        log("FAIL","ForumIAS",f"Error: {e}")

# ---------------------------------------------------------------------------
# 4. THE HINDU  (Paywall note + RSS metadata demo)
# ---------------------------------------------------------------------------
def demo_thehindu():
    print("\n[4/7] THE HINDU - Editorial (RSS metadata demo)")
    print("-"*55)
    log("INFO","The Hindu","NOTE: The Hindu has a hard paywall. Full article text requires subscription.")
    log("INFO","The Hindu","Saving richest available RSS metadata as the demo output.")
    feeds = [
        "https://www.thehindu.com/opinion/editorial/feeder/default.rss",
        "https://www.thehindu.com/opinion/feeder/default.rss",
    ]
    try:
        for rss_url in feeds:
            feed = feedparser.parse(rss_url)
            entries_with_summary = [e for e in feed.entries if len(e.get("summary","").split()) >= 50]
            if not entries_with_summary: continue
            entry  = entries_with_summary[0]
            summary = BeautifulSoup(entry.get("summary",""), "lxml").get_text(" ", strip=True)
            data = {
                "source":       "The Hindu",
                "title":        entry.title,
                "date":         entry.get("published", datetime.now().isoformat()),
                "url":          entry.link,
                "content":      summary,
                "note":         "Full article behind paywall. Content is from RSS feed summary.",
            }
            p = save(data, "TheHindu_article_demo.json")
            log("OK","The Hindu",f"Saved {p.stat().st_size//1024} KB -> {p.name}")
            log("OK","The Hindu",f"Title: {entry.title[:70]}")
            return
        log("FAIL","The Hindu","No RSS entries with sufficient summary found")
    except Exception as e:
        log("FAIL","The Hindu",f"Error: {e}")

# ---------------------------------------------------------------------------
# 5. INDIAN EXPRESS  (RSS)
# ---------------------------------------------------------------------------
def demo_indianexpress():
    print("\n[5/7] INDIAN EXPRESS - Daily Article")
    print("-"*55)
    try:
        feed = feedparser.parse("https://indianexpress.com/section/india/feed/")
        for entry in feed.entries:
            log("INFO","IndianExpress",f"Trying: {entry.title[:60]}")
            text, s = clean(SESSION.get(entry.link, timeout=30).text)
            ok, reason = validate(text, s)
            if not ok: log("WARN","IndianExpress",f"REJECT: {reason}"); continue
            p = save({"source":"Indian Express","title":entry.title,
                      "date":entry.get("published",datetime.now().isoformat()),"content":text},
                     "IndianExpress_article_demo.json")
            log("OK","IndianExpress",f"Saved {p.stat().st_size//1024} KB -> {p.name}"); return
        log("FAIL","IndianExpress","No valid article found")
    except Exception as e:
        log("FAIL","IndianExpress",f"Error: {e}")

# ---------------------------------------------------------------------------
# 6. PIB  (Press Release - min 150 words, relaxed for short PRs)
# ---------------------------------------------------------------------------
def demo_pib():
    print("\n[6/7] PIB - Press Release")
    print("-"*55)
    tried = set()
    try:
        soup = BeautifulSoup(SESSION.get("https://pib.gov.in/indexd.aspx", timeout=30).text, "lxml")
        for a in soup.find_all("a", href=True):
            if "PressReleasePage" not in a["href"]: continue
            full = urljoin("https://pib.gov.in/", a["href"])
            if full in tried: continue
            tried.add(full)
            title = a.get_text(strip=True) or "PIB Press Release"
            log("INFO","PIB",f"Fetching: {title[:60]}")
            text, s = clean(SESSION.get(full, timeout=30).text)
            words = text.split()
            if len(words) < 150:
                log("WARN","PIB",f"REJECT: {len(words)} words < 150"); continue
            if any(e in text[:300].lower() for e in ("page not found","404","no content available")):
                log("WARN","PIB","REJECT: error page"); continue
            p = save({"source":"PIB","title":title,"date":datetime.now().isoformat(),"content":text},
                     "PIB_press_release_demo.json")
            log("OK","PIB",f"Saved {p.stat().st_size//1024} KB -> {p.name}"); return
        log("FAIL","PIB","No valid press release found")
    except Exception as e:
        log("FAIL","PIB",f"Error: {e}")

# ---------------------------------------------------------------------------
# 7. DRISHTI IAS  (Daily Analysis)
# ---------------------------------------------------------------------------
def demo_drishtiias():
    print("\n[7/7] DRISHTI IAS - Daily Analysis")
    print("-"*55)
    base = "https://www.drishtiias.com"
    try:
        soup = BeautifulSoup(SESSION.get(f"{base}/current-affairs-news-analysis-editorials", timeout=30).text, "lxml")
        for a in soup.find_all("a", href=True):
            if "daily-updates" not in a["href"]: continue
            title = a.get_text(strip=True)
            if len(title) < 5: continue
            full = a["href"] if a["href"].startswith("http") else f"{base}{a['href']}"
            log("INFO","DrishtiIAS",f"Fetching: {title[:60]}")
            text, s = clean(SESSION.get(full, timeout=30).text)
            ok, reason = validate(text, s)
            if not ok: log("WARN","DrishtiIAS",f"REJECT: {reason}"); continue
            p = save({"source":"DrishtiIAS","title":title,"date":datetime.now().isoformat(),"content":text},
                     "DrishtiIAS_daily_analysis_demo.json")
            log("OK","DrishtiIAS",f"Saved {p.stat().st_size//1024} KB -> {p.name}"); return
        log("FAIL","DrishtiIAS","No valid article found")
    except Exception as e:
        log("FAIL","DrishtiIAS",f"Error: {e}")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "="*55)
    print("  UPSC SCRAPER - DEMO RUN (All 7 Sources)")
    print(f"  Output: {OUT}")
    print("="*55)

    t0 = time.time()
    demo_visionias()
    demo_insightsias()
    demo_forumias()
    demo_thehindu()
    demo_indianexpress()
    demo_pib()
    demo_drishtiias()

    elapsed = time.time() - t0
    files   = sorted(OUT.glob("*"))
    print("\n" + "="*55)
    print(f"  DONE in {elapsed:.0f}s  |  Files in folder: {len(files)}")
    print(f"  Location: {OUT}")
    for f in files:
        kb = f.stat().st_size / 1024
        print(f"    {f.name:<52}  {kb:>7.0f} KB")
    print("="*55)
