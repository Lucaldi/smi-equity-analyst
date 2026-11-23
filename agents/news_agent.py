"""News-Agent: sammelt, filtert und bewertet News zum Unternehmen."""
from __future__ import annotations

from graph.state import AnalysisState, NewsResult


def run_news_agent(state: AnalysisState) -> dict:
    """Holt News (tools.news_fetcher), klassifiziert jede Meldung
    (tools.sentiment_classifier), aggregiert den Score und fasst Themen zusammen.

    Gibt {"news": NewsResult} zurück.
    """
    raise NotImplementedError
