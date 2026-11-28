"""LangGraph-Definition: Fundamental- und News-Agent laufen parallel, der Supervisor synthetisiert."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from langgraph.graph import END, START, StateGraph

from agents.fundamental_agent import run_fundamental_agent
from agents.news_agent import run_news_agent
from agents.supervisor import render_memo, run_supervisor
from graph.state import AnalysisState
from graph.trace import Tracer, set_tracer
from tools import llm

MEMO_DIR = Path("eval/results/memos")


def _safe(name: str, fn: Callable[[AnalysisState], dict]) -> Callable[[AnalysisState], dict]:
    """Fehler eines Spezialisten stoppen die Analyse nicht: Der Supervisor arbeitet mit dem Rest."""
    def node(state: AnalysisState) -> dict:
        try:
            return fn(state)
        except Exception as exc:
            return {"errors": [f"{name}: {type(exc).__name__}: {exc}"]}
    return node


def build_graph():
    """Erstellt und kompiliert den Analyse-Graphen.

    Knoten: fundamental, news, supervisor
    Ablauf: START → fundamental + news (parallel) → supervisor → END
    """
    g = StateGraph(AnalysisState)
    g.add_node("fundamental", _safe("Fundamental-Agent", run_fundamental_agent))
    g.add_node("news", _safe("News-Agent", run_news_agent))
    g.add_node("supervisor", run_supervisor)
    g.add_edge(START, "fundamental")
    g.add_edge(START, "news")
    g.add_edge(["fundamental", "news"], "supervisor")   # wartet auf beide
    g.add_edge("supervisor", END)
    return g.compile()


def run_analysis(ticker: str, company: str | None = None, trace: bool = False, label: str = "",
                 save: bool = True) -> dict:
    """Führt die komplette Analyse für einen Ticker aus.

    Rückgabe: Endzustand plus `meta` (Dauer, LLM-Kosten, Pfade zu Memo und Trace).
    """
    tracer = Tracer(ticker, verbose=trace, label=label)
    set_tracer(tracer)
    llm.METER.reset()
    start = time.perf_counter()
    try:
        state = build_graph().invoke({"ticker": ticker, "company": company or ticker, "errors": []})
    finally:
        set_tracer(None)
    duration = time.perf_counter() - start
    usage = llm.METER.as_dict()
    markdown = render_memo(state.get("memo", {}), state)

    meta = {"duration_s": round(duration, 2), "usage": usage, "memo_path": None, "trace_path": None}
    if save:
        MEMO_DIR.mkdir(parents=True, exist_ok=True)
        memo_path = MEMO_DIR / f"{ticker}{'_' + label if label else ''}.md"
        memo_path.write_text(markdown, encoding="utf-8")
        meta["memo_path"] = str(memo_path)
        meta["trace_path"] = str(tracer.save({"usage": usage, "memo": state.get("memo"),
                                              "errors": state.get("errors")}))
    return {**state, "memo_markdown": markdown, "meta": meta}
