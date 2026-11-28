"""Interaktives Labeling der SMI-Headlines im Terminal (Richtlinie: nlp/LABELING.md).

Zeigt jede noch ungelabelte Headline einzeln an. Eingabe + Enter:
    p = positive   0 = neutral   n = negative
    d = Zeile löschen (betrifft das Unternehmen nicht)
    o = Artikel im Browser öffnen
    z = letzte Eingabe zurücknehmen
    q = beenden (Fortschritt ist bereits gespeichert)

Gespeichert wird nach jeder Eingabe; ein erneuter Start macht bei der ersten offenen Zeile weiter.

Aufruf:
    python -m nlp.label_tool                     # labeln
    python -m nlp.label_tool --check             # Fortschritt und Verteilung anzeigen
    python -m nlp.label_tool --list [negative]   # alle Labels als Liste (optional nur eine Klasse)
    python -m nlp.label_tool --review            # bestehende Labels bestätigen (Enter) oder ändern
    python -m nlp.label_tool --blind 25          # Stichprobe blind labeln, Übereinstimmung + Kappa
"""
from __future__ import annotations

import argparse
import csv
import random
import webbrowser
from collections import Counter
from pathlib import Path

CSV_PATH = Path("nlp/label_smi_headlines.csv")
BLIND_PATH = Path("nlp/label_check.csv")
SHORT = {"positive": "POS", "neutral": "neu", "negative": "NEG"}
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


def show_list(rows: list[dict], only: str | None) -> None:
    for k, r in enumerate(rows):
        if only and r["label"] != only:
            continue
        print(f"{k:>3} {SHORT.get(r['label'], '---')}  {r['ticker']:<8} {r['text']}")


def review(fields: list[str], rows: list[dict]) -> None:
    """Zeigt jedes Label; Enter = ok, p/0/n = ändern, z = zurück, q = Ende."""
    changed, k = 0, 0
    while k < len(rows):
        r = rows[k]
        print(f"\n[{k + 1}/{len(rows)}] {r['ticker']} · {SHORT.get(r['label'], '---')}")
        print(f"  {r['text']}")
        key = input("  Enter=ok  p / 0 / n=ändern  z=zurück  q=Ende > ").strip().lower()
        if key == "q":
            break
        if key == "z":
            k = max(k - 1, 0)
            continue
        if key in KEYS and KEYS[key] != r["label"]:
            r["label"] = KEYS[key]
            changed += 1
            save(fields, rows)
        elif key and key not in KEYS:
            print("  Ungültige Eingabe.")
            continue
        k += 1
    print(f"\n{changed} Labels geändert.")


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[v] * cb[v] for v in VALID) / n**2
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def blind(rows: list[dict], n: int, seed: int = 42) -> None:
    """Zufällige Stichprobe ohne Anzeige des bestehenden Labels; Ergebnis in nlp/label_check.csv."""
    sample = random.Random(seed).sample(range(len(rows)), min(n, len(rows)))
    mine: list[tuple[int, str]] = []
    for j, k in enumerate(sample, 1):
        r = rows[k]
        print(f"\n[{j}/{len(sample)}] {r['ticker']}")
        print(f"  {r['text']}")
        try:
            while (key := input("  p / 0 / n   q=Ende > ").strip().lstrip("﻿").lower()) not in (*KEYS, "q"):
                print("  Ungültige Eingabe.")
        except (KeyboardInterrupt, EOFError):
            key = "q"   # bisherige Antworten trotzdem auswerten
        if key == "q":
            break
        mine.append((k, KEYS[key]))
    if not mine:
        return
    with open(BLIND_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "text", "label_reference", "label_check"])
        for k, lab in mine:
            w.writerow([k, rows[k]["text"], rows[k]["label"], lab])
    ref = [rows[k]["label"] for k, _ in mine]
    hum = [lab for _, lab in mine]
    agree = sum(x == y for x, y in zip(ref, hum))
    print(f"\nÜbereinstimmung: {agree}/{len(mine)} ({agree / len(mine):.0%}), "
          f"Cohen's Kappa: {cohen_kappa(ref, hum):.2f}  → {BLIND_PATH}")
    for (k, lab), r in zip(mine, ref):
        if lab != r:
            print(f"  {k:>3} Referenz {SHORT[r]} / Kontrolle {SHORT[lab]}: {rows[k]['text']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SMI-Headlines labeln")
    parser.add_argument("--check", action="store_true", help="nur Fortschritt und Verteilung anzeigen")
    parser.add_argument("--list", nargs="?", const="", metavar="LABEL", help="Labels als Liste anzeigen")
    parser.add_argument("--review", action="store_true", help="bestehende Labels bestätigen oder ändern")
    parser.add_argument("--blind", type=int, metavar="N", help="N zufällige Headlines blind labeln")
    args = parser.parse_args()

    fields, rows = load()
    try:
        if args.list is not None:
            show_list(rows, args.list or None)
            return
        if args.blind:
            blind(rows, args.blind)
            return
        if args.review:
            review(fields, rows)
            check(rows)
            return
    except (KeyboardInterrupt, EOFError):
        print()
        return
    if not args.check:
        try:
            label(fields, rows)
        except (KeyboardInterrupt, EOFError):
            print()
    check(rows)


if __name__ == "__main__":
    main()
