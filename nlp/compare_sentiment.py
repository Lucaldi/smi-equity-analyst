"""Vergleich der Sentiment-Varianten für H2 (kein Training, nur Inferenz, lokal auf CPU).

Varianten:
    V1 – FinBERT (ProsusAI/finbert), vortrainiert
    V2 – OpenAI Zero-shot
    V3 – OpenAI Few-shot (optional)
Claude ist aus Kostengründen nicht im Vergleich.

Testset: 146 gelabelte SMI-Headlines in nlp/label_smi_headlines.csv
(Spalten: text, ticker, date, source, url, label; gesammelt mit nlp/collect_headlines.py,
gelabelt gemäss nlp/LABELING.md). Financial PhraseBank wird nicht verwendet,
weil FinBERT darauf trainiert wurde (Data Leakage).

Metriken: Macro-F1 (+ Confusion Matrix), Kosten und Latenz pro Headline, Konsistenz
(Anteil Headlines mit identischem Label über wiederholte Läufe).

Vorhersagen werden über tools.sentiment_classifier als JSON in data/cache/ gecacht.
Resultate landen in eval/results/sentiment/.

Aufruf:
    python -m nlp.compare_sentiment [--variants V1 V2] [--runs 3]
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

LABELS_CSV = Path("nlp/label_smi_headlines.csv")
RESULTS_DIR = Path("eval/results/sentiment")
LABELS = ["positive", "neutral", "negative"]


@dataclass(frozen=True)
class Variant:
    name: str
    backend: str               # finbert | llm
    provider: str | None       # openai (nur für llm)
    few_shot: bool = False


VARIANTS: dict[str, Variant] = {
    "V1": Variant("V1", "finbert", None),
    "V2": Variant("V2", "llm", "openai"),
    "V3": Variant("V3", "llm", "openai", few_shot=True),   # optional
}


def load_testset(path: Path = LABELS_CSV) -> list[dict]:
    """Lädt die gelabelten Headlines und prüft, dass nur gültige Labels vorkommen."""
    raise NotImplementedError


def evaluate_variant(variant: Variant, rows: list[dict], runs: int) -> dict:
    """Klassifiziert alle Headlines `runs`-mal und berechnet:
    macro_f1, confusion_matrix, cost_per_headline_chf, latency_per_headline_s, consistency.
    """
    raise NotImplementedError


def write_results(results: list[dict], out_dir: Path = RESULTS_DIR) -> None:
    """Schreibt Vergleichstabelle (CSV/Markdown) und Confusion Matrices nach eval/results/."""
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentiment-Vergleich FinBERT vs. OpenAI (H2)")
    parser.add_argument("--variants", nargs="+", default=["V1", "V2"], choices=list(VARIANTS))
    parser.add_argument("--runs", type=int, default=3, help="Wiederholungen für die Konsistenz")
    args = parser.parse_args()

    rows = load_testset()
    results = [evaluate_variant(VARIANTS[v], rows, args.runs) for v in args.variants]
    write_results(results)


if __name__ == "__main__":
    main()
