"""News zu einem Ticker abrufen, deduplizieren und nach Relevanz filtern (deterministisch, kein LLM).

Quellen (dieselbe Mischung für News-Agent und Sentiment-Testset):
    1. yfinance-News, ohne Bewertungs-Blogs und Aggregatoren (LOW_QUALITY_SOURCES)
    2. Tavily-Suche (topic=news) ausschliesslich auf englischsprachigen Qualitätsmedien
       (TRUSTED_DOMAINS); nur aktiv, wenn TAVILY_API_KEY gesetzt ist

Nur Englisch, weil FinBERT (V1) ein englisches Modell ist. Behalten werden nur Headlines,
die das Unternehmen selbst nennen (Name, Marke, ADR-Kürzel).
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import yfinance as yf

from graph.state import NewsItem

log = logging.getLogger(__name__)

# yfinance-Anbieter, deren Titel meist Bewertungs-Teaser, Transkripte oder Blog-Beiträge sind
LOW_QUALITY_SOURCES = {
    "Simply Wall St.", "Zacks", "GuruFocus.com", "Motley Fool", "MarketBeat", "Insider Monkey",
    "Stocktwits", "24/7 Wall St.", "Moby", "Trefis", "TipRanks", "Barchart", "TIKR",
    "InvestorsHub", "Yahoo Finance Video",
}

# Englischsprachige Qualitätsmedien für Tavily → angezeigter Quellenname
TRUSTED_DOMAINS: dict[str, str] = {
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "ft.com": "Financial Times",
    "wsj.com": "The Wall Street Journal",
    "cnbc.com": "CNBC",
    "marketwatch.com": "MarketWatch",
    "barrons.com": "Barron's",
    "apnews.com": "Associated Press",
    "investing.com": "Investing.com",
    "swissinfo.ch": "Swissinfo",
    "finews.com": "finews.com",
    "fiercepharma.com": "Fierce Pharma",
    "biopharmadive.com": "BioPharma Dive",
    "fooddive.com": "Food Dive",
    "just-food.com": "Just Food",
    "insurancejournal.com": "Insurance Journal",
    "artemis.bm": "Artemis",
    "constructiondive.com": "Construction Dive",
}

MIN_TITLE_WORDS = 4
TAVILY_QUERIES = ('"{name}" company news', '"{name}" shares earnings outlook')

# Zusätzliche Namen, unter denen ein Titel in Headlines auftaucht (Marken, ADR-Kürzel)
ALIASES: dict[str, list[str]] = {
    "ROG.SW": ["RHHBY"],
    "NOVN.SW": ["NVS"],
    "NESN.SW": ["Nestle", "NSRGY"],
    "CFR.SW": ["Cartier", "CFRUY"],
    "ZURN.SW": ["Zurich", "ZURVY"],
    "SREN.SW": ["SSREY", "SSREF"],
    "LONN.SW": ["LZAGY"],
    "GIVN.SW": ["GVDNY"],
    "HOLN.SW": ["HCMLY"],
    "SDZ.SW": ["SDZNY"],
    "SIKA.SW": ["SXYAY", "SKFOF"],
    "SLHN.SW": ["SWSDF"],
    "GEBN.SW": ["GBERY", "GBERF"],
}

# Meldungen, in denen der Titel nur als Absender einer Analyse über Drittfirmen auftritt
EXCLUDE: dict[str, str] = {
    "UBSG.SW": (r"\bUBS (says|warns|sees|cuts|lifts|raises|upgrades|downgrades|initiates|turns|flags|assesses"
                r"|outlines|stays|expects|recommends|names|picks|trims)\b|\b(says|as|after) UBS\b"),
}

# Suchbegriff für Tavily, falls der Name allein mehrdeutig ist
SEARCH_NAMES: dict[str, str] = {
    "ZURN.SW": "Zurich Insurance Group",
    "SREN.SW": "Swiss Re",
    "SLHN.SW": "Swiss Life Holding",
    "CFR.SW": "Richemont",
    "PGHN.SW": "Partners Group",
}

_TITLE_SUFFIX = re.compile(r"\s+[|\-–—]\s+(" + "|".join(re.escape(n) for n in TRUSTED_DOMAINS.values())
                           + r"|Reuters|Bloomberg|FT|WSJ)\s*$", re.IGNORECASE)


_SOURCE_TAIL = re.compile(r"\s+(By Investing\.com|[-|–]\s+[\w.-]+\.(com|bm|ch|co\.uk))\s*$", re.IGNORECASE)
_NOT_A_HEADLINE = re.compile(r"stock price|latest news|stock quote|share price & news", re.IGNORECASE)


def clean_title(title: str) -> str:
    """Entfernt Quellen-Anhängsel und Kürzungszeichen; '' wenn es keine Meldung ist (z. B. Kursseite)."""
    title = (title or "").strip()
    for _ in range(2):   # Anhängsel können kombiniert vorkommen («… - Bloomberg - reuters.com»)
        title = _SOURCE_TAIL.sub("", title)
        title = _TITLE_SUFFIX.sub("", title)
    title = re.sub(r"\s*(\.\.\.|…)$", "", title).strip()
    if _NOT_A_HEADLINE.search(title) or len(title.split()) < MIN_TITLE_WORDS:
        return ""
    return title


def is_duplicate(key: str, seen: set[str]) -> bool:
    """Gleicher Titel oder gekürzte Fassung eines bereits gesehenen Titels (und umgekehrt)."""
    return key in seen or any(len(key) >= 30 and (s.startswith(key) or key.startswith(s)) for s in seen)


def _plain(text: str) -> str:
    """Kleinbuchstaben ohne Akzente (Nestlé → nestle)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def normalize_title(title: str) -> str:
    """Schlüssel für die Duplikaterkennung."""
    return re.sub(r"\W+", " ", _plain(title)).strip()


