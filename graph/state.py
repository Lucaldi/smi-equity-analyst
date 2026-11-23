"""Gemeinsamer Zustand, der durch den LangGraph-Graphen gereicht wird."""
from __future__ import annotations

from typing import Literal, TypedDict

Sentiment = Literal["positive", "neutral", "negative"]


class NewsItem(TypedDict):
    title: str
    source: str
    published: str          # ISO-8601
    url: str
    sentiment: Sentiment | None


class FundamentalResult(TypedDict):
    metrics: dict[str, float | None]     # Rohkennzahlen aus tools/kennzahlen.py
    scores: dict[str, float]             # Profitabilität, Wachstum, Bilanz, Bewertung (0–10)
    rationale: str


class NewsResult(TypedDict):
    items: list[NewsItem]
    sentiment_score: float               # -1 … +1
    themes: list[str]
    rationale: str


class AnalysisState(TypedDict, total=False):
    ticker: str
    company: str
    fundamental: FundamentalResult
    news: NewsResult
    memo: dict                           # finales Investment Memo
    errors: list[str]
