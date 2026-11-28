"""Evaluation: Variante A (Single-Agent) vs. B (Multi-Agent).

Kriterien:
    H1 Extraktion Geschäftsbericht: Anteil Kennzahlen mit Abweichung ≤ 2 % zu yfinance
    H3 Faktentreue: Anteil Zahlen im Memo, die mit den Quelldaten übereinstimmen (eval/fact_check.py)
    H4 Konsistenz: gleiches Rating in allen Läufen pro Titel
    H5 Praxistauglichkeit: Laufzeit und Kosten pro Analyse (Multi-Agent)
    Qualität: LLM-as-a-Judge mit fixem Raster (eval/judge.py)

Variante A erhält pro Lauf dieselben Eingangsdaten wie Variante B im selben Lauf (Rohkennzahlen und
Headlines), damit Unterschiede vom Systemaufbau kommen und nicht von schwankenden News-Treffern.

Aufruf:
    python -m eval.run_eval [--tickers NESN.SW NOVN.SW ...] [--runs 3] [--no-judge]
Resultate in eval/results/ (eval_runs.csv, eval_summary.md/.json, eval_*.png).
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from main import _quiet, load_tickers

RESULTS = Path("eval/results")
DEFAULT_TICKERS = ["NESN.SW", "NOVN.SW", "UBSG.SW", "ABBN.SW", "CFR.SW"]
TARGETS = {"H1": 0.90, "H4": 0.80, "H5_duration_s": 300, "H5_cost_chf": 0.50}


def _data_fetch_seconds(trace_path: str) -> float:
    """Dauer der Datenbeschaffung (Kennzahlen + News) aus dem Trace von Variante B."""
    events = json.loads(Path(trace_path).read_text(encoding="utf-8"))["events"]
    return sum(e.get("duration_s", 0) for e in events
               if e["kind"] == "tool" and e.get("tool") in ("collect_kennzahlen", "fetch_news"))


def run(tickers: list[str], runs: int, judge: bool) -> list[dict]:
    from agents.single_agent import run_single_agent
    from eval.fact_check import allowed_values, check_memo
    from eval.judge import judge_memo
    from graph.graph import run_analysis
    from graph.trace import Tracer, set_tracer
    from tools import llm

    names = load_tickers()
    rows = []
    for ticker in tickers:
        for i in range(runs):
            print(f"{ticker} Lauf {i + 1}/{runs}: B (Multi-Agent) …", flush=True)
            b = run_analysis(ticker, names[ticker], label=f"B{i + 1}")
            f, n = b.get("fundamental"), b.get("news")
            if not f or not n:
                print(f"  übersprungen, Spezialist fehlgeschlagen: {b.get('errors')}")
                continue
            headlines = [it["title"] for it in n["items"]]
            allowed = allowed_values(f["metrics"], f["multiples"], f["scores"], n, headlines)

            print(f"{ticker} Lauf {i + 1}/{runs}: A (Single-Agent) …", flush=True)
            tracer = Tracer(ticker, label=f"A{i + 1}")
            set_tracer(tracer)
            llm.METER.reset()
            start = time.perf_counter()
            memo_a = run_single_agent(ticker, names[ticker], f["metrics"],
                                      [{k: it[k] for k in ("title", "source", "published")} for it in n["items"]])
            a_llm_s = time.perf_counter() - start
            usage_a = llm.METER.as_dict()
            set_tracer(None)
            tracer.save({"usage": usage_a, "memo": memo_a})

            for variant, memo, duration, usage in (
                ("B", b["memo"], b["meta"]["duration_s"], b["meta"]["usage"]),
                ("A", memo_a, a_llm_s + _data_fetch_seconds(b["meta"]["trace_path"]), usage_a),
            ):
                fc = check_memo(memo, allowed)
                row = {"ticker": ticker, "run": i + 1, "variant": variant, "rating": memo.get("rating"),
                       "conviction": memo.get("conviction"), "numbers": fc["numbers"],
                       "supported": fc["supported"], "faithfulness": fc["faithfulness"],
                       "unsupported": "; ".join(fc["unsupported"]),
                       "unsupported_context": " | ".join(fc["unsupported_context"]), "duration_s": round(duration, 2),
                       "llm_calls": usage["calls"], "tokens": usage["input_tokens"] + usage["output_tokens"],
                       "cost_chf": usage["cost_chf"]}
                if judge:
                    j = judge_memo(memo)
                    row.update({f"judge_{k}": j[k] for k in ("completeness", "reasoning", "structure", "mean")})
                if variant == "B" and i == 0 and f.get("validation"):
                    checked = [v for v in f["validation"].values() if v["ok"] is not None]
                    row["h1_checked"], row["h1_ok"] = len(checked), sum(v["ok"] for v in checked)
                rows.append(row)
                print(f"  {variant}: Rating {row['rating']}, Faktentreue {fc['supported']}/{fc['numbers']}, "
                      f"{row['duration_s']} s, {row['cost_chf']:.4f} CHF", flush=True)
    return rows


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def summarize(rows: list[dict]) -> dict:
    out: dict = {"variants": {}}
    for variant in ("A", "B"):
        vr = [r for r in rows if r["variant"] == variant]
        numbers, supported = sum(r["numbers"] for r in vr), sum(r["supported"] for r in vr)
        by_ticker: dict[str, list] = {}
        for r in vr:
            by_ticker.setdefault(r["ticker"], []).append(r["rating"])
        consistent = {t: len(set(rs)) == 1 and None not in rs for t, rs in by_ticker.items()}
        out["variants"][variant] = {
            "analyses": len(vr),
            "faithfulness": supported / numbers if numbers else None,
            "numbers": numbers, "supported": supported,
            "consistency": sum(consistent.values()) / len(consistent) if consistent else None,
            "ratings": {t: dict(Counter(rs)) for t, rs in by_ticker.items()},
            "duration_mean_s": _mean(r["duration_s"] for r in vr),
            "duration_max_s": max((r["duration_s"] for r in vr), default=None),
            "cost_mean_chf": _mean(r["cost_chf"] for r in vr),
            "cost_max_chf": max((r["cost_chf"] for r in vr), default=None),
            "tokens_mean": _mean(r["tokens"] for r in vr),
            "llm_calls_mean": _mean(r["llm_calls"] for r in vr),
            "judge_mean": _mean(r.get("judge_mean") for r in vr),
            **{f"judge_{c}": _mean(r.get(f"judge_{c}") for r in vr) for c in ("completeness", "reasoning", "structure")},
        }
    h1 = [r for r in rows if r.get("h1_checked")]
    checked, ok = sum(r["h1_checked"] for r in h1), sum(r["h1_ok"] for r in h1)
    out["H1"] = {"tickers": [r["ticker"] for r in h1], "checked": checked, "ok": ok,
                 "share": ok / checked if checked else None}
    return out


def write(rows: list[dict], summary: dict, runs: int) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(RESULTS / "eval_runs.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (RESULTS / "eval_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    a, b = summary["variants"]["A"], summary["variants"]["B"]

    def pct(v):
        return "–" if v is None else f"{v:.0%}"

    def num(v, d=2):
        return "–" if v is None else f"{v:.{d}f}"

    h1 = summary["H1"]
    tickers = sorted({r["ticker"] for r in rows})
    lines = [
        "# Evaluation Single-Agent (A) vs. Multi-Agent (B)", "",
        f"Titel: {', '.join(tickers)} · {runs} Läufe pro Titel und Variante · Modell gpt-4o-mini", "",
        "| Kriterium | A Single-Agent | B Multi-Agent | Ziel |", "|---|---|---|---|",
        f"| H3 Faktentreue (belegte Zahlen) | {pct(a['faithfulness'])} ({a['supported']}/{a['numbers']}) | "
        f"{pct(b['faithfulness'])} ({b['supported']}/{b['numbers']}) | B > A |",
        f"| H4 Konsistenz (gleiches Rating in allen Läufen) | {pct(a['consistency'])} | {pct(b['consistency'])} | ≥ 80 % |",
        f"| Qualität (Judge, 1–5) | {num(a['judge_mean'], 2)} | {num(b['judge_mean'], 2)} | – |",
        f"| – Vollständigkeit / Begründung / Struktur | {num(a['judge_completeness'], 1)} / {num(a['judge_reasoning'], 1)} / "
        f"{num(a['judge_structure'], 1)} | {num(b['judge_completeness'], 1)} / {num(b['judge_reasoning'], 1)} / "
        f"{num(b['judge_structure'], 1)} | – |",
        f"| H5 Laufzeit Ø / max [s] | {num(a['duration_mean_s'], 1)} / {num(a['duration_max_s'], 1)} | "
        f"{num(b['duration_mean_s'], 1)} / {num(b['duration_max_s'], 1)} | < 300 s |",
        f"| H5 Kosten Ø / max [CHF] | {num(a['cost_mean_chf'], 4)} / {num(a['cost_max_chf'], 4)} | "
        f"{num(b['cost_mean_chf'], 4)} / {num(b['cost_max_chf'], 4)} | < 0.50 CHF |",
        f"| LLM-Aufrufe Ø / Tokens Ø | {num(a['llm_calls_mean'], 1)} / {num(a['tokens_mean'], 0)} | "
        f"{num(b['llm_calls_mean'], 1)} / {num(b['tokens_mean'], 0)} | – |",
        "",
        f"**H1 Extraktion Geschäftsbericht:** {h1['ok']}/{h1['checked']} Kennzahlen ≤ 2 % Abweichung zu yfinance "
        f"({pct(h1['share'])}; Titel mit PDF: {', '.join(h1['tickers']) or 'keine'}; Ziel ≥ 90 %).", "",
        "Laufzeit A = LLM-Aufruf + Datenbeschaffung (Kennzahlen, News) aus dem Trace von B im selben Lauf.",
        "Judge-Kosten sind in den Kosten nicht enthalten.", "",
        "## Ratings pro Titel", "", "| Titel | A | B |", "|---|---|---|",
    ]
    for t in tickers:
        lines.append(f"| {t} | {a['ratings'].get(t, {})} | {b['ratings'].get(t, {})} |")
    lines += ["", "## Nicht belegte Zahlen (Beispiele)", ""]
    for r in rows:
        if r["unsupported"]:
            lines.append(f"- {r['ticker']} Lauf {r['run']} {r['variant']}: {r['unsupported_context']}")
    (RESULTS / "eval_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _plot(summary)
    print(f"Resultate → {RESULTS}/eval_summary.md")


def _plot(summary: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a, b = summary["variants"]["A"], summary["variants"]["B"]
    metrics = [("Faktentreue", "faithfulness", 1), ("Konsistenz", "consistency", 1), ("Qualität (Judge/5)", "judge_mean", 5)]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, (title, key, scale) in zip(axes, metrics):
        vals = [(a[key] or 0) / scale, (b[key] or 0) / scale]
        bars = ax.bar(["A Single", "B Multi"], vals, color=["#9aa5b1", "#2f6db5"])
        ax.set_ylim(0, 1.05)
        ax.set_title(title)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v * scale:.2f}" if scale > 1 else f"{v:.0%}",
                    ha="center")
    fig.tight_layout()
    fig.savefig(RESULTS / "eval_comparison.png", dpi=150)
    plt.close(fig)


def main() -> None:
    _quiet()
    parser = argparse.ArgumentParser(description="Evaluation Single- vs. Multi-Agent")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--no-judge", action="store_true", help="ohne LLM-as-a-Judge")
    args = parser.parse_args()

    rows = run(args.tickers, args.runs, judge=not args.no_judge)
    if not rows:
        raise SystemExit("Keine Resultate")
    write(rows, summarize(rows), args.runs)


if __name__ == "__main__":
    main()
