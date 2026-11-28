"""News-Agent: sammelt, filtert und bewertet News zum Unternehmen.

News-Abruf und Sentiment pro Headline sind Tools (tools.news_fetcher, tools.sentiment_classifier);
der Score wird in Python aggregiert. Das LLM fasst nur Themen zusammen und begründet.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from graph.state import AnalysisState, NewsItem, NewsResult
from graph.trace import get_tracer
from tools import llm
from tools.news_fetcher import fetch_news
from tools.sentiment_classifier import classify

NODE = "news"
CONFIG = Path(__file__).resolve().parent.parent / "config" / "smi_tickers.yaml"

SYSTEM_PROMPT = """Du bist Aktienanalyst. Du bekommst Headlines der letzten 90 Tage zu einem Unternehmen,
jeweils mit bereits bestimmtem Sentiment und Datum. Regeln:
- Ändere die Sentiment-Labels nicht und erfinde keine Ereignisse, die nicht in den Headlines stehen.
- Nenne keine Zahlen, die nicht wörtlich in einer Headline stehen.
- Deutsch (Schweizer Schreibweise, ss statt ß).
Antworte als JSON:
{"themes": ["3–5 Hauptthemen, je 2–6 Wörter"], "rationale": "2–3 Sätze zur Nachrichtenlage"}"""


def _news_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f).get("news", {})


def sentiment_score(labels: list[str | None]) -> float | None:
    """(positive − negative) / Anzahl bewerteter Headlines; None ohne bewertete Headlines."""
    valid = [l for l in labels if l is not None]
    if not valid:
        return None
    return round((valid.count("positive") - valid.count("negative")) / len(valid), 3)


def run_news_agent(state: AnalysisState) -> dict:
    """Holt News, klassifiziert jede Meldung, aggregiert den Score und fasst Themen zusammen.

    Gibt {"news": NewsResult} zurück.
    """
    tracer = get_tracer()
    ticker, company = state["ticker"], state.get("company", state["ticker"])
    cfg = _news_config()
    with tracer.node(NODE):
        items: list[NewsItem] = tracer.tool(
            NODE, "fetch_news", fetch_news, ticker, company,
            lookback_days=cfg.get("lookback_days", 90), max_items=cfg.get("max_items", 20),
            summarize=lambda r: {"anzahl": len(r), "quellen": dict(Counter(i["source"] for i in r).most_common(3))})

        labels = tracer.tool(NODE, "classify_sentiment", classify, [i["title"] for i in items],
                             summarize=lambda r: dict(Counter(r))) if items else []
        for item, label in zip(items, labels):
            item["sentiment"] = label
        counts = {k: labels.count(k) for k in ("positive", "neutral", "negative")}
        score = sentiment_score(labels)

        themes, rationale = [], "Keine relevanten News in den letzten 90 Tagen gefunden."
        if items:
            listing = "\n".join(f"- [{i['sentiment']}] {i['published']} {i['title']} ({i['source']})" for i in items)
            response = llm.chat([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Unternehmen: {company} ({ticker})\n\n{listing}"},
            ], json_mode=True)
            tracer.llm_call(NODE, response, purpose="Themen und Begründung")
            try:
                parsed = response.json()
                themes, rationale = list(parsed.get("themes", []))[:5], str(parsed.get("rationale", ""))
            except ValueError:
                rationale = response.content

        result: NewsResult = {"items": items, "counts": counts, "sentiment_score": score,
                              "themes": themes, "rationale": rationale}
        tracer.result(NODE, {"score": score, "counts": counts, "themes": themes})
    return {"news": result}
