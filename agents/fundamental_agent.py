"""Fundamental-Agent: bewertet Profitabilität, Wachstum, Bilanz und Bewertung.

Zahlen und Scores werden deterministisch berechnet (tools.kennzahlen, tools.multiples);
das LLM interpretiert nur die fertige Faktentabelle.
"""
from __future__ import annotations

from agents.facts import fact_table
from graph.state import AnalysisState, FundamentalResult
from graph.trace import get_tracer
from tools import llm
from tools.kennzahlen import collect_kennzahlen
from tools.multiples import compute_multiples, score_dimensions

NODE = "fundamental"

SYSTEM_PROMPT = """Du bist Aktienanalyst für Schweizer Blue Chips. Du interpretierst Kennzahlen, die bereits
berechnet wurden. Regeln:
- Verwende ausschliesslich Zahlen aus der Faktentabelle, exakt wie dort angegeben. Rechne nichts neu.
- Werte mit 'n/a' sind nicht verfügbar: nenne sie nicht und schätze sie nicht.
- Kurz und sachlich, Deutsch (Schweizer Schreibweise, ss statt ß).
Antworte als JSON:
{"profitability": "1–2 Sätze", "growth": "1–2 Sätze", "balance_sheet": "1–2 Sätze",
 "valuation": "1–2 Sätze", "strengths": ["…", "…"], "risks": ["…", "…"], "summary": "2–3 Sätze"}"""


def _summarize_kennzahlen(r: dict) -> dict:
    sources = [s for s in r["source"].values() if s]
    v = r["validation"] or {}
    checked = [x for x in v.values() if x["ok"] is not None]
    return {"fiscal_year": r["metrics"].get("fiscal_year"), "aus_report": sources.count("report"),
            "aus_yfinance": sources.count("yfinance"),
            "validierung_ok": f"{sum(x['ok'] for x in checked)}/{len(checked)}" if checked else None}


def run_fundamental_agent(state: AnalysisState) -> dict:
    """Holt Kennzahlen, berechnet Multiples und Scores, lässt das LLM interpretieren.

    Gibt {"fundamental": FundamentalResult} zurück.
    """
    tracer = get_tracer()
    ticker, company = state["ticker"], state.get("company", state["ticker"])
    with tracer.node(NODE):
        data = tracer.tool(NODE, "collect_kennzahlen", collect_kennzahlen, ticker, summarize=_summarize_kennzahlen)
        multiples = tracer.tool(NODE, "compute_multiples", compute_multiples, data["metrics"],
                                summarize=lambda m: {k: round(v, 3) for k, v in m.items()
                                                     if k in ("operating_margin", "revenue_growth", "pe") and v is not None})
        scores = tracer.tool(NODE, "score_dimensions", score_dimensions, multiples)

        table = fact_table(data["metrics"], multiples, scores)
        response = llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Unternehmen: {company} ({ticker})\n\n{table}"},
        ], json_mode=True)
        tracer.llm_call(NODE, response, purpose="Interpretation Kennzahlen")
        try:
            rationale = response.json()
        except ValueError:
            rationale = {"summary": response.content}

        result: FundamentalResult = {
            "metrics": data["metrics"], "source": data["source"], "multiples": multiples,
            "scores": scores, "validation": data["validation"], "rationale": rationale,
        }
        tracer.result(NODE, {"scores": scores, "summary": rationale.get("summary", "")})
    return {"fundamental": result}
