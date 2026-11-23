# SMI Equity Analyst

Multi-Agenten-System, das Unternehmen des Swiss Market Index (SMI) anhand von Kennzahlen und News analysiert und eine strukturierte Kurzanalyse erstellt.

CAS Agentic AI & Deep Learning (FHNW) – Advanced NLP Projekt · Luca Lüdi

Details zu Ziel, Architektur, Evaluation und Zeitplan: [SCOPE.md](SCOPE.md)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # API-Keys eintragen
```

## Nutzung

```bash
python main.py --ticker NESN.SW --trace      # ein Titel, Agentenschritte sichtbar
python main.py --all                         # alle SMI-Titel
python -m eval.run_eval                      # Variante A (Single-Agent) vs. B (Multi-Agent)
pytest
```

## Struktur

| Ordner | Inhalt |
|---|---|
| `config/` | SMI-Ticker und Parameter |
| `agents/` | Fundamental-, News- und Supervisor-Agent |
| `tools/` | Deterministische Tools: Kennzahlen, Multiples, News-Fetch, Sentiment-Classifier |
| `graph/` | LangGraph-State und Graph-Definition |
| `nlp/` | Training und Vergleich der Sentiment-Modelle (Colab) |
| `eval/` | Evaluation Single- vs. Multi-Agent |
| `docs/` | Projektbericht |
| `data/` | Lokale Daten (nicht im Repo) |
