# CLAUDE.md – Kontext für Claude Code

## Projekt
SMI Equity Analyst: Multi-Agenten-System (LangGraph), das Unternehmen des SMI anhand von
Kennzahlen und News analysiert und ein Investment Memo erstellt.
CAS Agentic AI & Deep Learning (FHNW), Advanced NLP Projekt. **Abgabe: So 29.11.2026, 23:59.**
Details: `SCOPE.md`. Fortschritt: `DEVLOG.md`.

## Arbeitsweise
- Schritt für Schritt: erst ein Titel (NESN.SW) end-to-end, dann skalieren.
- Nach jedem abgeschlossenen Schritt einen Eintrag in `DEVLOG.md` (Ziel, Entscheid, Ergebnis, Probleme).
- Zahlen werden in Python berechnet, nie vom LLM. Das LLM interpretiert nur.
- Fehlende Werte sind `None`, nie geschätzt.
- Sprache: Code/Identifier Englisch, Kommentare/Docs Deutsch (Schweizer Schreibweise, ss statt ß).

## Architektur
- `agents/`: fundamental_agent, news_agent, supervisor
- `tools/`: deterministische Tools (kennzahlen, ir_reports, multiples, news_fetcher, sentiment_classifier)
- `graph/state.py`: typisierter State, `graph/graph.py`: LangGraph
- `config/`: smi_tickers.yaml, ir_sources.yaml

## Fundamental-Datenquellen
1. Geschäftsbericht-PDF von der IR-Seite (Link in `config/ir_sources.yaml`), Cache in `data/reports/`
2. Seiten der Konzernrechnung per Stichwort finden (DE/EN), nur diese mit **Docling** parsen
3. Mapping auf Standardschema, Validierung gegen `yfinance` (Abweichung > 2 % markieren)
4. Fallback: Titel ohne PDF-Eintrag nutzen nur `yfinance`
5. Docling-Ergebnisse werden als JSON in `data/cache/` gecacht (kein erneutes Parsen)

## News-Quellen
- `tools/news_fetcher.fetch_news`: yfinance (ohne `LOW_QUALITY_SOURCES`) + Tavily (nur `TRUSTED_DOMAINS`, Englisch).
- News-Agent und Sentiment-Testset (`nlp/collect_headlines.py`) nutzen dieselbe Funktion.
- Nur englische Headlines (FinBERT ist ein englisches Modell).

## News-Sentiment
- **Kein Training, kein Fine-tuning.** Standard im News-Agent: OpenAI via API
  (`SENTIMENT_BACKEND=llm`, `SENTIMENT_LLM_PROVIDER=openai`).
- Vergleich für H2 in `nlp/compare_sentiment.py`: V1 FinBERT `ProsusAI/finbert` (vortrainiert, nur
  Inferenz), V2 OpenAI Zero-shot, V3 optional OpenAI Few-shot. **Claude nicht im Vergleich** (Kosten).
- Testset: 146 SMI-Headlines in `nlp/label_smi_headlines.csv`, Labels von Claude gesetzt (nicht
  im Vergleich → kein Zirkelschluss). **Nicht** Financial PhraseBank (FinBERT darauf trainiert → Data Leakage).
- Metriken: Macro-F1, Kosten und Latenz pro Headline, Konsistenz über wiederholte Läufe.
- Sentiment-Vorhersagen werden als JSON in `data/cache/` gecacht.

## Laufzeitumgebung
Alles läuft lokal auf CPU (kein GPU, kein Colab). PyTorch als CPU-Version installieren (siehe `README.md`).

## Abgabe
Git-Repo mit Code, `docs/BERICHT.md`, Resultaten in `eval/results/` und kurzem Video.
Deshalb Pflicht: jeder Graph-Knoten loggt Start, Tool-Aufrufe, Zwischenergebnis und Dauer
(Terminal mit `--trace`, zusätzlich JSON in `eval/results/traces/`). Die messbaren Kriterien H1–H5 stehen in `SCOPE.md`.

## Befehle
- `python main.py --ticker NESN.SW --trace`
- `python -m eval.run_eval`
- `python -m nlp.compare_sentiment`
- `pytest`

## Nicht tun
- `.env`, Credentials, PDFs, Modelle nie committen (siehe `.gitignore`)
- Keine IR-Seiten crawlen: Links werden in `config/ir_sources.yaml` gepflegt
