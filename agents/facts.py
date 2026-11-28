"""Einheitliche Faktentabelle: formatiert berechnete Kennzahlen für Prompts und Faktencheck.

Das LLM bekommt nur diese Tabelle und darf nur diese Zahlen zitieren. Die Evaluation (H3)
prüft jede Zahl im Memo gegen dieselben Werte.
"""
from __future__ import annotations

AMOUNT_KEYS = {
    "revenue": "Umsatz", "operating_profit": "Betriebsergebnis (EBIT)", "net_income": "Reingewinn (Aktionäre)",
    "ebitda": "EBITDA", "net_debt": "Nettoverschuldung", "free_cash_flow": "Free Cashflow",
    "market_cap": "Börsenwert", "enterprise_value": "Enterprise Value",
}
RATIO_KEYS = {
    "revenue_growth": "Umsatzwachstum", "operating_margin": "EBIT-Marge", "net_margin": "Nettomarge",
    "roe": "Eigenkapitalrendite (ROE)", "equity_ratio": "Eigenkapitalquote", "fcf_margin": "FCF-Marge",
    "fcf_yield": "FCF-Rendite", "dividend_yield": "Dividendenrendite", "payout_ratio": "Ausschüttungsquote",
}
MULTIPLE_KEYS = {
    "pe": "KGV", "ev_ebitda": "EV/EBITDA", "ev_sales": "EV/Umsatz", "pb": "Kurs/Buchwert",
    "net_debt_to_ebitda": "Nettoverschuldung/EBITDA",
}
SCORE_LABELS = {"profitability": "Profitabilität", "growth": "Wachstum", "balance_sheet": "Bilanz",
                "valuation": "Bewertung", "overall": "Gesamt"}


def fact_values(metrics: dict, multiples: dict) -> dict[str, tuple[str, float | None, str]]:
    """Schlüssel → (Bezeichnung, Zahl wie angezeigt, Einheit). Zahl None = nicht verfügbar."""
    ccy = metrics.get("currency") or ""
    data = {**metrics, **multiples}
    facts: dict[str, tuple[str, float | None, str]] = {}
    for key, label in AMOUNT_KEYS.items():
        v = data.get(key)
        facts[key] = (label, None if v is None else round(v / 1e9, 2), f"Mrd. {ccy}")
    for key, label in RATIO_KEYS.items():
        v = data.get(key)
        facts[key] = (label, None if v is None else round(v * 100, 1), "%")
    for key, label in MULTIPLE_KEYS.items():
        v = data.get(key)
        facts[key] = (label, None if v is None else round(v, 1), "x")
    price = metrics.get("price")
    facts["price"] = ("Aktienkurs", None if price is None else round(price, 2), ccy)
    eps = metrics.get("eps_diluted")
    facts["eps_diluted"] = ("Gewinn je Aktie (verwässert)", None if eps is None else round(eps, 2), ccy)
    return facts


def fact_table(metrics: dict, multiples: dict, scores: dict | None = None) -> str:
    """Markdown-Tabelle für Prompts; fehlende Werte als 'n/a'."""
    lines = [f"Geschäftsjahr {metrics.get('fiscal_year')}, Berichtswährung {metrics.get('currency')}", "",
             "| Kennzahl | Wert |", "|---|---|"]
    for label, value, unit in fact_values(metrics, multiples).values():
        lines.append(f"| {label} | {'n/a' if value is None else f'{value:g} {unit}'} |")
    if scores:
        lines += ["", "| Score (0–10, regelbasiert berechnet) | Wert |", "|---|---|"]
        for key, label in SCORE_LABELS.items():
            s = scores.get(key)
            lines.append(f"| {label} | {'n/a' if s is None else s} |")
    return "\n".join(lines)
