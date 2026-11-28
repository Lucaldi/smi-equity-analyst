"""Sentiment-Klassifikation einzelner Headlines: positive / neutral / negative.

Kein Training: alle Backends nutzen vortrainierte Modelle bzw. APIs (nur Inferenz).
Backend per SENTIMENT_BACKEND (.env) wählbar:
    llm     – OpenAI Zero-shot (Standard), optional Few-shot; Modell per SENTIMENT_LLM_MODEL
    finbert – ProsusAI/finbert, vortrainiert, lokal auf CPU

Vorhersagen werden als JSON in data/cache/sentiment/ gecacht (eine Datei pro Backend, Modell und
Prompt-Art; Schlüssel: Lauf-Nummer + Headline). Gespeichert werden auch Latenz und Kosten des
ursprünglichen Aufrufs, damit die Auswertung bei wiederholten Läufen dieselben Werte zeigt.
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv

from graph.state import Sentiment
from tools import llm

load_dotenv()

LABELS: tuple[str, ...] = ("positive", "neutral", "negative")

SYSTEM_PROMPT = """You classify the sentiment of a financial news headline about a listed company.
Question: How will this headline most likely affect the share price of the company it is about,
from the perspective of a shareholder?

positive: clearly good news (earnings/sales above expectations, upgrade, higher price target,
          regulatory approval, raised guidance, attractive acquisition)
negative: clearly bad news (profit warning, downgrade, lawsuit/fine, recall, job cuts due to
          weakness, lowered guidance, CEO leaving under pressure)
neutral:  information without clear direction (dates, appointments, market reports, mixed news)
If in doubt, answer neutral. Judge only the headline.
Answer with JSON: {"label": "positive" | "neutral" | "negative"}"""

# Few-shot-Beispiele: bewusst NICHT aus dem Testset und nicht zu SMI-Titeln (kein Leakage)
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    ("Siemens raises full-year profit guidance after strong orders", "positive"),
    ("Analysts upgrade Unilever to buy on margin recovery", "positive"),
    ("BASF issues profit warning as chemical demand slumps", "negative"),
    ("Bayer shares fall after court rules against it in glyphosate case", "negative"),
    ("Danone names new chief financial officer", "neutral"),
    ("Volkswagen to report third-quarter results on Thursday", "neutral"),
    ("Heineken sales rise but costs weigh on profit outlook", "neutral"),
]


class Prediction(TypedDict):
    text: str
    label: Sentiment | None
    latency_s: float
    cost_chf: float | None
    cached: bool


def _cache_dir() -> Path:
    base = (os.getenv("CACHE_DIR") or "data/cache").split("#")[0].strip()
    path = Path(base) / "sentiment"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).split("#")[0].strip() or default


class _Cache:
    """JSON-Cache für eine Kombination aus Backend, Modell und Prompt-Art."""

    def __init__(self, name: str):
        self.path = _cache_dir() / f"{name.replace('/', '_')}.json"
        self.data: dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self._lock = threading.Lock()

    def get(self, run: int, text: str) -> dict | None:
        return self.data.get(f"{run}|{text}")

    def put(self, run: int, text: str, value: dict) -> None:
        with self._lock:
            self.data[f"{run}|{text}"] = value

    def save(self) -> None:
        with self._lock:
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- LLM ----------

def _llm_messages(text: str, few_shot: bool) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if few_shot:
        for headline, label in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": headline})
            messages.append({"role": "assistant", "content": json.dumps({"label": label})})
    messages.append({"role": "user", "content": text})
    return messages


def _parse_label(content: str) -> Sentiment | None:
    try:
        label = str(json.loads(content).get("label", "")).strip().lower()
    except (json.JSONDecodeError, AttributeError):
        return None
    return label if label in LABELS else None   # ungültige Antwort → None, nie raten


def _classify_llm(texts: list[str], model: str, few_shot: bool, run: int, use_cache: bool,
                  workers: int = 8) -> list[Prediction]:
    cache = _Cache(f"llm_{model}_{'fewshot' if few_shot else 'zeroshot'}")

    def one(text: str) -> Prediction:
        hit = cache.get(run, text) if use_cache else None
        if hit:
            return {"text": text, **hit, "cached": True}
        r = llm.chat(_llm_messages(text, few_shot), model=model, json_mode=True, max_tokens=20)
        value = {"label": _parse_label(r.content), "latency_s": round(r.latency_s, 4), "cost_chf": r.cost_chf}
        cache.put(run, text, value)
        return {"text": text, **value, "cached": False}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        preds = list(pool.map(one, texts))
    cache.save()
    return preds


# ---------- FinBERT ----------

_finbert = None
_finbert_lock = threading.Lock()


def _get_finbert():
    global _finbert
    with _finbert_lock:
        if _finbert is None:
            from transformers import pipeline
            _finbert = pipeline("text-classification", model=_env("FINBERT_MODEL", "ProsusAI/finbert"), device=-1)
    return _finbert


def _classify_finbert(texts: list[str], run: int, use_cache: bool) -> list[Prediction]:
    cache = _Cache("finbert_" + _env("FINBERT_MODEL", "ProsusAI/finbert"))
    preds: list[Prediction] = []
    for text in texts:   # einzeln, damit die Latenz pro Headline vergleichbar mit dem LLM ist
        hit = cache.get(run, text) if use_cache else None
        if hit:
            preds.append({"text": text, **hit, "cached": True})
            continue
        model = _get_finbert()
        start = time.perf_counter()
        out = model(text, truncation=True)[0]
        latency = time.perf_counter() - start
        label = out["label"].lower()
        value = {"label": label if label in LABELS else None, "latency_s": round(latency, 4), "cost_chf": 0.0}
        cache.put(run, text, value)
        preds.append({"text": text, **value, "cached": False})
    cache.save()
    return preds


# ---------- öffentliche Schnittstelle ----------

def classify_detailed(texts: list[str], backend: str | None = None, model: str | None = None,
                      few_shot: bool = False, run: int = 0, use_cache: bool = True) -> list[Prediction]:
    """Klassifiziert Headlines und liefert pro Headline Label, Latenz und Kosten.

    `run` trennt wiederholte Läufe im Cache (für die Konsistenzmessung in H2).
    """
    backend = backend or _env("SENTIMENT_BACKEND", "llm")
    if backend == "finbert":
        return _classify_finbert(texts, run, use_cache)
    if backend == "llm":
        model = model or _env("SENTIMENT_LLM_MODEL") or llm.default_model()
        return _classify_llm(texts, model, few_shot, run, use_cache)
    raise ValueError(f"Unbekanntes SENTIMENT_BACKEND: {backend!r} (llm | finbert)")


def classify(texts: list[str], backend: str | None = None) -> list[Sentiment | None]:
    """Klassifiziert eine Liste von Headlines (Standard-Backend aus .env, mit Cache)."""
    return [p["label"] for p in classify_detailed(texts, backend=backend)]
