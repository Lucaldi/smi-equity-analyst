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

Metriken: Macro-F1 (Mittel und Streuung über die Läufe, + Confusion Matrix), Kosten und Latenz
pro Headline, Konsistenz (Anteil Headlines mit identischem Label über alle Läufe).

Vorhersagen werden über tools.sentiment_classifier als JSON in data/cache/ gecacht.
Resultate landen in eval/results/sentiment/.

Aufruf:
    python -m nlp.compare_sentiment [--variants V1 V2 V3] [--runs 3]
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from tools.sentiment_classifier import classify_detailed

LABELS_CSV = Path("nlp/label_smi_headlines.csv")
RESULTS_DIR = Path("eval/results/sentiment")
LABELS = ["positive", "neutral", "negative"]


@dataclass(frozen=True)
class Variant:
    name: str
    description: str
    backend: str               # finbert | llm
    few_shot: bool = False


VARIANTS: dict[str, Variant] = {
    "V1": Variant("V1", "FinBERT (ProsusAI/finbert)", "finbert"),
    "V2": Variant("V2", "OpenAI Zero-shot", "llm"),
    "V3": Variant("V3", "OpenAI Few-shot", "llm", few_shot=True),
}


def load_testset(path: Path = LABELS_CSV) -> list[dict]:
    """Lädt die gelabelten Headlines und prüft, dass nur gültige Labels vorkommen."""
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    invalid = [r["text"] for r in rows if r["label"] not in LABELS]
    if invalid:
        raise ValueError(f"{len(invalid)} Zeilen ohne gültiges Label, z. B.: {invalid[0]!r}")
    return rows


def _macro_f1(gold: list[str], pred: list[str | None]) -> float:
    # None (ungültige Modellantwort) zählt als falsch
    return f1_score(gold, [p or "invalid" for p in pred], labels=LABELS, average="macro", zero_division=0)


def evaluate_variant(variant: Variant, rows: list[dict], runs: int) -> dict:
    """Klassifiziert alle Headlines `runs`-mal und berechnet die Kennzahlen für H2."""
    texts = [r["text"] for r in rows]
    gold = [r["label"] for r in rows]
    all_runs = []
    for run in range(runs):
        preds = classify_detailed(texts, backend=variant.backend, few_shot=variant.few_shot, run=run)
        n_cached = sum(p["cached"] for p in preds)
        print(f"  {variant.name} Lauf {run + 1}/{runs}: {len(preds)} Headlines ({n_cached} aus Cache)")
        all_runs.append(preds)

    labels_per_run = [[p["label"] for p in preds] for preds in all_runs]
    f1s = [_macro_f1(gold, labels) for labels in labels_per_run]
    accs = [accuracy_score(gold, [l or "invalid" for l in labels]) for labels in labels_per_run]
    consistent = sum(len({run[i] for run in labels_per_run}) == 1 for i in range(len(texts)))
    latencies = [p["latency_s"] for preds in all_runs for p in preds]
    costs = [p["cost_chf"] for preds in all_runs for p in preds if p["cost_chf"] is not None]
    first = labels_per_run[0]

    return {
        "variant": variant.name,
        "description": variant.description,
        "n": len(texts),
        "runs": runs,
        "macro_f1_mean": statistics.mean(f1s),
        "macro_f1_std": statistics.stdev(f1s) if runs > 1 else 0.0,
        "macro_f1_runs": f1s,
        "accuracy_mean": statistics.mean(accs),
        "consistency": consistent / len(texts),
        "latency_mean_s": statistics.mean(latencies),
        "latency_median_s": statistics.median(latencies),
        "cost_per_headline_chf": statistics.mean(costs) if costs else None,
        "invalid_answers": sum(l is None for labels in labels_per_run for l in labels),
        "f1_per_class": dict(zip(LABELS, f1_score(gold, [l or "invalid" for l in first], labels=LABELS,
                                                   average=None, zero_division=0).tolist())),
        "confusion_matrix": confusion_matrix(gold, [l or "invalid" for l in first], labels=LABELS).tolist(),
        "predictions": first,
    }


