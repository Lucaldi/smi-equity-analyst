"""Nachvollziehbarkeit: jeder Graph-Knoten loggt Start, Tool-Aufrufe, Zwischenergebnis und Dauer.

Mit --trace erscheinen die Schritte im Terminal; zusätzlich wird jeder Lauf als JSON in
eval/results/traces/ gespeichert.
"""
from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tools import llm

TRACE_DIR = Path("eval/results/traces")


def _short(value: Any, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


class Tracer:
    def __init__(self, ticker: str, verbose: bool = False, label: str = ""):
        self.ticker = ticker
        self.verbose = verbose
        self.label = label
        self.events: list[dict] = []
        self.started = time.perf_counter()
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self._lock = threading.Lock()

    def _log(self, node: str, kind: str, **data) -> None:
        event = {"t_s": round(time.perf_counter() - self.started, 3), "node": node, "kind": kind, **data}
        with self._lock:
            self.events.append(event)
        if self.verbose:
            detail = "  ".join(f"{k}={_short(v)}" for k, v in data.items())
            print(f"[{event['t_s']:7.2f}s] {node:<12} {kind:<7} {detail}", flush=True)

    @contextmanager
    def node(self, name: str):
        """Umschliesst einen Graph-Knoten: Start, Dauer, LLM-Kosten des Knotens, Fehler."""
        before = llm.METER.as_dict()
        start = time.perf_counter()
        self._log(name, "start")
        try:
            yield self
        except Exception as exc:
            self._log(name, "error", error=repr(exc))
            raise
        finally:
            after = llm.METER.as_dict()
            self._log(name, "end", duration_s=round(time.perf_counter() - start, 3),
                      llm_calls=after["calls"] - before["calls"],
                      cost_chf=round(after["cost_chf"] - before["cost_chf"], 5))

    def tool(self, node: str, name: str, fn: Callable, *args, summarize: Callable | None = None, **kwargs):
        """Führt ein Tool aus und loggt Argumente, Ergebnis-Zusammenfassung und Dauer."""
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        self._log(node, "tool", tool=name, args=[*args, *kwargs.values()],
                  result=summarize(result) if summarize else _short(result),
                  duration_s=round(time.perf_counter() - start, 3))
        return result

    def llm_call(self, node: str, response: "llm.LLMResponse", purpose: str = "") -> None:
        self._log(node, "llm", purpose=purpose, model=response.model, tokens_in=response.input_tokens,
                  tokens_out=response.output_tokens, latency_s=round(response.latency_s, 2))

    def result(self, node: str, summary: Any) -> None:
        self._log(node, "result", summary=summary)

    def save(self, extra: dict | None = None) -> Path:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = f"_{self.label}" if self.label else ""
        path = TRACE_DIR / f"{self.ticker}_{stamp}{suffix}.json"
        payload = {"ticker": self.ticker, "started_at": self.started_at,
                   "duration_s": round(time.perf_counter() - self.started, 3),
                   "events": self.events, **(extra or {})}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return path


_current: Tracer | None = None


def set_tracer(tracer: Tracer | None) -> None:
    global _current
    _current = tracer


def get_tracer() -> Tracer:
    """Aktueller Tracer; ohne laufende Analyse ein stiller Tracer (z. B. in Tests)."""
    return _current or Tracer("-", verbose=False)
