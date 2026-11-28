"""LLM-as-a-Judge mit fixem Bewertungsraster (Qualität der Memos).

Der Richter sieht nur das Memo (ohne Hinweis auf die Variante) und vergibt 1–5 Punkte für
Vollständigkeit, Begründung und Struktur. Als Richter dient ein stärkeres Modell als der Generator.
"""
from __future__ import annotations

import json

from eval.fact_check import memo_text
from tools import llm

JUDGE_MODEL = "gpt-4o"
CRITERIA = ("completeness", "reasoning", "structure")

RUBRIC = """Du bewertest ein kurzes Investment Memo zu einer Schweizer Aktie nach einem festen Raster.
Vergib je Kriterium 1–5 Punkte (5 = sehr gut):
- completeness: Deckt das Memo Profitabilität, Wachstum, Bilanz, Bewertung, Nachrichtenlage und Risiken ab?
- reasoning: Ist das Rating nachvollziehbar aus den genannten Fakten begründet, werden Widersprüche gewichtet?
- structure: Ist das Memo klar, knapp und logisch aufgebaut, ohne Wiederholungen und Floskeln?
Beurteile nicht, ob das Rating «richtig» ist. Antworte als JSON:
{"completeness": 1-5, "reasoning": 1-5, "structure": 1-5, "comment": "1 Satz"}"""


def judge_memo(memo: dict) -> dict:
    text = f"Rating: {memo.get('rating')} (Überzeugung: {memo.get('conviction')})\n\n{memo_text(memo)}"
    r = llm.chat([{"role": "system", "content": RUBRIC}, {"role": "user", "content": text}],
                 model=JUDGE_MODEL, json_mode=True)
    try:
        data = json.loads(r.content)
    except json.JSONDecodeError:
        data = {}
    scores = {c: data.get(c) if isinstance(data.get(c), int) and 1 <= data.get(c) <= 5 else None for c in CRITERIA}
    valid = [v for v in scores.values() if v is not None]
    return {**scores, "mean": sum(valid) / len(valid) if valid else None, "comment": data.get("comment", ""),
            "cost_chf": r.cost_chf}
