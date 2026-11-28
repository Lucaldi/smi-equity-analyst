"""Sammelt Headlines zu allen SMI-Titeln als Rohmaterial für das Sentiment-Testset (H2).

Nutzt dieselbe Funktion wie der News-Agent (tools.news_fetcher.fetch_news): yfinance ohne
Bewertungs-Blogs plus Tavily auf englischsprachigen Qualitätsmedien, Relevanzfilter und
Duplikaterkennung. Damit entspricht das Testset dem, was der Agent im Betrieb sieht.

Pro Titel höchstens `--per-ticker` Headlines (ausgewogen über den SMI); Duplikate auch über
Titel hinweg entfernt. Die Spalte `label` bleibt leer; gelabelt wird separat
(siehe nlp/LABELING.md), nie mit einem der verglichenen Modelle (FinBERT, OpenAI).

Aufruf:
    python -m nlp.collect_headlines [--per-ticker 8] [--lookback-days 365] [--force]
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from main import load_tickers
from tools.news_fetcher import fetch_news, is_duplicate, normalize_title

OUT_CSV = Path("nlp/label_smi_headlines.csv")
FIELDS = ["text", "ticker", "date", "source", "url", "label"]


def main() -> None:
    parser = argparse.ArgumentParser(description="SMI-Headlines für das Labeling sammeln")
    parser.add_argument("--per-ticker", type=int, default=8)
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--force", action="store_true", help="bestehende Datei überschreiben")
    args = parser.parse_args()
    load_dotenv(Path(".env"))
    if not os.getenv("TAVILY_API_KEY"):
        print("Hinweis: TAVILY_API_KEY fehlt, es wird nur yfinance genutzt.")

    if OUT_CSV.exists() and not args.force:
        with open(OUT_CSV, encoding="utf-8") as f:
            if sum(1 for _ in f) > 1:
                raise SystemExit(f"{OUT_CSV} enthält bereits Daten (evtl. Labels). Mit --force überschreiben.")

    seen: set[str] = set()
    rows: list[dict] = []
    for ticker, company in load_tickers().items():
        kept = []
        for item in fetch_news(ticker, company, lookback_days=args.lookback_days, max_items=100):
            key = normalize_title(item["title"])
            if is_duplicate(key, seen):
                continue
            seen.add(key)
            kept.append({"text": item["title"], "ticker": ticker, "date": item["published"],
                         "source": item["source"], "url": item["url"], "label": ""})
            if len(kept) >= args.per_ticker:
                break
        rows.extend(kept)
        print(f"{ticker:<8} {len(kept):>2}  " + ", ".join(f"{s} {n}" for s, n in Counter(r['source'] for r in kept).most_common(3)))

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} Headlines → {OUT_CSV}")


if __name__ == "__main__":
    main()
