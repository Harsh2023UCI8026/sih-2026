# src/scrape_flood_reports.py
"""scrape_flood_reports.py

This script searches for news articles about flood/water‑logging in the Dwarka or Najafgarh areas of Delhi.
It uses a Google "site:"‑restricted search to locate historic articles on three major Indian news sites, fetches each article, extracts location mentions, depth estimates, and geocodes the location via OpenStreetMap Nominatim (respecting the 1 req/sec limit).

The resulting CSV contains the following columns:
    report_id, title, url, date, latitude, longitude, confidence_tier, depth_estimate_cm, depth_confidence

The script is deliberately self‑contained and only requires the standard library plus optional ``spaCy`` (fallback to regex if unavailable).
"""

import csv
import json
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Optional spaCy import – if not available we fall back to a simple regex.
# ---------------------------------------------------------------------------
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    _HAS_SPACY = True
except Exception:
    _HAS_SPACY = False
print(f"[Info] spaCy available: {_HAS_SPACY}")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

# Nominatim endpoint – 1 request per second required.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Output CSV path
OUTPUT_CSV = Path(__file__).with_name("dwarka_flood_reports.csv")

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def google_site_search(domain: str, keywords: List[str]) -> List[str]:
    """Perform a Google site‑restricted search as a fallback.

    Args:
        domain: e.g. "timesofindia.indiatimes.com"
        keywords: list of keyword strings – each will be OR‑combined inside the query.

    Returns:
        List of article URLs (deduplicated)."""
    query = f"site:{domain} " + " OR ".join(keywords)
    url = "https://www.google.com/search"
    params = {"q": query, "hl": "en"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Google Search] failed for {domain}: {e}")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    for a in soup.select('a'):
        href = a.get('href')
        if not href:
            continue
        # Google wraps real URL as /url?q=<actual>&...
        m = re.search(r"/url\?q=(https?://[^&]+)", href)
        if m:
            links.append(m.group(1))
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for l in links:
        if l not in seen:
            seen.add(l)
            uniq.append(l)
    return uniq

# Site‑specific search fallbacks