def write_results(results: list[dict], rows: list[dict], out_dir: Path = RESULTS_DIR) -> None:
    """Schreibt Vergleichstabelle (CSV/Markdown/JSON), Vorhersagen und Confusion Matrices."""
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_cols = ["variant", "description", "n", "runs", "macro_f1_mean", "macro_f1_std", "accuracy_mean",
                    "consistency", "latency_mean_s", "latency_median_s", "cost_per_headline_chf", "invalid_answers"]
    with open(out_dir / "summary.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=summary_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    def fmt(v, digits=3):
        return "–" if v is None else f"{v:.{digits}f}"

    lines = [
        "# H2 – Sentiment-Vergleich", "",
        f"Testset: {len(rows)} SMI-Headlines (`nlp/label_smi_headlines.csv`), Läufe pro Variante: {results[0]['runs']}.", "",
        "| Variante | Modell | Macro-F1 (± Std) | Accuracy | Konsistenz | Latenz Ø / Median [s] | Kosten pro Headline [CHF] |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['variant']} | {r['description']} | {fmt(r['macro_f1_mean'])} ± {fmt(r['macro_f1_std'])} | "
            f"{fmt(r['accuracy_mean'])} | {r['consistency']:.0%} | {fmt(r['latency_mean_s'])} / "
            f"{fmt(r['latency_median_s'])} | {fmt(r['cost_per_headline_chf'], 6)} |")
    lines += ["", "F1 pro Klasse (Lauf 1):", "",
              "| Variante | positive | neutral | negative |", "|---|---|---|---|"]
    for r in results:
        c = r["f1_per_class"]
        lines.append(f"| {r['variant']} | {c['positive']:.3f} | {c['neutral']:.3f} | {c['negative']:.3f} |")
    lines += ["", "Confusion Matrix (Zeilen = Label, Spalten = Vorhersage; Reihenfolge positive, neutral, negative):", ""]
    for r in results:
        lines.append(f"- {r['variant']}: `{r['confusion_matrix']}`")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (out_dir / "summary.json").write_text(
        json.dumps([{k: v for k, v in r.items() if k != "predictions"} for r in results], indent=2), encoding="utf-8")

    with open(out_dir / "predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "ticker", "label", *[r["variant"] for r in results]])
        for i, row in enumerate(rows):
            w.writerow([row["text"], row["ticker"], row["label"], *[r["predictions"][i] for r in results]])

    _plot_confusion(results, out_dir)
    print(f"Resultate → {out_dir}/summary.md")


def _plot_confusion(results: list[dict], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(results), figsize=(4.2 * len(results), 4), squeeze=False)
    for ax, r in zip(axes[0], results):
        cm = r["confusion_matrix"]
        ax.imshow(cm, cmap="Blues")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, cm[i][j], ha="center", va="center",
                        color="white" if cm[i][j] > max(map(max, cm)) / 2 else "black")
        ax.set_xticks(range(3), LABELS)
        ax.set_yticks(range(3), LABELS)
        ax.set_xlabel("Vorhersage")
        ax.set_ylabel("Label")
        ax.set_title(f"{r['variant']} – Macro-F1 {r['macro_f1_mean']:.2f}")
    fig.tight_layout()
    fig.savefig(out_dir / "confusion_matrices.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentiment-Vergleich FinBERT vs. OpenAI (H2)")
    parser.add_argument("--variants", nargs="+", default=["V1", "V2"], choices=list(VARIANTS))
    parser.add_argument("--runs", type=int, default=3, help="Wiederholungen für die Konsistenz")
    args = parser.parse_args()

    rows = load_testset()
    results = [evaluate_variant(VARIANTS[v], rows, args.runs) for v in args.variants]
    write_results(results, rows)


if __name__ == "__main__":
    main()
