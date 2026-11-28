"""Bewertungs- und Qualitätskennzahlen sowie Scores aus Rohdaten (deterministisch, kein LLM).

Alle Werte in der Berichtswährung (Marktdaten werden in tools.kennzahlen umgerechnet).
Fehlt ein Eingangswert, ist das Ergebnis None, nie geschätzt.
"""
from __future__ import annotations


def _div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _sub(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def compute_multiples(k: dict) -> dict[str, float | None]:
    """Berechnet abgeleitete Kennzahlen (Margen, Wachstum, Bilanz, Multiples)."""
    ebitda = None if k.get("operating_profit") is None or k.get("depreciation_amortization") is None \
        else k["operating_profit"] + k["depreciation_amortization"]
    net_debt = _sub(k.get("total_debt"), k.get("cash"))
    fcf = _sub(k.get("operating_cash_flow"), k.get("capex"))
    market_cap = k.get("market_cap")
    if market_cap is None and k.get("price") is not None and k.get("shares_outstanding") is not None:
        market_cap = k["price"] * k["shares_outstanding"]
    ev = None if market_cap is None or net_debt is None else market_cap + net_debt
    eps = k.get("eps_diluted")

    return {
        "revenue_growth": _sub(_div(k.get("revenue"), k.get("revenue_prev")), 1.0),
        "operating_margin": _div(k.get("operating_profit"), k.get("revenue")),
        "net_margin": _div(k.get("net_income"), k.get("revenue")),
        "ebitda": ebitda,
        "roe": _div(k.get("net_income"), k.get("total_equity")),
        "equity_ratio": _div(k.get("total_equity"), k.get("total_assets")),
        "net_debt": net_debt,
        "net_debt_to_ebitda": _div(net_debt, ebitda),
        "free_cash_flow": fcf,
        "fcf_margin": _div(fcf, k.get("revenue")),
        "market_cap": market_cap,
        "enterprise_value": ev,
        "pe": _div(k.get("price"), eps) if eps is not None and eps > 0 else None,
        "ev_ebitda": _div(ev, ebitda) if ebitda is not None and ebitda > 0 else None,
        "ev_sales": _div(ev, k.get("revenue")),
        "pb": _div(market_cap, k.get("total_equity")),
        "fcf_yield": _div(fcf, market_cap),
        "dividend_yield": _div(k.get("dividend_per_share"), k.get("price")),
        "payout_ratio": _div(k.get("dividends_paid"), k.get("net_income")),
    }


# Score-Regeln: Kennzahl → (Wert für Score 0, Wert für Score 10), linear dazwischen, begrenzt auf 0–10.
# Bewusst einfache, transparente Schwellen für grosse Schweizer Industrie-/Konsumtitel;
# für Banken und Versicherungen sind Margen und EBITDA nur bedingt aussagekräftig.
SCORE_RULES: dict[str, dict[str, tuple[float, float]]] = {
    "profitability": {"operating_margin": (0.0, 0.25), "roe": (0.0, 0.25)},
    "growth": {"revenue_growth": (-0.05, 0.10)},
    "balance_sheet": {"equity_ratio": (0.10, 0.50), "net_debt_to_ebitda": (4.0, 0.0)},
    "valuation": {"pe": (35.0, 10.0), "ev_ebitda": (25.0, 6.0), "fcf_yield": (0.0, 0.08)},
}


def _scale(value: float, zero: float, ten: float) -> float:
    score = (value - zero) / (ten - zero) * 10
    return max(0.0, min(10.0, score))


def score_dimensions(m: dict[str, float | None]) -> dict[str, float | None]:
    """Score 0–10 je Dimension (Mittel der verfügbaren Kennzahlen; None, wenn keine verfügbar)."""
    scores: dict[str, float | None] = {}
    for dim, rules in SCORE_RULES.items():
        parts = [_scale(m[key], lo, hi) for key, (lo, hi) in rules.items() if m.get(key) is not None]
        scores[dim] = round(sum(parts) / len(parts), 1) if parts else None
    available = [s for s in scores.values() if s is not None]
    scores["overall"] = round(sum(available) / len(available), 1) if available else None
    return scores
