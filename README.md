# SMI Equity Analyst

Multi-Agenten-System, das Unternehmen des Swiss Market Index (SMI) anhand von Kennzahlen und News analysiert und eine strukturierte Kurzanalyse erstellt.

CAS Agentic AI & Deep Learning (FHNW) – Advanced NLP Projekt · Luca Lüdi

Details zu Ziel, Architektur, Evaluation und Zeitplan: [SCOPE.md](SCOPE.md)

## Setup

Alles läuft lokal auf der **CPU**, eine GPU ist nicht nötig. Es wird kein Modell trainiert;
FinBERT wird nur für die Inferenz genutzt.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 1. PyTorch als CPU-Version installieren (vor requirements.txt,
#    sonst zieht pip die deutlich grössere CUDA-Version)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. Restliche Abhängigkeiten
pip install -r requirements.txt

cp .env.example .env               # API-Keys eintragen
```

Prüfen, dass die CPU-Version installiert ist:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# erwartet: z. B. 2.x.x+cpu False
```

### Konfiguration (`.env`)

| Variable | Bedeutung |
|---|---|
| `TAVILY_API_KEY` | News von Qualitätsmedien (Reuters, Bloomberg, FT …); leer = nur yfinance |
| `LLM_PROVIDER`, `LLM_MODEL` | LLM für die Agenten (`openai` \| `anthropic`) |
| `SENTIMENT_BACKEND` | `llm` (Standard) oder `finbert` |
| `SENTIMENT_LLM_PROVIDER` | Anbieter für das Sentiment-LLM: `openai` (Standard und im H2-Vergleich) |
| `SENTIMENT_LLM_MODEL` | Modell für das Sentiment-LLM (leer = `LLM_MODEL`) |

### Cache

Docling-Ergebnisse (geparste Geschäftsberichts-Seiten) und Sentiment-Vorhersagen werden als
JSON in `data/cache/` abgelegt. Wiederholte Läufe parsen nicht neu und verursachen keine
zusätzlichen API-Kosten. Zum Neuberechnen den betreffenden Cache-Eintrag löschen.

## Nutzung

```bash
python main.py --ticker NESN.SW --trace      # ein Titel, Agentenschritte sichtbar
python main.py --all                         # alle SMI-Titel
python -m eval.run_eval                      # Variante A (Single-Agent) vs. B (Multi-Agent)
python -m nlp.compare_sentiment              # Sentiment-Vergleich FinBERT vs. OpenAI (H2)
pytest
```

## Struktur

| Ordner | Inhalt |
|---|---|
| `config/` | SMI-Ticker und Parameter |
| `agents/` | Fundamental-, News- und Supervisor-Agent |
| `tools/` | Deterministische Tools: Kennzahlen, Multiples, News-Fetch, Sentiment-Classifier |
| `graph/` | LangGraph-State und Graph-Definition |
| `nlp/` | Vergleich der Sentiment-Varianten (FinBERT, OpenAI) und gelabelte SMI-Headlines |
| `eval/` | Evaluation Single- vs. Multi-Agent |
| `docs/` | Projektbericht |
| `data/` | Lokale Daten und Cache (nicht im Repo) |
