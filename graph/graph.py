"""LangGraph-Definition: Supervisor ruft Fundamental- und News-Agent auf und synthetisiert."""
from __future__ import annotations

from graph.state import AnalysisState


def build_graph():
    """Erstellt und kompiliert den Analyse-Graphen.

    Knoten: fundamental, news, supervisor
    Ablauf: START → fundamental + news (parallel) → supervisor → END
    """
    raise NotImplementedError


def run_analysis(ticker: str) -> AnalysisState:
    """Führt die komplette Analyse für einen Ticker aus und gibt den Endzustand zurück."""
    raise NotImplementedError
