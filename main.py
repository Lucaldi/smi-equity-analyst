"""CLI-Einstieg: Analyse für einen oder alle SMI-Titel starten."""
from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings
from pathlib import Path

import yaml
from dotenv import load_dotenv

CONFIG = Path(__file__).parent / "config" / "smi_tickers.yaml"


def load_tickers(path: Path = CONFIG) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["tickers"]


def _quiet() -> None:
    """Warnungen von Drittbibliotheken (HF-Symlinks, Fortschrittsbalken) im Terminal unterdrücken."""
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    for name in ("docling", "httpx", "yfinance", "transformers", "RapidOCR"):
        logging.getLogger(name).setLevel(logging.ERROR)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    load_dotenv(Path(__file__).parent / ".env")
    _quiet()
    parser = argparse.ArgumentParser(description="SMI Equity Analyst")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker", help="z. B. NESN.SW")
    group.add_argument("--all", action="store_true", help="alle SMI-Titel")
    parser.add_argument("--trace", action="store_true", help="Agentenschritte im Terminal anzeigen")
    args = parser.parse_args()

    tickers = load_tickers()
    if args.ticker and args.ticker not in tickers:
        parser.error(f"{args.ticker} ist nicht in config/smi_tickers.yaml")
    selected = list(tickers) if args.all else [args.ticker]

    from graph.graph import run_analysis
    for t in selected:
        print(f"→ {t} ({tickers[t]})")
        result = run_analysis(t, tickers[t], trace=args.trace)
        print()
        print(result["memo_markdown"])
        meta = result["meta"]
        print(f"Dauer {meta['duration_s']} s · {meta['usage']['calls']} LLM-Aufrufe · "
              f"Kosten {meta['usage']['cost_chf']:.4f} CHF")
        print(f"Memo: {meta['memo_path']} · Trace: {meta['trace_path']}\n")


if __name__ == "__main__":
    main()
