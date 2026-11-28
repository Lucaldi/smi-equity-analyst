"""Variante A für die Evaluation: ein einzelner LLM-Aufruf macht alles.

Gleiche Eingangsdaten wie das Multi-Agenten-System (Rohkennzahlen aus tools.kennzahlen und
Headlines aus tools.news_fetcher), aber ohne deterministische Multiples, ohne regelbasierte
Scores und ohne Sentiment-Classifier: Das LLM rechnet, bewertet und schreibt selbst.
"""
from __future__ import annotations

import json

from agents.supervisor import MEMO_SCHEMA, _parse_memo
from graph.trace import get_tracer
from tools import llm

NODE = "single"

SYSTEM_PROMPT = f"""Du bist Aktienanalyst und schreibst ein kurzes Investment Memo zu einem SMI-Titel.
Du bekommst Rohkennzahlen (Jahreszahlen in Berichtswährung, Marktdaten) und Headlines der letzten 90 Tage.
Berechne die nötigen Kennzahlen selbst (Margen, Wachstum, Verschuldung, Bewertung), beurteile die
Nachrichtenlage und gib ein Rating. Werte mit null sind nicht verfügbar: nicht nennen, nicht schätzen.
Deutsch (Schweizer Schreibweise, ss statt ß).
Antworte als JSON:
{MEMO_SCHEMA}"""


def run_single_agent(ticker: str, company: str, metrics: dict, headlines: list[dict]) -> dict:
    """Erstellt das Memo in einem Aufruf. Gibt das Memo (gleiches Schema wie der Supervisor) zurück."""
    tracer = get_tracer()
    with tracer.node(NODE):
        raw = {k: v for k, v in metrics.items() if k not in ("market_currency", "fx_market_to_report")}
        listing = "\n".join(f"- {h['published']} {h['title']} ({h['source']})" for h in headlines) or "keine"
        user = (f"Unternehmen: {company} ({ticker})\n\nRohkennzahlen:\n{json.dumps(raw, ensure_ascii=False)}"
                f"\n\nHeadlines:\n{listing}")
        response = llm.chat([{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": user}], json_mode=True)
        tracer.llm_call(NODE, response, purpose="Memo (Single-Agent)")
        memo = _parse_memo(response.content)
        tracer.result(NODE, {"rating": memo.get("rating")})
    return memo
