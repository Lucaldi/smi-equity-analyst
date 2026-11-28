# SMI Equity Analyst – Projektbericht

CAS Agentic AI & Deep Learning (FHNW) · Advanced NLP Projekt · Luca Lüdi · 29.11.2026

## 1. Einsatz von GenAI
## 2. Problemstellung
## 3. Scope (in / bewusst ausgeschlossen)
## 4. Untersuchungsfragen und Kriterien (H1–H5)
## 5. Datenlage

### 5.x Testset News-Sentiment (H2)

**Herkunft:** Headlines zu den SMI-Titeln, gesammelt am 24.11.2026 mit `nlp/collect_headlines.py`.
Das Skript nutzt dieselbe Funktion wie der News-Agent (`tools/news_fetcher.fetch_news`), damit das
Testset dem entspricht, was der Agent im Betrieb sieht. Zwei Quellen:
- **yfinance-News** ohne Bewertungs-Blogs und Aggregatoren (Simply Wall St., Zacks, GuruFocus,
  Motley Fool u. a.). Deren Titel sind überwiegend Bewertungs-Teaser («Is … Undervalued?») und
  machten in einer ersten Sammlung 28 % aus.
- **Tavily-Suche** (Nachrichten) ausschliesslich auf einer festen Liste englischsprachiger
  Qualitätsmedien (Reuters, Bloomberg, FT, WSJ, CNBC, Swissinfo, Fachmedien). Nur Englisch, weil
  FinBERT ein englisches Modell ist.

Finnhub wurde geprüft und verworfen: Für Schweizer Ticker liefert der Gratis-Zugang keine News,
über die ADR-Kürzel kommen fast nur dieselben Yahoo-Meldungen wie bei yfinance.

**Filter:** Ein Relevanzfilter behält nur Headlines, die das Unternehmen nennen (Name, Marke oder
ADR-Kürzel); bei UBS werden Research-Meldungen über Drittfirmen ausgeschlossen («UBS cuts Tele2 …»).
Titel werden von Quellen-Anhängseln bereinigt, Kursseiten verworfen, Duplikate (auch gekürzte
Fassungen) entfernt. Pro Titel höchstens 10 Headlines.

**Bereinigung:** 6 Headlines manuell entfernt, weil sie eine andere Firma betreffen (z. B. Amgen
mit Novartis als Vergleich, Danone mit Nestlé als Nebenbezug, UBS-Research zu Tesla).
Verbleibend: **146 Headlines** aus 33 Quellen (Reuters 28, Investing.com 28, WSJ 26),
Zeitraum 16.12.2025 bis 24.11.2026.

**Labeling:** durch Claude (Opus 5.5) gemäss `nlp/LABELING.md` (positive / neutral / negative aus
Sicht des Aktionärs, im Zweifel neutral). Verglichen werden FinBERT (V1) und OpenAI (V2, optional
V3 Few-shot); Claude wurde aus Kostengründen nicht in den Vergleich aufgenommen. Dadurch bewertet
kein verglichenes Modell sich selbst. Verteilung: **44 positive (30 %), 66 neutral (45 %),
36 negative (25 %)**. Wegen der ungleichen Verteilung wird Macro-F1 statt Accuracy verwendet.

**Einschränkungen:**
- **Ungleiche Abdeckung:** Alle 20 SMI-Titel sind vertreten, aber zu Alcon (1), Geberit (1),
  Givaudan (2), Swiss Life (3) und Sika (4) gibt es nur wenige seriöse englische Headlines.
  Aussagen pro Titel sind deshalb nicht möglich, nur über das Gesamtset.
- **Zeitraum:** 46 Headlines sind älter als 90 Tage. Für das Testset ist das unerheblich, da nur
  die Klassifikation einzelner Headlines gemessen wird, nicht die Aktualität.
- **Gleiche Ereignisse:** Einige Ereignisse erscheinen in mehreren Quellen mit anderer Formulierung
  (z. B. Galdermas Kauf von ZO Skin Health). Die Headlines sind dadurch nicht ganz unabhängig.
- **Nicht exakt reproduzierbar:** Tavily liefert bei wiederholten Suchen leicht andere Treffer.
  Massgebend ist deshalb die eingecheckte CSV, nicht ein erneuter Lauf des Skripts.
- **Modell als Annotator:** Die Referenz stammt von einem LLM, nicht von einem Menschen. Ein
  LLM-Label liegt näher an der Urteilsweise eines anderen LLM (OpenAI) als an der von FinBERT;
  das kann V2 leicht bevorteilen. Abhilfe: eine Stichprobe (20–30 Headlines) vom Autor von Hand
  labeln und die Übereinstimmung mit den Claude-Labels angeben.
- **Ein einzelner Annotator:** keine Inter-Annotator-Übereinstimmung.
## 6. Lösungsansatz
### 6.1 Architektur
### 6.2 Fundamental-Agent
### 6.3 News-Agent und Sentiment-Modelle
### 6.4 Supervisor
### 6.5 Evaluation
## 7. Resultate
## 8. Diskussion
## 9. Reflexion
## 10. Video und Ausführung