def is_relevant(title: str, ticker: str, company: str) -> bool:
    """True, wenn die Headline das Unternehmen selbst nennt."""
    root = ticker.split(".")[0]
    names = [company, f"SWX:{root}", f"VTX:{root}", *ALIASES.get(ticker, [])]
    plain = _plain(title)
    if not any(re.search(rf"\b{re.escape(_plain(n))}\b", plain) for n in names):
        return False
    pattern = EXCLUDE.get(ticker)
    return not (pattern and re.search(pattern, title, flags=re.IGNORECASE))


def to_iso_date(value: str | None) -> str:
    """'2026-11-24T15:00:00Z' oder 'Mon, 24 Nov 2026 15:00:00 GMT' → '2026-11-24'; sonst ''."""
    if not value:
        return ""
    value = value.strip()
    if re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _item(title: str, source: str, published: str, url: str) -> NewsItem:
    return {"title": title, "source": source, "published": published, "url": url, "sentiment": None}


def fetch_yfinance(ticker: str, limit: int = 60) -> list[NewsItem]:
    """yfinance-News ohne LOW_QUALITY_SOURCES."""
    t = yf.Ticker(ticker)
    try:
        raw = t.get_news(count=limit)
    except (AttributeError, TypeError):
        raw = t.news
    items: list[NewsItem] = []
    for entry in raw or []:
        c = entry.get("content", entry)
        title = clean_title(c.get("title"))
        source = (c.get("provider") or {}).get("displayName", "")
        if not title or source in LOW_QUALITY_SOURCES:
            continue
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url") or ""
        items.append(_item(title, source, to_iso_date(c.get("pubDate")), url))
    return items


def fetch_tavily(ticker: str, company: str, lookback_days: int = 90, max_results: int = 20) -> list[NewsItem]:
    """Tavily-News von TRUSTED_DOMAINS. Ohne TAVILY_API_KEY: leere Liste."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        log.warning("TAVILY_API_KEY fehlt, Tavily wird übersprungen")
        return []
    from tavily import TavilyClient

    name = SEARCH_NAMES.get(ticker, company)
    client = TavilyClient(api_key=api_key)
    results: list[dict] = []
    for query in TAVILY_QUERIES:   # zwei Formulierungen: allgemeine Meldungen + Kurs/Ergebnisse
        response = client.search(
            query=query.format(name=name),
            topic="news",
            start_date=(date.today() - timedelta(days=lookback_days)).isoformat(),
            max_results=max_results,
            include_domains=list(TRUSTED_DOMAINS),
        )
        results.extend(response.get("results", []))
    items: list[NewsItem] = []
    for r in results:
        url = r.get("url", "")
        host = urlparse(url).netloc.lower().removeprefix("www.")
        domain = next((d for d in TRUSTED_DOMAINS if host == d or host.endswith("." + d)), None)
        if domain is None or (domain == "swissinfo.ch" and "/eng/" not in url):
            continue   # nur Whitelist, Swissinfo nur englische Ausgabe
        title = clean_title(r.get("title"))
        if title:
            items.append(_item(title, TRUSTED_DOMAINS[domain], to_iso_date(r.get("published_date")), url))
    return items


def fetch_news(ticker: str, company: str, lookback_days: int = 90, max_items: int = 20) -> list[NewsItem]:
    """Holt News aus yfinance und Tavily, entfernt Duplikate und Meldungen ohne Bezug zum Unternehmen.

    Ergebnis nach Datum absteigend sortiert; Meldungen ohne Datum zuletzt.
    """
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    seen: set[str] = set()
    items: list[NewsItem] = []
    for item in fetch_yfinance(ticker) + fetch_tavily(ticker, company, lookback_days):
        key = normalize_title(item["title"])
        if is_duplicate(key, seen) or not is_relevant(item["title"], ticker, company):
            continue
        if item["published"] and item["published"] < cutoff:
            continue
        seen.add(key)
        items.append(item)
    items.sort(key=lambda i: i["published"] or "", reverse=True)
    return items[:max_items]
