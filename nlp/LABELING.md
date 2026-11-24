# Labeling-Richtlinie SMI-Headlines

Testset für H2 (`nlp/label_smi_headlines.csv`). Gelabelt wird **von Hand**, nicht mit FinBERT
oder einem LLM: Diese Modelle werden auf dem Set verglichen. Würden sie die Labels setzen,
wäre ihre Treffsicherheit zirkulär (das labelnde Modell hätte automatisch einen Vorteil).

## Ablauf
```bash
python -m nlp.label_tool            # p / 0 / n, d = löschen, o = Link, z = zurück, q = Ende
python -m nlp.label_tool --check    # Fortschritt und Verteilung
```
Gespeichert wird nach jeder Eingabe; ein erneuter Start macht bei der ersten offenen Zeile weiter.

## Frage pro Headline
> Wie wirkt die Meldung voraussichtlich auf den Aktienkurs **des genannten Tickers**?

| Label | Wann |
|---|---|
| `positive` | klar gute Nachricht für das Unternehmen: Gewinn/Umsatz über Erwartung, Upgrade, höheres Kursziel, Zulassung, attraktive Übernahme, Prognose erhöht |
| `negative` | klar schlechte Nachricht: Gewinnwarnung, Downgrade, Klage/Busse, Rückruf, Stellenabbau wegen Schwäche, Prognose gesenkt, CEO-Abgang unter Druck |
| `neutral` | reine Information ohne klare Richtung: Termine, Personalien ohne Wertung, Marktberichte, gemischte Meldungen, Meldung betrifft das Unternehmen kaum |

## Regeln
- Nur die Headline bewerten, nicht den Artikel (das Modell sieht auch nur die Headline).
  Der Link dient nur zur Klärung, worum es geht.
- Im Zweifel `neutral`.
- Perspektive ist der Aktionär des Tickers in der Spalte `ticker`.
- Irrelevante Zeilen (Werbung, keine Unternehmensnachricht) löschen statt labeln.
- Labels nur in Kleinbuchstaben: `positive`, `neutral`, `negative`.

Optional für den Bericht: 20–30 Zeilen nach einigen Tagen ein zweites Mal labeln und die
Übereinstimmung angeben (Selbstkonsistenz als Obergrenze für die Modelle).
