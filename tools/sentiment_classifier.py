"""Sentiment-Klassifikation einzelner News: positive / neutral / negative.

Kein Training: alle Backends nutzen vortrainierte Modelle bzw. APIs (nur Inferenz).
Backend per SENTIMENT_BACKEND (.env) wählbar:
    llm     – LLM Zero-/Few-shot via API (Standard); Anbieter per
              SENTIMENT_LLM_PROVIDER: openai | anthropic
    finbert – ProsusAI/finbert, vortrainiert, lokal auf CPU

Vorhersagen werden als JSON in data/cache/ gecacht (Schlüssel: Backend, Modell, Headline).
"""
from __future__ import annotations

from graph.state import Sentiment


def classify(texts: list[str], backend: str | None = None) -> list[Sentiment]:
    """Klassifiziert eine Liste von Headlines."""
    raise NotImplementedError
