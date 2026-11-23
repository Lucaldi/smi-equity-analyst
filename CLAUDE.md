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

## Abgabe
Git-Repo mit Code, `docs/BERICHT.md`, Resultaten in `eval/results/` und kurzem Video.
Deshalb Pflicht: jeder Graph-Knoten loggt Start, Tool-Aufrufe, Zwischenergebnis und Dauer
(Terminal mit `--trace`, zusätzlich JSON in `eval/results/traces/`). Die messbaren Kriterien H1–H5 stehen in `SCOPE.md`.

## Befehle
- `python main.py --ticker NESN.SW --trace`
- `python -m eval.run_eval`
- `pytest`

## Nicht tun
- `.env`, Credentials, PDFs, Modelle nie committen (siehe `.gitignore`)
- Keine IR-Seiten crawlen: Links werden in `config/ir_sources.yaml` gepflegt
