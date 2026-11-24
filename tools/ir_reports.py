"""Kennzahlen aus Geschäftsbericht-PDFs (deterministisch, kein LLM).

Ablauf:
    1. PDF-Link aus config/ir_sources.yaml lesen (kein Crawlen), PDF nach data/reports/ cachen
    2. Seiten der Konzernrechnung per Stichwort finden (DE/EN)
    3. Nur diese Seiten mit Docling parsen, Ergebnis als JSON in data/cache/ ablegen
    4. Mapping auf Standardschema; Validierung gegen yfinance (Abweichung > 2 % markieren)

Titel ohne Eintrag in ir_sources.yaml liefern None (Fallback: nur yfinance).
Fehlende Werte sind None, nie geschätzt.
"""
from __future__ import annotations


def fetch_report_kennzahlen(ticker: str) -> dict[str, float | None] | None:
    """Liefert die Kennzahlen aus dem Geschäftsbericht oder None, wenn kein PDF-Eintrag existiert."""
    raise NotImplementedError