def search_timesofindia(keywords: List[str]) -> List[str]:
    """Search Times of India using its internal search endpoint.
    Returns a list of article URLs.
    """
    base = "https://timesofindia.indiatimes.com/searchpage.cms"
    urls = []
    for kw in keywords:
        params = {"searchKeyword": kw}
        try:
            resp = requests.get(base, headers=HEADERS, params=params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[TimesofIndia Search] {kw} – {e}")
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select('a[href]'):
            href = a['href']
            if href.startswith('/'):
                full = f"https://timesofindia.indiatimes.com{href}"
                urls.append(full)
    # Deduplicate
    return list(dict.fromkeys(urls))

def search_hindustantimes(keywords: List[str]) -> List[str]:
    """Search Hindustan Times using its internal search endpoint.
    Returns a list of article URLs.
    """
    base = "https://www.hindustantimes.com/search"
    urls = []
    for kw in keywords:
        params = {"q": kw}
        try:
            resp = requests.get(base, headers=HEADERS, params=params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[HindustanTimes Search] {kw} – {e}")
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select('a[href]'):
            href = a['href']
            if href.startswith('https://'):
                urls.append(href)
            elif href.startswith('/'):
                urls.append(f"https://www.hindustantimes.com{href}")
    return list(dict.fromkeys(urls))

def search_ndtv(keywords: List[str]) -> List[str]:
    """Search NDTV using its internal search endpoint.
    Returns a list of article URLs.
    """
    base = "https://www.ndtv.com/search"
    urls = []
    for kw in keywords:
        params = {"searchtext": kw}
        try:
            resp = requests.get(base, headers=HEADERS, params=params, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[NDTV Search] {kw} – {e}")
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select('a[href]'):
            href = a['href']
            if href.startswith('http'):
                urls.append(href)
            elif href.startswith('/'):
                urls.append(f"https://www.ndtv.com{href}")
    return list(dict.fromkeys(urls))

def fetch_article(url: str) -> Optional[Dict[str, str]]:
    """Download an article and return a dict with title, date, and text.
    The function attempts a very generic extraction – many sites have different structures.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[Fetch] {url} -> {e}")
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    # Title
    title_tag = soup.find(['h1', 'title'])
    title = title_tag.get_text(strip=True) if title_tag else ""
    # Date – try meta tags first
    date = ""
    for meta in soup.find_all('meta'):
        if meta.get('property') in ['article:published_time', 'og:published_time']:
            date = meta.get('content', "")
            break
    if not date:
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            date = time_tag['datetime']
    # Text – concatenate paragraph texts
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all('p')]
    text = " ".join(paragraphs)
    return {"title": title, "date": date, "text": text}

def extract_locations(text: str) -> List[str]:
    """Return a list of location strings found in the text.
    Prefer spaCy NER (GPE/LOC) but fall back to a simple regex for capitalised words.
    """
    locations = []
    # Debug: indicate which extraction method is being used
    if _HAS_SPACY:
        print("[Info] Using spaCy for location extraction")
    else:
        print("[Info] Using regex fallback for location extraction")
    if _HAS_SPACY:
        doc = _nlp(text)
        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC", "FAC"}:
                locations.append(ent.text)
    else:
        # Very naive regex: consecutive capitalised words (including Delhi)
        matches = re.findall(r"([A-Z][a-z]+(?:[\s-][A-Z][a-z]+)*)", text)
        for m in matches:
            if len(m.split()) <= 6:
                locations.append(m)
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for loc in locations:
        if loc not in seen:
            seen.add(loc)
            uniq.append(loc)
    return uniq

def geocode_location(location: str) -> Optional[Dict[str, float]]:
    """Geocode a location string via Nominatim.
    Returns dict with latitude and longitude or None on failure.
    """
    params = {
        "q": f"{location}, Delhi, India",
        "format": "json",
        "limit": 1,
        "viewbox": "76.8,28.9,77.4,28.4",
        "bounded": 1,
    }
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        return {"latitude": float(data[0]["lat"]), "longitude": float(data[0]["lon"])}
    except Exception as e:
        print(f"[Geocode] {location} -> {e}")
        return None
    finally:
        time.sleep(1)  # respect 1 req/sec

DEPTH_PATTERNS = [
    (re.compile(r"(knee[-\s]?deep)\s*(?:≈|~|about)?\s*(\d{1,3})\s*cm", re.I), "knee-deep"),
    (re.compile(r"(ankle[-\s]?deep)\s*(?:≈|~|about)?\s*(\d{1,3})\s*cm", re.I), "ankle-deep"),
    (re.compile(r"(waist[-\s]?deep)\s*(?:≈|~|about)?\s*(\d{1,3})\s*cm", re.I), "waist-deep"),
]

def extract_depth(text: str) -> (Optional[int], str):
    """Search for explicit depth statements.
    Returns (depth_cm or None, confidence) where confidence is "explicit" if a pattern matches,
    otherwise "none".
    """
    for pattern, _ in DEPTH_PATTERNS:
        m = pattern.search(text)
        if m:
            depth = int(m.group(2))
            return depth, "explicit"
    return None, "none"

def assign_confidence_tier(location: Optional[Dict[str, float]], depth_confidence: str) -> str:
    """Determine overall confidence tier.
    High – both location and explicit depth are present.
    Medium – location present but depth not explicit.
    Low – location missing.
    """
    if location and depth_confidence == "explicit":
        return "high"
    if location:
        return "medium"
    return "low"

# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------
def main():
    # Seed URLs selected for crawling. Their reported events and any depth
    # figures are not independently verified by this scraper.
    SEED_URLS = [
        "https://www.tribuneindia.com/news/delhi/pre-monsoon-showers-expose-capitals-chronic-drainage-woes",
        "https://test.uniindia.com/delhi-govt-accelerates-measures-to-prevent-monsoon-flooding-zakhira-underpass-to-remain-water-logging-free-verma/india/news/3867085.html",
        "https://lg.delhi.gov.in/node/9244",
        "https://www.deccanherald.com/national/traffic-snarls-waterlogging-as-monsoon-hits-delhi-1122636.html",
    ]
    article_urls = SEED_URLS
    # No deduplication needed for seed URLs; proceed directly

    records = []
    for url in article_urls:
        article = fetch_article(url)
        if not article:
            continue
        text = article["text"]
        # Filter: ensure article mentions Dwarka or Najafgarh with proper context
        if re.search(r"\bNajafgarh\b", text, re.I):
            pass  # Najafgarh is unambiguous
        elif re.search(r"\bDwarka\b", text, re.I) and re.search(r"\b(Delhi|Dwarka Sector|Dwarka Expressway|IGI Airport)\b", text, re.I):
            pass  # Dwarka with additional context
        else:
            continue
        locations = extract_locations(text)
        target_loc = None
        for loc in locations:
            if re.search(r"\b(Dwarka|Najafgarh)\b", loc, re.I):
                target_loc = loc
                # Debug: print the location string being geocoded
                print(f"[Debug] Geocoding target location: {target_loc}")
                break
        geocode = geocode_location(target_loc) if target_loc else None
        # Sanity check: ensure coordinates fall within Delhi NCR bounding box
        geocode_suspect = False
        if geocode:
            lat = geocode.get("latitude")
            lon = geocode.get("longitude")
            if not (28.4 <= lat <= 28.9 and 76.8 <= lon <= 77.4):
                geocode_suspect = True
                print(f"[Warning] Geocode suspect for '{target_loc}': ({lat}, {lon}) outside Delhi NCR bounds")
            # Debug: print successful geocode result
            print(f"[Result] Geocoded '{target_loc}' -> ({lat}, {lon})")
        else:
            print(f"[Result] No geocode for '{target_loc}'")
        depth_cm, depth_conf = extract_depth(text)
        confidence_tier = assign_confidence_tier(geocode, depth_conf)
        record = {
            "report_id": str(uuid.uuid4()),
            "title": article["title"],
            "url": url,
            "date": article["date"],
            "latitude": geocode["latitude"] if geocode else "",
            "longitude": geocode["longitude"] if geocode else "",
            "confidence_tier": confidence_tier,
            "depth_estimate_cm": depth_cm if depth_cm is not None else "",
            "depth_confidence": depth_conf,
            "geocode_suspect": geocode_suspect,
        }
        records.append(record)

    fieldnames = [
        "report_id",
        "title",
        "url",
        "date",
        "latitude",
        "longitude",
        "confidence_tier",
        "depth_estimate_cm",
        "depth_confidence",
        "geocode_suspect",
    ]

    low_confidence = [r for r in records if r["confidence_tier"] == "low"]
    if low_confidence:
        low_path = OUTPUT_CSV.with_name("dwarka_flood_reports_low_confidence.csv")
        with open(low_path, "w", newline="", encoding="utf-8") as lf:
            low_writer = csv.DictWriter(lf, fieldnames=fieldnames)
            low_writer.writeheader()
            for r in low_confidence:
                low_writer.writerow(r)
            print(f"[Info] {len(low_confidence)} low-confidence records written to {low_path}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    print(f"[Done] {len(records)} records written to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
