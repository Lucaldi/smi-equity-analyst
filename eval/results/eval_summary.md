# Evaluation Single-Agent (A) vs. Multi-Agent (B)

Titel: ABBN.SW, CFR.SW, NESN.SW, NOVN.SW, UBSG.SW · 3 Läufe pro Titel und Variante · Modell gpt-4o-mini

| Kriterium | A Single-Agent | B Multi-Agent | Ziel |
|---|---|---|---|
| H3 Faktentreue (belegte Zahlen) | 83% (45/54) | 100% (68/68) | B > A |
| H4 Konsistenz (gleiches Rating in allen Läufen) | 100% | 100% | ≥ 80 % |
| Qualität (Judge, 1–5) | 3.98 | 3.82 | – |
| – Vollständigkeit / Begründung / Struktur | 4.0 / 4.0 / 3.9 | 4.0 / 4.0 / 3.5 | – |
| H5 Laufzeit Ø / max [s] | 8.6 / 13.4 | 13.6 / 19.6 | < 300 s |
| H5 Kosten Ø / max [CHF] | 0.0003 / 0.0003 | 0.0007 / 0.0007 | < 0.50 CHF |
| LLM-Aufrufe Ø / Tokens Ø | 1.0 / 1264 | 3.0 / 3268 | – |

**H1 Extraktion Geschäftsbericht:** 11/13 Kennzahlen ≤ 2 % Abweichung zu yfinance (85%; Titel mit PDF: NESN.SW; Ziel ≥ 90 %).

Laufzeit A = LLM-Aufruf + Datenbeschaffung (Kennzahlen, News) aus dem Trace von B im selben Lauf.
Judge-Kosten sind in den Kosten nicht enthalten.

## Ratings pro Titel

| Titel | A | B |
|---|---|---|
| ABBN.SW | {'Halten': 3} | {'Halten': 3} |
| CFR.SW | {'Halten': 3} | {'Halten': 3} |
| NESN.SW | {'Halten': 3} | {'Halten': 3} |
| NOVN.SW | {'Halten': 3} | {'Halten': 3} |
| UBSG.SW | {'Halten': 3} | {'Halten': 3} |

## Nicht belegte Zahlen (Beispiele)

- NOVN.SW Lauf 1 A: «9,5» in: …von Novartis stiegen im Vergleich zum Vorjahr um 9,5%, während die operative Marge…
- NOVN.SW Lauf 2 A: «9,5» in: …tze von Novartis sind im Vergleich zum Vorjahr um 9,5% gewachsen, während die opera…
- NOVN.SW Lauf 3 A: «9,5» in: …tze von Novartis sind im Vergleich zum Vorjahr um 9,5% gewachsen, während die opera…
- UBSG.SW Lauf 3 A: «37,5» in: …talquote von 5,57% und die Verschuldungsquote von 37,5% deuten auf eine gesunde fina…
- ABBN.SW Lauf 1 A: «8,5» in: …22 Milliarden USD erzielt, was einem Wachstum von 8,5 % im Vergleich zum Vorjahr en…
- ABBN.SW Lauf 2 A: «8,5» in: …22 Milliarden USD erzielt, was einem Wachstum von 8,5 % im Vergleich zum Vorjahr en… | «0,56» in: …ung ist moderat, mit einer Verschuldungsquote von 0,56. Die Nachrichtenlage ist durc…
- ABBN.SW Lauf 3 A: «8,5» in: …22 Milliarden USD erzielt, was einem Wachstum von 8,5 % im Vergleich zum Vorjahr en… | «0,56» in: …ung ist moderat, mit einer Verschuldungsquote von 0,56. Die Nachrichtenlage ist durc…
