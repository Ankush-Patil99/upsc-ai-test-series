"""
ca_scraper.py — Autonomous Current Affairs Scraper
===================================================
Scrapes UPSC Current Affairs from 7 sources (PDFs and News HTML).
Intervals supported: Monthly (Vision, Insights), Daily (Forum, Hindu, IE), 5-Days (PIB, Drishti).
"""

import argparse
import hashlib
import logging
import os
import re
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import feedparser
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# -- Config ------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
os.environ["HF_HOME"] = str(BASE_DIR / "models")
os.environ["HF_HUB_OFFLINE"] = "0"  # Allow downloading if model not found

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(BASE_DIR / "logs" / "ca_scraper.log"), mode="a", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ca_scraper")

from src.config import CHROMA_PERSIST_DIR, CHROMA_RAG_COLLECTION, RAG_EMBED_MODEL

CA_PDF_DIR = BASE_DIR / "pipeline_data" / "ca_pdfs"
CA_PDF_DIR.mkdir(parents=True, exist_ok=True)

CA_REQUEST_TIMEOUT = 30

# -----------------------------------------------------------------------------
# Network & DB Utils
# -----------------------------------------------------------------------------

def _get_session():
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    return s

_session = _get_session()
_chroma_lock = threading.Lock()
_collection = None

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        from sentence_transformers import SentenceTransformer
        class EF:
            def __init__(self):
                self.m = SentenceTransformer(RAG_EMBED_MODEL)
            def name(self): return RAG_EMBED_MODEL
            def __call__(self, input): return self.m.encode(input, normalize_embeddings=True).tolist()
        _collection = client.get_or_create_collection(name=CHROMA_RAG_COLLECTION, embedding_function=EF())
    return _collection

# -----------------------------------------------------------------------------
# Core Logic
# -----------------------------------------------------------------------------

def _download_pdf(url: str, filename: str) -> Optional[bytes]:
    try:
        filepath = CA_PDF_DIR / filename
        if filepath.exists():
            with open(filepath, "rb") as f:
                return f.read()
                
        resp = _session.get(url, stream=True, timeout=CA_REQUEST_TIMEOUT)
        resp.raise_for_status()
        
        pdf_bytes = bytearray()
        for data in resp.iter_content(1024 * 1024):
            pdf_bytes.extend(data)
            
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        return bytes(pdf_bytes)
    except Exception as e:
        logger.error(f"  [Error] PDF Download failed for {filename}: {e}")
        return None

def _extract_pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n\n".join(page.get_text() for page in doc).strip()

def _extract_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "lxml")
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.extract()
    return soup.get_text(separator="\n", strip=True)

