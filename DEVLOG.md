# Entwicklungsprotokoll

Ein Eintrag pro Schritt. Grundlage für die Kapitel «Lösungsansatz» und «Reflexion».

---

## Schritt 0 – Setup (23.11.2026)
- **Ziel:** Repo, Struktur, Entwicklungsumgebung (VS Code)
- **Entscheid:** Struktur gemäss SCOPE.md; Docling für PDF-Tabellen; Start mit einem Titel (Nestlé)
- **Ergebnis:** Repo auf GitHub angelegt (Initial commit), Grundstruktur mit Modul-Skeletten
  (`agents/`, `tools/`, `graph/`, `eval/`, `nlp/`), Config (`smi_tickers.yaml`, `ir_sources.yaml`),
  `.gitignore`, `.env.example`, `pytest.ini` und Config-Test. Sentiment-Plan überarbeitet:
  kein Training/Fine-tuning; Standard im News-Agent ist ein LLM via API (OpenAI oder Claude,
  wählbar über `.env`). Vergleich für H2: V1 FinBERT (`ProsusAI/finbert`, nur Inferenz),
  V2 OpenAI Zero-shot, V3 Claude Zero-shot, V4 optional Few-shot. Testset: ca. 150 eigene
  SMI-Headlines statt Financial PhraseBank (FinBERT darauf trainiert → Data Leakage).
  Alles läuft lokal auf CPU; Docling-Ergebnisse und Sentiment-Vorhersagen als JSON-Cache in
  `data/cache/`. `nlp/train_sentiment.ipynb` (Colab) durch `nlp/compare_sentiment.py` ersetzt.
- **Probleme:** Ursprünglicher Plan (TF-IDF-Baseline, FinBERT fine-getuned auf Financial
  PhraseBank, Training in Colab) zu aufwendig für den Zeitrahmen und methodisch heikel
  (Testdaten = FinBERT-Trainingsdaten).

## Schritt 1 – News-Quellen und Sentiment-Testset (24.11.2026)
- **Ziel:** ca. 150 SMI-Headlines als Testset für H2, aus seriösen Quellen
- **Entscheid:** News aus yfinance (ohne Bewertungs-Blogs) plus Tavily auf einer festen Liste
  englischsprachiger Qualitätsmedien. Dieselbe Funktion (`tools/news_fetcher.fetch_news`) für
  News-Agent und Testset. Labeling nicht mit einem der verglichenen Modelle (Zirkelschluss).
- **Ergebnis:** 146 Headlines aus 33 Quellen in `nlp/label_smi_headlines.csv`, alle 20 Titel
  vertreten. Labeling-Werkzeug `nlp/label_tool.py`, Richtlinie `nlp/LABELING.md`.
  8 Offline-Tests für den News-Fetcher.
- **Probleme:**
  - yfinance allein: viele Headlines zu fremden Firmen (z. B. bei Givaudan alle) und 28 %
    Simply-Wall-St.-Teaser. Gelöst mit Relevanzfilter und Quellen-Ausschluss.
  - Finnhub-Gratiszugang liefert keine Schweizer News (403), ADR-Kürzel nur Yahoo-Duplikate.
  - Tavily: Titel mit Quellen-Anhängseln, gekürzte Titel, Kursseiten statt Meldungen; Treffer
    schwanken zwischen Läufen. Gelöst mit Titelbereinigung und Duplikaterkennung; die CSV ist
    der massgebende Stand.

## Schritt 2 – Labels und Eingrenzung des Sentiment-Vergleichs (28.11.2026)
- **Ziel:** gelabeltes Testset für H2
- **Entscheid:** Claude wird aus Kostengründen nicht verglichen; H2 vergleicht FinBERT (V1) mit
  OpenAI Zero-shot (V2), optional OpenAI Few-shot (V3). Kriterium H2: V2 Macro-F1 ≥ V1.
- **Ergebnis:** 146/146 gelabelt: 44 positive, 66 neutral, 36 negative. Labeling-Werkzeug um
  Kontrollmodi erweitert (`--list`, `--review`, `--blind`).
