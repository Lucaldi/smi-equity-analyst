# Labeling-Richtlinie SMI-Headlines

Testset für H2 (`nlp/label_smi_headlines.csv`). Die Labels werden nicht mit einem der
verglichenen Modelle (FinBERT, OpenAI) gesetzt, sonst wäre deren Treffsicherheit zirkulär.

## Ablauf
```bash
python -m nlp.label_tool            # p / 0 / n, d = löschen, o = Link, z = zurück, q = Ende
python -m nlp.label_tool --check    # Fortschritt und Verteilung

# Kontrolle bestehender Labels
python -m nlp.label_tool --list [negative]   # Liste zum Überfliegen
python -m nlp.label_tool --review            # Enter = ok, p / 0 / n = ändern
python -m nlp.label_tool --blind 25          # Stichprobe blind neu labeln → Übereinstimmung,
                                             # Cohen's Kappa, gespeichert in nlp/label_check.csv
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
