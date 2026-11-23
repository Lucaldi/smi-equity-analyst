"""Kennzahlen-Fetcher via yfinance (deterministisch, kein LLM)."""
from __future__ import annotations


def fetch_kennzahlen(ticker: str) -> dict[str, float | None]:
    """Liefert die Rohkennzahlen eines Titels, z. B. Umsatz, EBIT-Marge,
    Umsatzwachstum, Nettoverschuldung, Eigenkapitalquote, KGV, EV/EBITDA.

    Fehlende Werte werden als None zurückgegeben, nie geschätzt.
    """
    raise NotImplementedError
