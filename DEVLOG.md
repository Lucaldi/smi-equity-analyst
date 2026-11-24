# Entwicklungsprotokoll

Ein Eintrag pro Schritt. Grundlage für die Kapitel «Lösungsansatz» und «Reflexion».

---

## Schritt 0 – Setup (23.11.2026)
- **Ziel:** Repo, Struktur, Entwicklungsumgebung (VS Code + Claude Code)
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
