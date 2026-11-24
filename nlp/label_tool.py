"""Interaktives Labeling der SMI-Headlines im Terminal (Richtlinie: nlp/LABELING.md).

Zeigt jede noch ungelabelte Headline einzeln an. Eingabe + Enter:
    p = positive   0 = neutral   n = negative
    d = Zeile löschen (betrifft das Unternehmen nicht)
    o = Artikel im Browser öffnen
    z = letzte Eingabe zurücknehmen
    q = beenden (Fortschritt ist bereits gespeichert)

Gespeichert wird nach jeder Eingabe; ein erneuter Start macht bei der ersten offenen Zeile weiter.

Aufruf:
    python -m nlp.label_tool            # labeln
    python -m nlp.label_tool --check    # Fortschritt und Verteilung anzeigen
"""
from __future__ import annotations

import argparse
import csv
import webbrowser
from collections import Counter
from pathlib import Path

CSV_PATH = Path("nlp/label_smi_headlines.csv")
KEYS = {"p": "positive", "0": "neutral", "n": "negative"}
VALID = set(KEYS.values())


def load() -> tuple[list[str], list[dict]]:
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def save(fields: list[str], rows: list[dict]) -> None:
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def check(rows: list[dict]) -> None:
    labels = Counter(r["label"].strip() for r in rows)
    invalid = [r["text"] for r in rows if r["label"].strip() and r["label"].strip() not in VALID]
    done = sum(labels[v] for v in VALID)
    print(f"{done}/{len(rows)} gelabelt, {labels['']} offen")
    for v in sorted(VALID):
        share = labels[v] / done if done else 0
        print(f"  {v:<9} {labels[v]:>4}  ({share:.0%})")
    if invalid:
        print(f"Ungültige Labels ({len(invalid)}):")
        for t in invalid:
            print(f"  - {t}")


def label(fields: list[str], rows: list[dict]) -> None:
    history: list[tuple[int, dict, str]] = []   # (Index, Zeile, "" oder "deleted")
    while True:
        open_idx = [k for k, r in enumerate(rows) if not r["label"].strip()]
        if not open_idx:
            print("Alles gelabelt.")
            return
        i = open_idx[0]
        r = rows[i]
        print(f"\n[{len(rows) - len(open_idx) + 1}/{len(rows)}] {r['ticker']} · {r['date']} · {r['source']}")
        print(f"  {r['text']}")
        key = input("  p / 0 / n   d=löschen  o=Link  z=zurück  q=Ende > ").strip().lower()

        if key in KEYS:
            history.append((i, r, ""))
            r["label"] = KEYS[key]
        elif key == "d":
            history.append((i, r, "deleted"))
            rows.pop(i)
        elif key == "o":
            webbrowser.open(r["url"])
            continue
        elif key == "z":
            if not history:
                print("  Nichts zurückzunehmen.")
                continue
            idx, row, prev = history.pop()
            if prev == "deleted":
                rows.insert(idx, row)
            row["label"] = ""
        elif key == "q":
            return
        else:
            print("  Ungültige Eingabe.")
            continue
        save(fields, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="SMI-Headlines labeln")
    parser.add_argument("--check", action="store_true", help="nur Fortschritt und Verteilung anzeigen")
    args = parser.parse_args()

    fields, rows = load()
    if not args.check:
        try:
            label(fields, rows)
        except (KeyboardInterrupt, EOFError):
            print()
    check(rows)


if __name__ == "__main__":
    main()
