"""Fundamental-Agent: bewertet Profitabilität, Wachstum, Bilanz und Bewertung."""
from __future__ import annotations

from graph.state import AnalysisState, FundamentalResult


def run_fundamental_agent(state: AnalysisState) -> dict:
    """Holt Kennzahlen (tools.kennzahlen), berechnet Multiples (tools.multiples)
    und lässt das LLM die Zahlen interpretieren.

    Gibt {"fundamental": FundamentalResult} zurück.
    """
    raise NotImplementedError
