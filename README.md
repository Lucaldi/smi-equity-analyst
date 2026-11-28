# SMI Equity Analyst

Multi-Agenten-System (LangGraph), das ein Unternehmen des Swiss Market Index (SMI) anhand von
Kennzahlen und aktuellen News analysiert und ein Investment Memo erstellt.

CAS Agentic AI & Deep Learning (FHNW) – Advanced NLP Projekt · Luca Lüdi

## Was der Agent macht

1. **Fundamental-Agent:** liest die Kennzahlen aus dem Geschäftsbericht (PDF, Konzernrechnung
   mit Docling geparst), prüft sie gegen `yfinance` und berechnet Multiples. Titel ohne
   hinterlegten Geschäftsbericht nutzen nur `yfinance`.
2. **News-Agent:** sammelt englische News der letzten 90 Tage (yfinance und Tavily auf
   Qualitätsmedien), filtert sie nach Relevanz und bewertet das Sentiment jeder Headline.
3. **Supervisor:** ruft beide Agenten auf, führt die Ergebnisse zusammen und schreibt das Memo.

Alle Zahlen werden in Python berechnet; das Sprachmodell interpretiert nur. Fehlende Werte
bleiben leer und werden nicht geschätzt.

## Installation

Voraussetzung: Python 3.11 oder neuer. Alles läuft lokal auf der **CPU**, eine GPU ist nicht nötig.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 1. PyTorch als CPU-Version (vor requirements.txt, sonst wird die grosse CUDA-Version installiert)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. Restliche Abhängigkeiten
pip install -r requirements.txt
```

Prüfen, dass die CPU-Version installiert ist:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# erwartet: z. B. 2.x.x+cpu False
```

## Konfiguration

### API-Keys (`.env`)

```bash
cp .env.example .env               # Windows: copy .env.example .env
```

Danach die Werte in `.env` eintragen. Die Datei wird nie committet.

| Variable | Pflicht | Bedeutung |
|---|---|---|
| `OPENAI_API_KEY` | ja | Sprachmodell für Agenten und Sentiment |
| `TAVILY_API_KEY` | nein | News von Qualitätsmedien (Reuters, Bloomberg, FT …); leer = nur yfinance |
| `LLM_PROVIDER`, `LLM_MODEL` | – | Sprachmodell der Agenten (Standard `openai`, `gpt-4o-mini`) |
| `SENTIMENT_BACKEND` | – | `llm` (Standard) oder `finbert` (lokal, ohne API-Kosten) |
| `SENTIMENT_LLM_PROVIDER`, `SENTIMENT_LLM_MODEL` | – | Modell für das Sentiment (leer = `LLM_MODEL`) |
| `CACHE_DIR` | – | Ablage für Zwischenergebnisse (Standard `data/cache`) |

### Titel und Geschäftsberichte (`config/`)

- `config/smi_tickers.yaml`: Liste der SMI-Titel (Ticker → Firmenname).
- `config/ir_sources.yaml`: direkter Link zum Geschäftsbericht-PDF pro Titel. Ein neuer Titel
  bekommt hier einen Eintrag mit der PDF-URL; ohne Eintrag wird nur `yfinance` genutzt.
  IR-Seiten werden nicht automatisch durchsucht.

## Anwendung

```bash
python main.py --ticker NESN.SW            # einen Titel analysieren
python main.py --ticker NESN.SW --trace    # mit sichtbaren Agentenschritten
python main.py --all                       # alle SMI-Titel
```

Mit `--trace` loggt jeder Schritt Start, Tool-Aufrufe, Zwischenergebnis und Dauer im Terminal;
zusätzlich wird der Ablauf als JSON in `eval/results/traces/` gespeichert.

### Cache

Geparste Geschäftsberichts-Seiten und Sentiment-Bewertungen werden als JSON in `data/cache/`
abgelegt. Ein zweiter Lauf parst nicht neu und verursacht keine zusätzlichen API-Kosten.
Zum Neuberechnen den betreffenden Eintrag in `data/cache/` löschen.

## Evaluation

```bash
python -m eval.run_eval                    # Single-Agent vs. Multi-Agent (H1, H3–H5)
python -m nlp.compare_sentiment            # Sentiment: FinBERT vs. OpenAI (H2)
pytest                                     # Tests
```

Resultate liegen in `eval/results/`. Das Sentiment-Testset (146 Headlines zu SMI-Titeln) ist
`nlp/label_smi_headlines.csv`; die Labelregeln stehen in `nlp/LABELING.md`.

## Struktur

| Ordner | Inhalt |
|---|---|
| `config/` | SMI-Ticker und Links zu den Geschäftsberichten |
| `agents/` | Fundamental-, News- und Supervisor-Agent |
| `tools/` | Deterministische Tools: Kennzahlen, Geschäftsberichte, Multiples, News, Sentiment |
| `graph/` | LangGraph-State und Graph-Definition |
| `nlp/` | Sentiment-Testset, Labeling-Werkzeug und Modellvergleich |
| `eval/` | Evaluation und Resultate |
| `tests/` | Tests |
| `data/` | Geschäftsberichte und Cache (lokal, nicht im Repo) |
