"""Kennzahlen-Fetcher (deterministisch, kein LLM).

- `fetch_kennzahlen`: Jahreszahlen und Marktdaten aus yfinance im Standardschema
- `collect_kennzahlen`: Geschäftsbericht (tools.ir_reports) wo vorhanden, sonst yfinance;
  Marktdaten immer aus yfinance; Validierung PDF ↔ yfinance

Fehlende Werte werden als None zurückgegeben, nie geschätzt.
"""
from __future__ import annotations

import logging
import math

import yfinance as yf

from tools import ir_reports

log = logging.getLogger(__name__)

# Standardschema ← yfinance-Zeilen (erste vorhandene gewinnt)
INCOME_ROWS = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "operating_profit": ["Total Operating Income As Reported", "Operating Income", "EBIT"],
    "net_income": ["Net Income Common Stockholders", "Net Income"],
    "eps_diluted": ["Diluted EPS"],
}
BALANCE_ROWS = {
    "total_assets": ["Total Assets"],
    "total_liabilities": ["Total Liabilities Net Minority Interest"],
    "total_equity": ["Stockholders Equity", "Common Stock Equity"],
    "cash": ["Cash And Cash Equivalents"],
    "total_debt": ["Total Debt"],
}
CASHFLOW_ROWS = {
    "operating_cash_flow": ["Operating Cash Flow"],
    "capex": ["Capital Expenditure"],
    "depreciation_amortization": ["Reconciled Depreciation", "Depreciation And Amortization"],
    "dividends_paid": ["Cash Dividends Paid", "Common Stock Dividend Paid"],
}
ABS_KEYS = {"capex", "dividends_paid"}          # als positive Beträge geführt
MARKET_KEYS = ("price", "shares_outstanding", "market_cap", "dividend_per_share")


def _num(value) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _row(df, names: list[str], col: int = 0) -> float | None:
    if df is None or df.empty or col >= df.shape[1]:
        return None
    for name in names:
        if name in df.index:
            v = _num(df.loc[name].iloc[col])
            if v is not None:
                return v
    return None


def fetch_kennzahlen(ticker: str) -> dict:
    """Rohkennzahlen aus yfinance (letztes Geschäftsjahr + aktuelle Marktdaten)."""
    t = yf.Ticker(ticker)
    income, balance, cashflow = t.income_stmt, t.balance_sheet, t.cashflow
    info = t.info or {}

    values: dict = {}
    for rows, df in ((INCOME_ROWS, income), (BALANCE_ROWS, balance), (CASHFLOW_ROWS, cashflow)):
        for key, names in rows.items():
            v = _row(df, names)
            values[key] = abs(v) if v is not None and key in ABS_KEYS else v
    values["revenue_prev"] = _row(income, INCOME_ROWS["revenue"], col=1)
    values["fiscal_year"] = int(income.columns[0].year) if income is not None and not income.empty else None
    values["currency"] = info.get("financialCurrency") or info.get("currency")
    values["price"] = _num(info.get("currentPrice") or info.get("regularMarketPrice"))
    values["shares_outstanding"] = _num(info.get("sharesOutstanding"))
    values["market_cap"] = _num(info.get("marketCap"))
    values["dividend_per_share"] = _num(info.get("dividendRate"))
    values["sector"] = info.get("sector")

    # Marktdaten in die Berichtswährung umrechnen (z. B. Novartis: Kurs in CHF, Bericht in USD)
    market_ccy = info.get("currency")
    values["market_currency"] = market_ccy
    values["fx_market_to_report"] = 1.0
    if market_ccy and values["currency"] and market_ccy != values["currency"]:
        rate = fx_rate(market_ccy, values["currency"])
        values["fx_market_to_report"] = rate
        for key in ("price", "market_cap", "dividend_per_share"):
            values[key] = values[key] * rate if values[key] is not None and rate is not None else None
    return values


def fx_rate(base: str, quote: str) -> float | None:
    """Aktueller Kurs base→quote aus yfinance (z. B. CHF→USD); None, wenn nicht verfügbar."""
    try:
        hist = yf.Ticker(f"{base}{quote}=X").history(period="5d")
        return _num(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
    except Exception as exc:
        log.warning("Wechselkurs %s%s nicht verfügbar: %s", base, quote, exc)
        return None


def collect_kennzahlen(ticker: str) -> dict:
    """Kombiniert Geschäftsbericht und yfinance.

    Rückgabe:
        metrics    – Standardschema; Jahreszahlen aus dem PDF, wo vorhanden, sonst yfinance
        source     – pro Kennzahl 'report' oder 'yfinance' (None, wenn fehlend)
        validation – PDF ↔ yfinance (nur mit PDF), siehe ir_reports.validate
        report     – Fundstellen im PDF und Cache-Pfad (oder None)
    """
    yf_values = fetch_kennzahlen(ticker)
    report = None
    try:
        report = ir_reports.fetch_report_kennzahlen(ticker)
    except Exception as exc:   # PDF-Probleme dürfen die Analyse nicht stoppen → Fallback yfinance
        log.warning("Geschäftsbericht %s nicht verwertbar: %s", ticker, exc)

    metrics, source = dict(yf_values), {k: ("yfinance" if v is not None else None) for k, v in yf_values.items()}
    validation = None
    if report:
        rv = report["values"]
        # PDF und yfinance müssen dasselbe Geschäftsjahr betreffen, sonst nur yfinance
        if yf_values.get("fiscal_year") in (None, rv["fiscal_year"]):
            for key, value in rv.items():
                if value is not None and key not in ("fiscal_year", "currency"):
                    metrics[key] = value
                    source[key] = "report"
            metrics["fiscal_year"] = rv["fiscal_year"]
            source["fiscal_year"] = "report"
            if rv.get("currency"):
                metrics["currency"], source["currency"] = rv["currency"], "report"
        validation = ir_reports.validate(rv, yf_values)
    return {"metrics": metrics, "source": source, "validation": validation,
            "report": {"sources": report["sources"], "cache": report["cache"]} if report else None}
