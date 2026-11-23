"""News zu einem Ticker abrufen, deduplizieren und nach Relevanz filtern."""
from __future__ import annotations

from graph.state import NewsItem


def fetch_news(ticker: str, company: str, lookback_days: int = 90, max_items: int = 20) -> list[NewsItem]:
    """Holt News (Finnhub / yfinance), entfernt Duplikate und Meldungen ohne Bezug zum Unternehmen."""
    raise NotImplementedError
