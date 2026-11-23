"""Supervisor-Agent: führt die Teilanalysen zu einem Investment Memo zusammen."""
from __future__ import annotations

from graph.state import AnalysisState


def run_supervisor(state: AnalysisState) -> dict:
    """Synthetisiert Fundamental- und News-Ergebnis, löst Widersprüche auf
    und erstellt das Memo (Gesamteinschätzung, Begründung, Risiken).

    Gibt {"memo": dict} zurück.
    """
    raise NotImplementedError
