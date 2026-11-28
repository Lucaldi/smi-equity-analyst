"""Automatischer Faktencheck (H3): Jede Zahl im Memo wird gegen die Quelldaten geprüft.

Belegt ist eine Zahl, wenn sie (im Betrag) einem Wert der Quelldaten entspricht, unter
Berücksichtigung der Rundung, mit der sie im Memo steht (z. B. «11.4 Mrd.» ↔ 11.38).
Quelldaten: berechnete Kennzahlen und Multiples (Python), Rohkennzahlen, Scores, Sentiment-Score
und -Zählung, Zahlen aus den Headlines sowie Geschäftsjahre. Beide Varianten (A und B) werden gegen
dieselben, in Python berechneten Werte geprüft.
"""
from __future__ import annotations

import re

from agents.facts import AMOUNT_KEYS, RATIO_KEYS, fact_values

MEMO_FIELDS = ("summary", "fundamental_view", "news_view", "conflicts", "risks")
NUMBER = re.compile(r"(?<![\w.])[-−–]?\d{1,3}(?:['’ ]\d{3})+(?:[.,]\d+)?(?![\w])|(?<![\w.])[-−–]?\d+(?:[.,]\d+)?")
UNIT_AFTER = re.compile(r"^\s*(%|prozent|mrd\.?|milliarden|mio\.?|millionen|bn|billion|x\b|mal\b)", re.IGNORECASE)


def memo_text(memo: dict) -> str:
    parts = []
    for field in MEMO_FIELDS:
        value = memo.get(field)
        parts.extend(value if isinstance(value, list) else [value or ""])
    return "\n".join(str(p) for p in parts)


def extract_numbers(text: str) -> list[dict]:
    """Zahlen mit Rohtext, Wert (in Mrd., falls als Mio./absolut angegeben) und Nachkommastellen."""
    found = []
    for m in NUMBER.finditer(text):
        raw = m.group(0)
        s = re.sub(r"['’ ]", "", raw).replace("−", "-").replace("–", "-").replace(",", ".")
        try:
            value = abs(float(s))
        except ValueError:
            continue
        decimals = len(s.split(".")[1]) if "." in s else 0
        unit_m = UNIT_AFTER.match(text[m.end():m.end() + 14])
        unit = unit_m.group(1).lower() if unit_m else ""
        if unit.startswith(("mio", "million")):
            value, decimals = value / 1000, decimals + 3
        elif not unit and value >= 1e6:          # ausgeschriebene Beträge → Mrd.
            value, decimals = value / 1e9, 2
        context = " ".join(text[max(0, m.start() - 50):m.end() + 30].split())
        found.append({"raw": raw, "value": value, "decimals": decimals, "unit": unit, "context": context})
    return found


def allowed_values(metrics: dict, multiples: dict, scores: dict | None = None,
                   news: dict | None = None, headlines: list[str] | None = None) -> list[float]:
    """Alle Werte, auf die sich ein Memo stützen darf (Beträge in Mrd., Quoten in %)."""
    values: list[float] = []
    for _, v, _ in fact_values(metrics, multiples).values():
        if v is not None:
            values.append(abs(v))
    for key, v in multiples.items():                    # ungerundet (das LLM kann genauer zitieren)
        if v is None:
            continue
        if key in RATIO_KEYS:
            values.append(abs(v) * 100)
        elif key in AMOUNT_KEYS:
            values.append(abs(v) / 1e9)
        else:
            values.append(abs(v))
    for key, v in metrics.items():                      # Rohkennzahlen in der Form, die Variante A sieht
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v is not None:
            values.append(abs(v) / 1e9 if abs(v) >= 1e6 else abs(v))
    # einfache Verhältniszahlen, die Variante A häufig selbst bildet (als Faktor und in %)
    def ratio(a, b):
        return None if metrics.get(a) is None or not metrics.get(b) else metrics[a] / metrics[b]
    for r in (ratio("total_debt", "total_equity"), ratio("total_debt", "total_assets"),
              ratio("total_liabilities", "total_assets"), ratio("total_liabilities", "total_equity")):
        if r is not None:
            values += [abs(r), abs(r) * 100]
    for v in (scores or {}).values():
        if v is not None:
            values.append(abs(v))
    if news:
        if news.get("sentiment_score") is not None:
            values.append(abs(news["sentiment_score"]))
        values.extend(news.get("counts", {}).values())
    for h in headlines or []:
        values.extend(n["value"] for n in extract_numbers(h))
    fy = metrics.get("fiscal_year")
    if fy:
        values += [fy, fy - 1, fy + 1]
    values += [90, 0, 1, 2, 3, 4, 5, 6.5, 10]           # Zeitraum, Skalen, Rating-Schwellen aus dem Prompt
    return values


def is_supported(number: dict, allowed: list[float]) -> bool:
    tolerance = 0.5 * 10 ** (-number["decimals"]) + 1e-9   # Rundung, mit der die Zahl geschrieben ist
    x = number["value"]
    return any(abs(x - v) <= tolerance or (v and abs(x - v) / abs(v) <= 0.005) for v in allowed)


def check_memo(memo: dict, allowed: list[float]) -> dict:
    numbers = extract_numbers(memo_text(memo))
    missing = [n for n in numbers if not is_supported(n, allowed)]
    unsupported = [n["raw"] + (f" {n['unit']}" if n["unit"] else "") for n in missing]
    total = len(numbers)
    return {"numbers": total, "supported": total - len(unsupported), "unsupported": unsupported,
            "unsupported_context": [f"«{n['raw']}» in: …{n['context']}…" for n in missing],
            "faithfulness": (total - len(unsupported)) / total if total else None}
