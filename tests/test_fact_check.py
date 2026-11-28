"""Tests für den automatischen Faktencheck (H3)."""
from eval.fact_check import allowed_values, check_memo, extract_numbers

METRICS = {"revenue": 89_490e6, "revenue_prev": 91_354e6, "fiscal_year": 2025, "currency": "CHF",
           "price": 87.34, "eps_diluted": 3.51}
MULTIPLES = {"revenue_growth": -0.0204, "operating_margin": 0.1372, "free_cash_flow": 11_377e6,
             "debt_to_equity": 1.7632, "pe": 24.88}


def test_extract_numbers_units():
    nums = extract_numbers("Umsatz 89.49 Mrd. CHF, Marge 13.7 %, Capex 4'527 Mio. CHF, KGV 24.9x")
    values = [round(n["value"], 3) for n in nums]
    assert values == [89.49, 13.7, 4.527, 24.9]


def test_supported_with_rounding():
    allowed = allowed_values(METRICS, MULTIPLES)
    memo = {"summary": "Der Umsatz sank um 2 % auf 89.5 Mrd. CHF, die EBIT-Marge liegt bei 13.7 %.",
            "fundamental_view": "Free Cashflow 11.38 Mrd. CHF, Verschuldungsgrad 1,76, KGV 24.9.",
            "risks": ["Umsatzrückgang im Geschäftsjahr 2025"]}
    r = check_memo(memo, allowed)
    assert r["unsupported"] == []
    assert r["faithfulness"] == 1.0


def test_unsupported_number_is_flagged_with_context():
    allowed = allowed_values(METRICS, MULTIPLES)
    r = check_memo({"summary": "Die EBIT-Marge liegt bei 18.4 %."}, allowed)
    assert r["unsupported"] == ["18.4 %"]
    assert "EBIT-Marge" in r["unsupported_context"][0]
    assert r["faithfulness"] == 0.0


def test_simple_ratios_in_percent_are_supported():
    metrics = {**METRICS, "total_debt": 20.0e9, "total_assets": 96.3e9, "total_equity": 35.6e9}
    r = check_memo({"summary": "Schuldenquote 20.8 %, Verschuldungsgrad 56.2 %."}, allowed_values(metrics, MULTIPLES))
    assert r["unsupported"] == []


def test_memo_without_numbers():
    assert check_memo({"summary": "Solide Lage."}, [])["faithfulness"] is None
