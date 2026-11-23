# SMI Equity Analyst – Multi-Agenten-System zur Unternehmensanalyse

**CAS Agentic AI & Deep Learning (FHNW) – Advanced NLP Projekt**
Luca Lüdi · Abgabe 29.11.2026

---

## 1. Ziel

Ein Multi-Agenten-System (MAS) analysiert ein Unternehmen aus dem SMI anhand seiner **Kennzahlen** und aktueller **News** und erstellt daraus eine strukturierte Kurzanalyse (Investment Memo) mit Gesamteinschätzung.

**Fragestellung:** Liefert ein spezialisiertes Multi-Agenten-System bessere, faktentreuere und konsistentere Unternehmensanalysen als ein einzelner LLM-Aufruf mit denselben Daten – und welche NLP-Methode eignet sich am besten für die Bewertung der News?

## 2. Scope

### In Scope
- Universum: die 20 SMI-Titel (Stand prüfen vor Abgabe)
- Datenquellen: Kennzahlen via `yfinance`, News via News-API (z. B. Finnhub / yfinance-News)
- Agenten: Fundamental, News, Supervisor (siehe Architektur)
- NLP-Komponente: News-Sentiment-Klassifikation mit Modellvergleich
- Evaluation: quantitativer Vergleich der Varianten (siehe Kapitel 5)
- Output: Memo als JSON + Markdown

### Out of Scope
- Frontend / Web-App
- Kursprognosen, Handelssignale, Backtesting
- Titel ausserhalb des SMI
- Langzeit-Persistenz / Datenbank (Ablage als Dateien genügt)

### SMI-Titel (Stand MarketScreener, Nov. 2026)
| Ticker (Yahoo) | Unternehmen | Ticker (Yahoo) | Unternehmen |
|---|---|---|---|
| ROG.SW | Roche | GIVN.SW | Givaudan |
| NOVN.SW | Novartis | HOLN.SW | Holcim |
| NESN.SW | Nestlé | SDZ.SW | Sandoz |
| ABBN.SW | ABB | SIKA.SW | Sika |
| UBSG.SW | UBS | ALC.SW | Alcon |
| CFR.SW | Richemont | SLHN.SW | Swiss Life |
| ZURN.SW | Zurich Insurance | GEBN.SW | Geberit |
| SREN.SW | Swiss Re | AMRZ.SW | Amrize |
| LONN.SW | Lonza | PGHN.SW | Partners Group |
| GALD.SW | Galderma | LOGN.SW | Logitech |

> Ticker vor dem ersten Lauf mit `yfinance` verifizieren.

## 2a. Untersuchungsfragen und messbare Kriterien

| # | Frage | Metrik | Erfolgskriterium |
|---|---|---|---|
| H1 | Extrahiert der Fundamental-Agent die Kennzahlen korrekt aus den Geschäftsberichten? | Anteil Kennzahlen mit Abweichung ≤ 2 % zu yfinance | ≥ 90 % |
| H2 | Welches Modell bewertet News-Sentiment am besten? | Macro-F1 auf Financial PhraseBank und eigenen SMI-Headlines | FinBERT > TF-IDF-Baseline |
| H3 | Ist das Multi-Agenten-System faktentreuer als ein Single-Agent? | Anteil korrekter Zahlen im Memo | MAS > Single-Agent |
| H4 | Liefert das System konsistente Urteile? | Gleiches Gesamturteil in 3 Läufen pro Titel | ≥ 80 % der Titel |
| H5 | Ist das System praxistauglich? | Laufzeit und Kosten pro Analyse | < 5 min, < 0.50 CHF |

Die Schwellenwerte sind Zielwerte. Werden sie verfehlt, wird das im Bericht analysiert, nicht kaschiert.

## 3. Architektur

```
                 ┌────────────────────────┐
   Ticker ─────▶ │   Supervisor-Agent     │ ──▶ Investment Memo
                 │ (Planung + Synthese)   │
                 └───────┬────────┬───────┘
                         │        │
              ┌──────────▼──┐  ┌──▼──────────┐
              │ Fundamental │  │ News-Agent  │
              │   -Agent    │  │             │
              └──────┬──────┘  └──────┬──────┘
                     │                │
        Tools:  Kennzahlen      News-Fetch + Sentiment-
                (yfinance),     Classifier (NLP-Modell)
                Multiples-Rechner
```

| Agent | Aufgabe | Tools | Output |
|---|---|---|---|
| Fundamental | Profitabilität, Wachstum, Bilanz, Bewertung | Kennzahlen-Fetcher, Multiples-Rechner (deterministisch) | Score + Begründung je Dimension |
| News | Relevante News der letzten 90 Tage sammeln, filtern, bewerten | News-Fetcher, Sentiment-Classifier | Sentiment-Score + Top-Themen |
| Supervisor | Agenten aufrufen, Ergebnisse zusammenführen, Widersprüche auflösen | – | Memo mit Gesamteinschätzung |

