"""Sentiment-Klassifikation einzelner News: positive / neutral / negative.

Backend per SENTIMENT_BACKEND (.env) wählbar, damit die Varianten V1–V3
im selben Agenten verglichen werden können:
    tfidf   – TF-IDF + Logistic Regression
    finbert – fine-getuntes FinBERT
    llm     – LLM Zero-shot
"""
from __future__ import annotations

from graph.state import Sentiment


def classify(texts: list[str], backend: str | None = None) -> list[Sentiment]:
    """Klassifiziert eine Liste von Headlines."""
    raise NotImplementedError
