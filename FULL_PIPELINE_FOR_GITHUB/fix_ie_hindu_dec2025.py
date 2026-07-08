"""
fix_ie_hindu_dec2025.py
Fixes Indian Express and The Hindu for December 2025.
"""
import re, json, time, logging
import requests, feedparser
from pathlib import Path
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

OUT = Path(r"D:\upsc test series\data\Scrapper test")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-5s | %(message)s")
log = logging.getLogger("fix_dec")

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
    return True, "ok"

def save_json(data, fname):
    p = OUT / fname
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    arts = data.get("articles", [])
    wc   = sum(len(a.get("content","").split()) for a in arts)
    log.info(f"SAVED {fname}  ({p.stat().st_size//1024} KB, ~{wc:,} words, {len(arts)} articles)")

# ── INDIAN EXPRESS ────────────────────────────────────────
def scrape_ie():
    log.info("=== INDIAN EXPRESS — December 2025 ===")
    results = []
    try:
        # Try multiple sitemap approaches for IE
        urls = []

        # Approach 1: news sitemap with date range
        for day in range(1, 32, 5):  # Sample every 5 days
            sm_url = f"https://indianexpress.com/sitemap.xml?yyyy=2025&mm=12&dd={day:02d}"
            r = S.get(sm_url, timeout=20)
            found = re.findall(r"<loc>(https://indianexpress\.com/article/[^<]+)</loc>", r.text)
            urls.extend(found)

        # Approach 2: search page
        for query in ["current affairs december 2025", "india news december 2025"]:
            search_url = f"https://indianexpress.com/search/{query.replace(' ', '-')}/"
            r = S.get(search_url, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=re.compile(r"indianexpress\.com/article/")):
                urls.append(a["href"])

        # Approach 3: UPSC/current-affairs section with date filtering
        for page_n in range(1, 4):
            cat_url = f"https://indianexpress.com/section/india/page/{page_n}/"
            r = S.get(cat_url, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=re.compile(r"/article/")):
                href = a.get("href","")
                if "indianexpress.com" not in href:
                    href = "https://indianexpress.com" + href
                urls.append(href)

        urls = list(dict.fromkeys(u for u in urls if u.startswith("http")))
        log.info(f"  IE: {len(urls)} candidate URLs")

        for url in urls[:50]:
            if len(results) >= 5: break
            try:
                r    = S.get(url, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                # Check published date
                date_meta = (soup.find("meta", {"property": "article:published_time"}) or
                             soup.find("meta", {"itemprop": "datePublished"}))
                date_str = date_meta.get("content","") if date_meta else ""
                # Must be December 2025
                if date_str and "2025-12" not in date_str and "December" not in date_str:
                    continue
                if not date_str:
                    # Check in page text
                    pub = soup.find(attrs={"class": re.compile(r"date|publish|time", re.I)})
                    if pub:
                        pub_text = pub.get_text(strip=True)
                        if "December" not in pub_text and "Dec" not in pub_text:
                            continue
                    else:
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
                ok, _ = validate(text)
                if not ok: continue
                title_tag = soup.find("h1")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2]
                results.append({"url": url, "title": title, "date": date_str, "content": text})
                log.info(f"  IE OK: {title[:65]}")
                time.sleep(0.3)
            except Exception as e:
                pass

        if results:
            save_json({"source":"IndianExpress","month":"December 2025","articles":results},
                      "dec2025_indian_express.json")
        else:
            log.error("  IE: still no December 2025 articles — trying RSS fallback...")
            # RSS fallback (may not have Dec 2025 but try)
            feed = feedparser.parse("https://indianexpress.com/feed/")
            for entry in feed.entries:
                pub = entry.get("published","")
                if "Dec" not in pub and "December" not in pub: continue
                if "2025" not in pub: continue
                r    = S.get(entry.link, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                article = soup.find("div", class_=re.compile(r"full-details|article-body", re.I)) or soup.find("article")
                if not article: continue
                strip_noise(article)
                text = article.get_text("\n", strip=True)
                ok, _ = validate(text)
                if not ok: continue
                title = soup.find("h1")
                results.append({"url": entry.link, "title": title.get_text(strip=True) if title else "", "date": pub, "content": text})
                log.info(f"  IE RSS OK: {entry.title[:65]}")
                if len(results) >= 3: break
            if results:
                save_json({"source":"IndianExpress","month":"December 2025","articles":results},
                          "dec2025_indian_express.json")
    except Exception as e:
        log.error(f"IE error: {e}")

# ── THE HINDU ─────────────────────────────────────────────
def scrape_hindu():
    log.info("=== THE HINDU — December 2025 Editorials ===")
    results = []
    try:
        # The Hindu's archive URL format
        archive_urls = [
            "https://www.thehindu.com/opinion/editorial/?date=december-2025",
            "https://www.thehindu.com/archive/print/2025/12/01/",
            "https://www.thehindu.com/archive/web/2025/12/01/",
        ]

        editorial_links = []
        for arch_url in archive_urls:
            r = S.get(arch_url, timeout=20)
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/opinion/editorial/" in href and "2025" in href:
                    if not href.startswith("http"):
                        href = "https://www.thehindu.com" + href
                    editorial_links.append(href)

        # Try December 2025 archive days
        if not editorial_links:
            for day in range(1, 32):
                for section in ["opinion/editorial", "opinion/lead"]:
                    archive = f"https://www.thehindu.com/archive/web/2025/12/{day:02d}/"
                    try:
                        r = S.get(archive, timeout=10)
                        if r.status_code != 200: continue
                        soup = BeautifulSoup(r.text, "lxml")
                        for a in soup.find_all("a", href=True):
                            if section in a["href"]:
                                href = a["href"]
                                if not href.startswith("http"): href = "https://www.thehindu.com" + href
                                editorial_links.append(href)
                    except: pass

        editorial_links = list(dict.fromkeys(editorial_links))
        log.info(f"  Hindu: {len(editorial_links)} editorial links found")

        for url in editorial_links[:15]:
            if len(results) >= 5: break
            try:
                amp_url = url.rstrip("/") + "?amp=true"
                r = S.get(amp_url, timeout=15)
                soup = BeautifulSoup(r.text, "lxml")
                paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")
                         if len(p.get_text(strip=True).split()) > 5]
                text = "\n\n".join(paras)
                for phrase in ["Sign in","Subscribe","Related stories"]:
                    cut = text.find(phrase)
                    if 0 < cut: text = text[:cut]; break
                if re.search(r"\bsign in\b|\bsubscribe\b", text[:300], re.I): continue
                ok, _ = validate(text)
                if not ok: continue
                title_tag = soup.find("h1") or soup.find("h2")
                title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2].replace("-"," ").title()
                results.append({"url": url, "title": title, "content": text})
                log.info(f"  Hindu OK: {title[:65]}")
                time.sleep(0.3)
            except Exception as e:
                pass

        if results:
            save_json({"source":"TheHindu","month":"December 2025","articles":results},
                      "dec2025_the_hindu.json")
        else:
            log.error("  Hindu: December 2025 editorials not accessible (paywall/archive limitation)")
            # Create a note file explaining the limitation
            note = {
                "source": "TheHindu",
                "month": "December 2025",
                "note": "The Hindu editorials older than ~30 days require a paid subscription. Content not extractable.",
                "archive_url": "https://www.thehindu.com/archive/web/2025/12/",
                "articles": []
            }
            save_json(note, "dec2025_the_hindu.json")
    except Exception as e:
        log.error(f"Hindu error: {e}")

if __name__ == "__main__":
    scrape_ie()
    scrape_hindu()

    # Final status
    files = sorted(f for f in OUT.glob("dec2025_*.json") if f.stat().st_size > 1000)
    print()
    print("=" * 60)
    for f in sorted(OUT.glob("dec2025_*")):
        kb = f.stat().st_size // 1024
        print(f"  {'✅' if kb > 5 else '⚠️ '} {f.name:<42} {kb:>7,} KB")
    print("=" * 60)