**Framework:** LangGraph (Zustand als typisiertes `State`-Objekt, Supervisor als Router).
**Prinzip:** Zahlen werden in Python berechnet, nicht vom LLM – das LLM interpretiert nur.

## 4. NLP-Komponente: News-Sentiment

Die Bewertung jeder News (positiv / neutral / negativ) ist der zentrale NLP-Baustein des News-Agents. Verglichen werden:

| Variante | Modell |
|---|---|
| V1 | TF-IDF + Logistic Regression (Baseline) |
| V2 | FinBERT (`ProsusAI/finbert`), fine-getuned |
| V3 | LLM Zero-shot (Prompt im News-Agent) |

**Daten:**
- Training/Test: Financial PhraseBank (3 Klassen, expertengelabelt)
- Zusätzlicher Test: ca. 200 selbst gelabelte Headlines zu SMI-Titeln (Domain-Transfer)

**Metriken:** Macro-F1, Confusion Matrix, Latenz und Kosten pro News.
Das beste Modell wird als Tool im News-Agent eingesetzt.

## 5. Evaluation des MAS

| Variante | Beschreibung |
|---|---|
| A – Single-Agent | Ein LLM-Aufruf erhält alle Kennzahlen + News und schreibt das Memo |
| B – Multi-Agent | Spezialisierte Agenten + Supervisor (dieses System) |

| Kriterium | Messung |
|---|---|
| Faktentreue | Anteil Zahlen im Memo, die mit den Quelldaten übereinstimmen (automatisch geprüft) |
| Konsistenz | Gleicher Titel 3× analysiert → Abweichung der Gesamteinschätzung |
| Qualität | LLM-as-a-Judge mit fixem Bewertungsraster (Vollständigkeit, Begründung, Struktur), stichprobenweise manuell geprüft |
| Effizienz | Laufzeit, Tokens, Kosten pro Analyse |

Lauf über alle 20 SMI-Titel, Resultate als Tabelle und Grafiken.

## 6. Repo-Struktur

```
smi-equity-analyst/
├── README.md
├── SCOPE.md
├── requirements.txt
├── .env.example            # API-Keys, nie committen
├── .gitignore              # .env, Daten, Modelle, Credentials
├── config/
│   └── smi_tickers.yaml
├── agents/
│   ├── fundamental_agent.py
│   ├── news_agent.py
│   └── supervisor.py
├── tools/
│   ├── ir_reports.py
│   ├── kennzahlen.py
│   ├── multiples.py
│   ├── news_fetcher.py
│   └── sentiment_classifier.py
├── graph/
│   ├── state.py
│   └── graph.py
├── nlp/
│   ├── train_sentiment.ipynb   # V1–V3, Colab
│   └── label_smi_headlines.csv
├── eval/
│   ├── run_eval.py             # Variante A vs. B
│   └── results/
├── docs/
│   └── BERICHT.md              # Abgabe-Bericht
└── tests/
```

## 7. Abgabe (gemäss Absprache mit Dozent)

Abgabe als **Git-Repository** statt Notebook:
- **Code** inkl. Setup-Anleitung (`README.md`)
- **Dokumentation / Bericht:** `docs/BERICHT.md` mit Titel, Einsatz von GenAI, Problemstellung, Datenlage, Lösungsansatz, Resultate, Diskussion, Reflexion
- **Resultate:** `eval/results/` (Tabellen, Grafiken, Beispiel-Memos)
- **Video (3–5 min):** Aufnahme eines Laufs, in dem die Arbeitsschritte der Agenten sichtbar sind (Trace-Ausgabe im Terminal, siehe unten)

### Sichtbarkeit der Agentenschritte
Jeder Graph-Knoten protokolliert Start, Tool-Aufrufe, Zwischenergebnis und Dauer im Terminal (`--trace`) und schreibt denselben Trace als JSON nach `eval/results/traces/`. Damit sind die Schritte im Video und im Bericht nachvollziehbar.

## 8. Zeitplan (Stand 23.11.)

| Bis | Meilenstein |
|---|---|
| Mo 23.11. | Repo auf GitHub, VS Code + Claude Code eingerichtet |
| Di 24.11. | Fundamental-Agent für Nestlé end-to-end (PDF → Docling → Kennzahlen → Validierung) |
| Mi 25.11. | News-Agent + Sentiment-Vergleich (TF-IDF, FinBERT, LLM) |
| Do 26.11. | Supervisor, End-to-End-Lauf, Single-Agent-Baseline; Skalierung auf 5 Titel mit PDF, Rest via yfinance |
| Fr 27.11. | Evaluation, Resultate, Grafiken |
| Sa 28.11. | Bericht (docs/BERICHT.md), Video aufnehmen |
| So 29.11. | Puffer, Abgabe bis 23:59 |
