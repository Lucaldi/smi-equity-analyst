"""Supervisor-Agent: führt die Teilanalysen zu einem Investment Memo zusammen."""
from __future__ import annotations

import json

from agents.facts import SCORE_LABELS, fact_table
from graph.state import AnalysisState
from graph.trace import get_tracer
from tools import llm

NODE = "supervisor"
RATINGS = ("Kaufen", "Halten", "Verkaufen")

MEMO_SCHEMA = """{"rating": "Kaufen" | "Halten" | "Verkaufen",
 "conviction": "hoch" | "mittel" | "tief",
 "summary": "3–4 Sätze Gesamteinschätzung",
 "fundamental_view": "2–3 Sätze",
 "news_view": "2–3 Sätze",
 "conflicts": "Widersprüche zwischen Fundamentaldaten und News und wie du sie gewichtest (1–2 Sätze)",
 "risks": ["2–4 Risiken"]}"""

SYSTEM_PROMPT = f"""Du bist leitender Aktienanalyst und schreibst ein kurzes Investment Memo zu einem SMI-Titel.
Du bekommst die Ergebnisse zweier Spezialisten: Fundamentalanalyse (Faktentabelle mit regelbasierten
Scores 0–10 und Interpretation) und Newsanalyse (Sentiment-Score −1 bis +1, Themen).
Regeln:
- Verwende ausschliesslich Zahlen aus den Unterlagen, exakt wie angegeben. Rechne nichts neu.
- Werte mit 'n/a' sind nicht verfügbar: nicht nennen, nicht schätzen.
- Orientierung für das Rating: Gesamtscore ≥ 6.5 spricht für Kaufen, ≤ 4 für Verkaufen, dazwischen Halten;
  eine klar negative oder positive Nachrichtenlage kann um eine Stufe verschieben. Begründe Abweichungen.
- Deutsch (Schweizer Schreibweise, ss statt ß).
Antworte als JSON:
{MEMO_SCHEMA}"""


def render_memo(memo: dict, state: AnalysisState) -> str:
    """Memo als Markdown (Terminal-Ausgabe und Datei)."""
    f, n = state.get("fundamental") or {}, state.get("news") or {}
    scores = f.get("scores") or {}
    lines = [
        f"# Investment Memo: {state.get('company')} ({state['ticker']})", "",
        f"**Rating:** {memo.get('rating', 'n/a')} · **Überzeugung:** {memo.get('conviction', 'n/a')}", "",
        memo.get("summary", ""), "",
        "## Fundamentaldaten", memo.get("fundamental_view", ""), "",
        "Scores: " + ", ".join(f"{SCORE_LABELS[k]} {scores.get(k, 'n/a')}" for k in SCORE_LABELS), "",
        "## News", memo.get("news_view", ""), "",
    ]
    if n:
        c = n.get("counts", {})
        lines.append(f"Sentiment-Score {n.get('sentiment_score')} ({c.get('positive', 0)} positiv, "
                     f"{c.get('neutral', 0)} neutral, {c.get('negative', 0)} negativ); "
                     f"Themen: {', '.join(n.get('themes', []))}")
        lines.append("")
    lines += ["## Widersprüche", memo.get("conflicts", ""), "", "## Risiken"]
    lines += [f"- {r}" for r in memo.get("risks", [])]
    if state.get("errors"):
        lines += ["", "## Hinweise", *[f"- {e}" for e in state["errors"]]]
    return ("\n".join(lines) + "\n").replace("ß", "ss")   # Schweizer Schreibweise


def _parse_memo(content: str) -> dict:
    try:
        memo = json.loads(content)
    except json.JSONDecodeError:
        return {"rating": None, "summary": content}
    if memo.get("rating") not in RATINGS:
        memo["rating"] = None   # ungültiges Rating nicht raten
    return memo


def run_supervisor(state: AnalysisState) -> dict:
    """Synthetisiert Fundamental- und News-Ergebnis, löst Widersprüche auf und erstellt das Memo.

    Gibt {"memo": dict} zurück.
    """
    tracer = get_tracer()
    f, n = state.get("fundamental"), state.get("news")
    with tracer.node(NODE):
        parts = [f"Unternehmen: {state.get('company')} ({state['ticker']})"]
        if f:
            parts += ["## Fundamentalanalyse", fact_table(f["metrics"], f["multiples"], f["scores"]),
                      "Interpretation: " + json.dumps(f["rationale"], ensure_ascii=False)]
        else:
            parts.append("## Fundamentalanalyse\nnicht verfügbar")
        if n:
            parts += ["## Newsanalyse",
                      f"Sentiment-Score: {n['sentiment_score']} (Headlines: {n['counts']})",
                      f"Themen: {', '.join(n['themes'])}", f"Einschätzung: {n['rationale']}"]
        else:
            parts.append("## Newsanalyse\nnicht verfügbar")
        if state.get("errors"):
            parts.append("Hinweise: " + "; ".join(state["errors"]))

        response = llm.chat([{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": "\n\n".join(parts)}], json_mode=True)
        tracer.llm_call(NODE, response, purpose="Memo")
        memo = _parse_memo(response.content)
        tracer.result(NODE, {"rating": memo.get("rating"), "conviction": memo.get("conviction")})
    return {"memo": memo}