def _upsert_chunks(chunks, source, url, title, pdf_name="", gs="GS2"):
    if not chunks:
        return 0
    coll = _get_collection()
    
    ids, docs, metadatas = [], [], []
    seen = set()
    for text in chunks:
        fp = hashlib.sha256(text.encode()).hexdigest()[:16]
        cid = f"CA_{source}_{fp}"
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)
            docs.append(text)
            metadatas.append({
                "source": source, "url": url, "article_title": title, 
                "pdf_local": pdf_name, "gs_paper": gs, "source_type": "CA",
                "ingested_at": datetime.now(timezone.utc).isoformat()
            })
        
    with _chroma_lock:
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            coll.upsert(
                ids=ids[i:i+batch_size],
                documents=docs[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )
    return len(ids)

# -----------------------------------------------------------------------------
# Scrapers
# -----------------------------------------------------------------------------

def scrape_visionias():
    logger.info("-- [1/7] VisionIAS (Monthly PDFs) --")
    url = "https://visionias.in/resources/monthly_magazine.php"
    total = 0
    try:
        soup = BeautifulSoup(_session.get(url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
        links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True) if ".pdf" in a["href"].lower()]
        for link in list(dict.fromkeys(links))[:5]: # Last 5 months for demo (expand to 18 later)
            fname = f"Vision_{hashlib.md5(link.encode()).hexdigest()[:8]}.pdf"
            data = _download_pdf(link, fname)
            if data:
                text = _extract_pdf_text(data)
                chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
                total += _upsert_chunks(chunks, "VisionIAS", link, "Vision Monthly", fname)
    except Exception as e: logger.error(f"Vision error: {e}")
    return total

def scrape_insightsias():
    logger.info("-- [2/7] InsightsIAS (Monthly PDFs) --")
    url = "https://www.insightsonindia.com/current-affairs/"
    total = 0
    try:
        soup = BeautifulSoup(_session.get(url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
        for a in soup.find_all("a", href=True):
            if "magazine" in a.get_text().lower() and "202" in a.get_text():
                post_url = a["href"]
                post_soup = BeautifulSoup(_session.get(post_url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
                for link in post_soup.find_all("a", href=True):
                    if link["href"].endswith(".pdf") and "combined" in link.get_text().lower():
                        pdf_url = link["href"]
                        fname = f"Insights_{pdf_url.split('/')[-1]}"
                        data = _download_pdf(pdf_url, fname)
                        if data:
                            text = _extract_pdf_text(data)
                            chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
                            total += _upsert_chunks(chunks, "InsightsIAS", pdf_url, a.get_text(), fname)
                        break
    except Exception as e: logger.error(f"Insights error: {e}")
    return total

def scrape_forumias():
    logger.info("-- [3/7] ForumIAS (Daily 9PM Brief HTML) --")
    url = "https://blog.forumias.com/category/9-pm-brief/"
    total = 0
    try:
        soup = BeautifulSoup(_session.get(url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
        for a in soup.find_all("a", href=True):
            if "9-pm-brief" in a.get_text().lower() or "9 pm brief" in a.get_text().lower():
                post_url = a["href"]
                html = _session.get(post_url, timeout=CA_REQUEST_TIMEOUT).text
                text = _extract_html_text(html)
                chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
                total += _upsert_chunks(chunks, "ForumIAS", post_url, a.get_text())
    except Exception as e: logger.error(f"Forum error: {e}")
    return total

def scrape_thehindu():
    logger.info("-- [4/7] The Hindu (Daily RSS/News) --")
    url = "https://www.thehindu.com/news/national/feeder/default.rss"
    total = 0
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            html = _session.get(entry.link, timeout=CA_REQUEST_TIMEOUT).text
            text = _extract_html_text(html)
            chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
            total += _upsert_chunks(chunks, "The Hindu", entry.link, entry.title)
    except Exception as e: logger.error(f"The Hindu error: {e}")
    return total

def scrape_indianexpress():
    logger.info("-- [5/7] Indian Express (Daily RSS/News) --")
    url = "https://indianexpress.com/section/india/feed/"
    total = 0
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            html = _session.get(entry.link, timeout=CA_REQUEST_TIMEOUT).text
            text = _extract_html_text(html)
            chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
            total += _upsert_chunks(chunks, "Indian Express", entry.link, entry.title)
    except Exception as e: logger.error(f"IE error: {e}")
    return total

def scrape_pib():
    logger.info("-- [6/7] PIB (5-Day PRs) --")
    url = "https://pib.gov.in/indexd.aspx"
    total = 0
    try:
        soup = BeautifulSoup(_session.get(url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
        links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True) if "PressReleasePage" in a["href"]]
        for link in list(dict.fromkeys(links))[:5]:
            html = _session.get(link, timeout=CA_REQUEST_TIMEOUT).text
            text = _extract_html_text(html)
            title = soup.title.string if soup.title else "PIB Release"
            chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
            total += _upsert_chunks(chunks, "PIB", link, title)
    except Exception as e: logger.error(f"PIB error: {e}")
    return total

def scrape_drishtiias():
    logger.info("-- [7/7] Drishti IAS (5-Day Analysis) --")
    url = "https://www.drishtiias.com/current-affairs-news-analysis-editorials"
    total = 0
    try:
        soup = BeautifulSoup(_session.get(url, timeout=CA_REQUEST_TIMEOUT).text, "lxml")
        links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True) if "daily-updates" in a["href"]]
        for link in list(dict.fromkeys(links))[:5]:
            html = _session.get(link, timeout=CA_REQUEST_TIMEOUT).text
            text = _extract_html_text(html)
            title = "Drishti IAS Update"
            chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80).split_text(text)
            total += _upsert_chunks(chunks, "DrishtiIAS", link, title)
    except Exception as e: logger.error(f"Drishti error: {e}")
    return total

SOURCE_MAP = {
    "visionias":     scrape_visionias,
    "insightsias":   scrape_insightsias,
    "forumias":      scrape_forumias,
    "thehindu":      scrape_thehindu,
    "indianexpress": scrape_indianexpress,
    "pib":           scrape_pib,
    "drishtiias":    scrape_drishtiias,
}

def run_all_scrapers(sources=None):
    summary = {"total_chunks_ingested": 0}
    sources_to_run = sources if sources else list(SOURCE_MAP.keys())
    for name in sources_to_run:
        if name in SOURCE_MAP:
            chunks = SOURCE_MAP[name]()
            summary[name] = chunks
            summary["total_chunks_ingested"] += chunks
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        try:
            print(f"Total CA chunks: {_get_collection().count()}")
        except Exception as e:
            print(f"ChromaDB not initialized or error: {e}")
        return

    if args.run_now:
        summary = run_all_scrapers()
        print(f"Scraping complete. Summary: {summary}")

if __name__ == "__main__":
    main()
