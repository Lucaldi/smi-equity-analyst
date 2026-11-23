"""CLI-Einstieg: Analyse für einen oder alle SMI-Titel starten."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv


CONFIG = Path(__file__).parent / "config" / "smi_tickers.yaml"


def load_tickers(path: Path = CONFIG) -> dict[str, str]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["tickers"]


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="SMI Equity Analyst")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticker", help="z. B. NESN.SW")
    group.add_argument("--all", action="store_true", help="alle SMI-Titel")
    parser.add_argument("--trace", action="store_true", help="Agentenschritte im Terminal anzeigen")
    args = parser.parse_args()

    tickers = load_tickers()
    selected = list(tickers) if args.all else [args.ticker]

    from graph.graph import run_analysis
    for t in selected:
        print(f"→ {t} ({tickers.get(t, '?')})")
        run_analysis(t)


if __name__ == "__main__":
    main()
