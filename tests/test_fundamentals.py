"""Offline-Tests für Geschäftsbericht-Parsing, Multiples, Scores und Sentiment-Score (kein Netzwerk)."""
import pytest

from agents.news_agent import sentiment_score
from tools import ir_reports
from tools.multiples import compute_multiples, score_dimensions


def test_parse_number_formats():
    assert ir_reports.parse_number("89 490") == 89490
    assert ir_reports.parse_number("(48 694)") == -48694
    assert ir_reports.parse_number("1,234.5") == 1234.5
    assert ir_reports.parse_number("1'234") == 1234
    assert ir_reports.parse_number("3.51") == 3.51
    assert ir_reports.parse_number("-") is None
    assert ir_reports.parse_number("14.2%") is None
    assert ir_reports.parse_number("") is None


# Auszug im Format des Docling-Caches (Werte aus der Nestlé-Konzernrechnung 2025)
TABLES = [
    {"page": 6, "columns": ["In millions of CHF", "Notes", "2025", "2024"], "rows": [
        ["Sales", "3", "89 490", "91 354"],
        ["Operating profit", "", "12 277", "14 724"],
        ["of which attributable to shareholders of the parent (Net profit)", "", "9 033", "10 884"],
        ["Profit for the year attributable to shareholders of the parent", "", "10.1%", "11.9%"],
        ["Diluted earnings per share", "15", "3.51", "4.19"],
    ]},
    {"page": 9, "columns": ["In millions of CHF", "Notes", "2025", "2024"], "rows": [
        ["Financial debt", "12", "11 606", "11 863"],
        ["Financial debt", "12", "46 246", "51 697"],
        ["Total equity attributable to shareholders of the parent", "", "32 810", "35 917"],
    ]},
    {"page": 10, "columns": ["In millions of CHF", "Notes", "2025", "2024"], "rows": [
        ["Capital expenditure", "8", "(4 527)", "(5 638)"],
    ]},
]


def test_map_tables_to_standard_schema():
    r = ir_reports.map_tables(TABLES, 2025)
    v = r["values"]
    assert v["revenue"] == 89_490e6
    assert v["revenue_prev"] == 91_354e6
    assert v["operating_profit"] == 12_277e6
    assert v["net_income"] == 9_033e6
    assert v["eps_diluted"] == 3.51            # nicht mit der Einheit skaliert
    assert v["total_debt"] == (11_606 + 46_246) * 1e6
    assert v["capex"] == 4_527e6               # als Betrag
    assert v["currency"] == "CHF"
    assert v["cash"] is None                   # fehlt → None, nie geschätzt
    assert r["sources"]["revenue"].startswith("S. 6")


def test_validate_flags_deviation_over_two_percent():
    out = ir_reports.validate({"revenue": 100.0, "cash": 107.0, "capex": None},
                              {"revenue": 101.0, "cash": 100.0, "capex": 5.0})
    assert out["revenue"]["ok"] is True
    assert out["cash"]["ok"] is False
    assert out["capex"]["ok"] is None


def test_multiples_and_missing_values():
    k = {"revenue": 100.0, "revenue_prev": 80.0, "operating_profit": 20.0, "depreciation_amortization": 5.0,
         "net_income": 10.0, "total_equity": 50.0, "total_assets": 200.0, "total_debt": 40.0, "cash": 15.0,
         "operating_cash_flow": 30.0, "capex": 10.0, "price": 20.0, "eps_diluted": 1.0, "market_cap": 200.0,
         "dividend_per_share": 0.5, "dividends_paid": 5.0}
    m = compute_multiples(k)
    assert m["revenue_growth"] == pytest.approx(0.25)
    assert m["operating_margin"] == pytest.approx(0.2)
    assert m["ebitda"] == 25.0
    assert m["net_debt"] == 25.0
    assert m["enterprise_value"] == 225.0
    assert m["pe"] == 20.0
    assert m["ev_ebitda"] == pytest.approx(9.0)
    assert compute_multiples({"revenue": 100.0})["operating_margin"] is None
    assert compute_multiples({"price": 10.0, "eps_diluted": -1.0})["pe"] is None   # negatives EPS → kein KGV


def test_scores_are_bounded_and_skip_missing():
    s = score_dimensions({"operating_margin": 0.5, "roe": None, "revenue_growth": -0.2})
    assert s["profitability"] == 10.0
    assert s["growth"] == 0.0
    assert s["valuation"] is None
    assert s["overall"] == 5.0


def test_sentiment_score():
    assert sentiment_score(["positive", "positive", "negative", "neutral"]) == 0.25
    assert sentiment_score([None, None]) is None
    assert sentiment_score([]) is None
