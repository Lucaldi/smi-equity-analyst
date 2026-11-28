"""Gemeinsamer Zugang zum Sprachmodell (OpenAI) mit Messung von Tokens, Kosten und Latenz.

Alle Agenten und der Sentiment-Classifier rufen das Modell über `chat()` auf. Jeder Aufruf
wird im `UsageMeter` verbucht, damit Kosten pro Analyse (H5) und pro Headline (H2) aus
denselben Zahlen stammen.
"""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# Preise in USD pro 1 Mio. Tokens (input, output), Stand Listenpreise OpenAI.
# Vor der Auswertung auf https://openai.com/api/pricing prüfen.
PRICES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (2.50, 10.00),
}
USD_CHF = 0.80   # Umrechnungskurs für die Angabe in CHF (Annahme, im Bericht nennen)


def default_model() -> str:
    return os.getenv("LLM_MODEL") or "gpt-4o-mini"


def cost_chf(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Kosten eines Aufrufs in CHF; None, wenn für das Modell kein Preis hinterlegt ist."""
    price = PRICES_USD_PER_MTOK.get(model)
    if price is None:
        return None
    usd = (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000
    return usd * USD_CHF


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_s: float

    @property
    def cost_chf(self) -> float | None:
        return cost_chf(self.model, self.input_tokens, self.output_tokens)

    def json(self) -> dict:
        return json.loads(self.content)


@dataclass
class UsageMeter:
    """Summiert alle LLM-Aufrufe (thread-sicher, da Agenten parallel laufen)."""
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_chf: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, r: LLMResponse) -> None:
        with self._lock:
            self.calls += 1
            self.input_tokens += r.input_tokens
            self.output_tokens += r.output_tokens
            self.cost_chf += r.cost_chf or 0.0

    def reset(self) -> None:
        with self._lock:
            self.calls = self.input_tokens = self.output_tokens = 0
            self.cost_chf = 0.0

    def as_dict(self) -> dict:
        return {"calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "cost_chf": round(self.cost_chf, 5)}


METER = UsageMeter()
_client = None


def _get_client():
    global _client
    if _client is None:
        provider = os.getenv("LLM_PROVIDER", "openai").split("#")[0].strip()
        if provider != "openai":
            raise NotImplementedError(f"LLM_PROVIDER={provider!r} wird nicht unterstützt (nur openai)")
        from openai import OpenAI
        _client = OpenAI()
    return _client


def chat(messages: list[dict], model: str | None = None, json_mode: bool = False,
         temperature: float = 0.0, max_tokens: int | None = None) -> LLMResponse:
    """Ein Chat-Aufruf. Mit json_mode=True antwortet das Modell mit einem JSON-Objekt."""
    model = model or default_model()
    kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    start = time.perf_counter()
    resp = _get_client().chat.completions.create(**kwargs)
    latency = time.perf_counter() - start
    usage = resp.usage
    result = LLMResponse(
        content=resp.choices[0].message.content or "",
        model=model,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
        latency_s=latency,
    )
    METER.add(result)
    return result
