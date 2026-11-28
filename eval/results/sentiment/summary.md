# H2 – Sentiment-Vergleich

Testset: 146 SMI-Headlines (`nlp/label_smi_headlines.csv`), Läufe pro Variante: 3.

| Variante | Modell | Macro-F1 (± Std) | Accuracy | Konsistenz | Latenz Ø / Median [s] | Kosten pro Headline [CHF] |
|---|---|---|---|---|---|---|
| V1 | FinBERT (ProsusAI/finbert) | 0.747 ± 0.000 | 0.740 | 100% | 0.023 / 0.022 | 0.000000 |
| V2 | OpenAI Zero-shot | 0.789 ± 0.004 | 0.772 | 98% | 0.732 / 0.656 | 0.000024 |
| V3 | OpenAI Few-shot | 0.760 ± 0.013 | 0.740 | 97% | 0.676 / 0.656 | 0.000044 |

F1 pro Klasse (Lauf 1):

| Variante | positive | neutral | negative |
|---|---|---|---|
| V1 | 0.769 | 0.648 | 0.825 |
| V2 | 0.757 | 0.703 | 0.914 |
| V3 | 0.730 | 0.660 | 0.930 |

Confusion Matrix (Zeilen = Label, Spalten = Vorhersage; Reihenfolge positive, neutral, negative):

- V1: `[[40, 4, 0], [20, 35, 11], [0, 3, 33]]`
- V2: `[[42, 2, 0], [25, 39, 2], [0, 4, 32]]`
- V3: `[[42, 2, 0], [29, 35, 2], [0, 3, 33]]`
