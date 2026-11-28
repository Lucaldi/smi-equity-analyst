"""Gemeinsamer Zustand, der durch den LangGraph-Graphen gereicht wird."""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

Sentiment = Literal["positive", "neutral", "negative"]


class NewsItem(TypedDict):
    title: str
    source: str
    published: str          # ISO-8601
    url: str
    sentiment: Sentiment | None


class FundamentalResult(TypedDict):
    metrics: dict                        # Rohkennzahlen (Standardschema, tools/kennzahlen.py)
    source: dict[str, str | None]        # pro Kennzahl: report | yfinance
    multiples: dict[str, float | None]   # abgeleitete Kennzahlen (tools/multiples.py)
    scores: dict[str, float | None]      # Profitabilität, Wachstum, Bilanz, Bewertung, Gesamt (0–10)
    validation: dict | None              # PDF ↔ yfinance (nur mit Geschäftsbericht)
    rationale: dict                      # LLM-Interpretation je Dimension, Stärken, Risiken


class NewsResult(TypedDict):
    items: list[NewsItem]
    counts: dict[str, int]               # Anzahl positive / neutral / negative
    sentiment_score: float | None        # -1 … +1 (None ohne News)
    themes: list[str]
    rationale: str


class AnalysisState(TypedDict, total=False):
    ticker: str
    company: str
    fundamental: FundamentalResult
    news: NewsResult
    memo: dict                           # finales Investment Memo
    errors: Annotated[list[str], operator.add]   # parallele Knoten dürfen beide Fehler melden
