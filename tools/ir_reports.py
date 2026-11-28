"""Kennzahlen aus Geschäftsbericht-PDFs (deterministisch, kein LLM).

Ablauf:
    1. PDF-Link aus config/ir_sources.yaml lesen (kein Crawlen), PDF nach data/reports/ cachen
    2. Seiten der Konzernrechnung per Stichwort finden (DE/EN): Titel oben auf der Seite und
       Einheitenangabe («In millions of …») auf der Seite (schliesst das Inhaltsverzeichnis aus)
    3. Nur diese Seiten mit Docling parsen, Tabellen als JSON in data/cache/docling/ ablegen
    4. Mapping der Zeilen auf das Standardschema (gleiche Schlüssel wie tools.kennzahlen);
       Validierung gegen yfinance (Abweichung > 2 % wird markiert)

Titel ohne Eintrag in ir_sources.yaml liefern None (Fallback: nur yfinance).
Fehlende Werte sind None, nie geschätzt.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONFIG = Path(__file__).resolve().parent.parent / "config" / "ir_sources.yaml"
REPORTS_DIR = Path("data/reports")
TOLERANCE = 0.02   # H1: Abweichung zu yfinance bis 2 % gilt als übereinstimmend

# Titel der Konzernrechnung (Kleinbuchstaben); geprüft werden die ersten Zeichen der Seite
STATEMENT_TITLES = (
    "consolidated income statement", "consolidated statement of income",
    "consolidated statement of profit or loss", "consolidated balance sheet",
    "consolidated statement of financial position", "consolidated cash flow statement",
    "consolidated statement of cash flows",
    "konzernerfolgsrechnung", "konsolidierte erfolgsrechnung", "konzernbilanz",
    "konsolidierte bilanz", "konzerngeldflussrechnung", "konsolidierte geldflussrechnung",
)
UNIT_HINT = re.compile(r"in (millions|thousands|billions|mio\.?|millionen|tausend|mrd\.?)\b", re.IGNORECASE)
UNIT_FACTOR = {"millions": 1e6, "mio": 1e6, "mio.": 1e6, "millionen": 1e6,
               "thousands": 1e3, "tausend": 1e3, "billions": 1e9, "mrd": 1e9, "mrd.": 1e9}
TITLE_WINDOW = 400   # Zeichen ab Seitenanfang, in denen der Titel stehen muss
MAX_PAGES = 8

# Standardschema: Schlüssel → (Regex auf die Zeilenbeschriftung, Modus, skaliert mit Einheit)
#   first = erste Zeile mit Zahl, sum = Summe aller passenden Zeilen, abs = Betrag der ersten Zeile
MAPPING: dict[str, tuple[str, str, bool]] = {
    "revenue": (r"^(sales|net sales|revenues?|total revenues?|net revenues?|umsatz|nettoumsatz|umsatzerlöse)$", "first", True),
    "operating_profit": (r"^(operating profit|operating income|ebit|betriebsergebnis|operatives ergebnis)$", "first", True),
    "net_income": (r"attributable to (the )?(shareholders|owners|equity holders) of the parent|"
                   r"den aktionären der .* zurechenbar", "first", True),
    "eps_diluted": (r"^diluted earnings per share|^verwässertes ergebnis je aktie", "first", False),
    "total_assets": (r"^(total assets|total aktiven|bilanzsumme)$", "first", True),
    "total_liabilities": (r"^(total liabilities|total fremdkapital|total verbindlichkeiten)$", "first", True),
    "total_equity": (r"^(total )?equity attributable to (the )?(shareholders|owners|equity holders) of the parent|"
                     r"^den aktionären .* zurechenbares eigenkapital", "first", True),
    "cash": (r"^(cash and cash equivalents|flüssige mittel|zahlungsmittel und zahlungsmitteläquivalente)$", "first", True),
    "total_debt": (r"^(financial debt|finanzverbindlichkeiten|borrowings)$", "sum", True),
    "operating_cash_flow": (r"^(operating cash flow|net cash (from|provided by|generated from) operating activities|"
                            r"cash flow from operating activities|geldfluss aus betrieblicher tätigkeit)$", "first", True),
    "capex": (r"^(capital expenditure|purchase of property, plant and equipment|"
              r"investitionen in sachanlagen)$", "abs", True),
    "depreciation_amortization": (r"^depreciation and amorti[sz]ation$|^abschreibungen", "abs", True),
    "dividends_paid": (r"^dividends? paid to (the )?shareholders of the parent|^dividends? paid$|"
                       r"^dividendenzahlungen?", "abs", True),
}


# ---------- Konfiguration und Download ----------

def load_sources(path: Path = CONFIG) -> dict[str, dict]:
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("reports") or {}


def _cache_dir() -> Path:
    base = (os.getenv("CACHE_DIR") or "data/cache").split("#")[0].strip()
    path = Path(base) / "docling"
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_report(ticker: str, url: str, fiscal_year: int) -> Path:
    """Lädt das PDF einmal herunter (Cache in data/reports/)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{ticker}_{fiscal_year}.pdf"
    if path.exists() and path.stat().st_size > 0:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (smi-equity-analyst)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if not data.startswith(b"%PDF"):
        raise ValueError(f"{url} liefert kein PDF (Link in config/ir_sources.yaml prüfen)")
    path.write_bytes(data)
    return path


# ---------- Seiten finden und parsen ----------

def find_statement_pages(pdf_path: Path) -> list[int]:
    """Seiten (1-basiert), die mit einem Titel der Konzernrechnung beginnen und eine Einheit nennen."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    pages = []
    for i in range(len(pdf)):
        text = pdf[i].get_textpage().get_text_range()
        head = " ".join(text[:TITLE_WINDOW].lower().split())
        if any(t in head for t in STATEMENT_TITLES) and UNIT_HINT.search(text):
            if "comprehensive income" in head or "changes in equity" in head or "eigenkapitalnachweis" in head:
                continue
            pages.append(i + 1)
    return pages[:MAX_PAGES]


def parse_pages(pdf_path: Path, pages: list[int]) -> list[dict]:
    """Parst die angegebenen Seiten mit Docling; pro Tabelle Spaltenköpfe und Zeilen als Text."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=False)   # PDFs mit Textebene, OCR unnötig und langsam
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    tables = []
    for page in pages:
        doc = converter.convert(str(pdf_path), page_range=(page, page)).document
        for table in doc.tables:
            df = table.export_to_dataframe(doc=doc)
            tables.append({
                "page": page,
                "columns": [str(c) for c in df.columns],
                "rows": [[str(v) for v in row] for row in df.itertuples(index=False)],
            })
    return tables


def load_tables(ticker: str, source: dict) -> tuple[list[dict], Path]:
    """Docling-Tabellen aus dem Cache oder neu geparst (und dann gecacht)."""
    fy = int(source["fiscal_year"])
    cache = _cache_dir() / f"{ticker}_{fy}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["tables"], cache
    pdf = download_report(ticker, source["url"], fy)
    pages = find_statement_pages(pdf)
    if not pages:
        raise ValueError(f"Keine Seiten der Konzernrechnung in {pdf} gefunden")
    tables = parse_pages(pdf, pages)
    cache.write_text(json.dumps({"ticker": ticker, "fiscal_year": fy, "pages": pages, "tables": tables},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    return tables, cache


# ---------- Zahlen und Mapping ----------

def parse_number(text: str) -> float | None:
    """'89 490' → 89490, '(48 694)' → -48694, '1,234.5' → 1234.5, '1'234' → 1234; '-', '14.2%' → None."""
    s = (text or "").strip().replace("−", "-")
    if not s or s in {"-", "–", "—", "nan", "None"} or "%" in s:
        return None
    negative = (s.startswith("(") and s.endswith(")")) or s.startswith(("-", "–"))
    s = s.strip("()-– ")
    s = re.sub(r"[\s  '’]", "", s)
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    elif re.fullmatch(r"\d+,\d+", s):
        s = s.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    value = float(s)
    return -value if negative else value


def _year_column(columns: list[str], year: int) -> int | None:
    for k, c in enumerate(columns):
        if re.search(rf"\b{year}\b", c):
            return k
    return None


def _unit_factor(columns: list[str]) -> float:
    m = UNIT_HINT.search(" ".join(columns))
    return UNIT_FACTOR.get(m.group(1).lower(), 1e6) if m else 1e6


def map_tables(tables: list[dict], fiscal_year: int) -> dict:
    """Ordnet die Tabellenzeilen dem Standardschema zu. Liefert Werte, Vorjahresumsatz und Fundstellen."""
    values: dict[str, float | None] = {key: None for key in MAPPING}
    values["revenue_prev"] = None
    sources: dict[str, str] = {}
    currency = None
    for key, (pattern, mode, scaled) in MAPPING.items():
        regex = re.compile(pattern, re.IGNORECASE)
        total, found = 0.0, False
        for table in tables:
            cols = table["columns"]
            col, col_prev = _year_column(cols, fiscal_year), _year_column(cols, fiscal_year - 1)
            if col is None:
                continue
            factor = _unit_factor(cols) if scaled else 1.0
            currency = currency or (m.group(1) if (m := re.search(r"\b(CHF|USD|EUR)\b", " ".join(cols))) else None)
            for row in table["rows"]:
                label = " ".join(row[0].split())
                if not regex.search(label):
                    continue
                number = parse_number(row[col]) if col < len(row) else None
                if number is None:
                    continue
                if key == "revenue" and col_prev is not None and values["revenue_prev"] is None:
                    prev = parse_number(row[col_prev]) if col_prev < len(row) else None
                    values["revenue_prev"] = prev * factor if prev is not None else None
                if mode == "sum":
                    total += number * factor
                    found = True
                    sources[key] = f"S. {table['page']}"
                    continue
                values[key] = (abs(number) if mode == "abs" else number) * factor
                sources[key] = f"S. {table['page']}: {label}"
                break
            if values[key] is not None:
                break
        if mode == "sum" and found:
            values[key] = total
    values["fiscal_year"] = fiscal_year
    values["currency"] = currency
    return {"values": values, "sources": sources}


# ---------- öffentliche Schnittstelle ----------

def fetch_report_kennzahlen(ticker: str) -> dict | None:
    """Kennzahlen aus dem Geschäftsbericht oder None, wenn kein PDF-Eintrag existiert.

    Rückgabe: {"values": {...Standardschema...}, "sources": {key: Fundstelle}, "cache": Pfad}
    """
    source = load_sources().get(ticker)
    if not source or not str(source.get("url", "")).lower().split("?")[0].endswith(".pdf"):
        return None
    tables, cache = load_tables(ticker, source)
    result = map_tables(tables, int(source["fiscal_year"]))
    result["cache"] = str(cache)
    return result


def validate(report: dict[str, float | None], reference: dict[str, float | None],
             tolerance: float = TOLERANCE) -> dict[str, dict]:
    """Vergleicht PDF-Werte mit yfinance. Pro Kennzahl: beide Werte, relative Abweichung, Flag."""
    out = {}
    for key in MAPPING:
        a, b = report.get(key), reference.get(key)
        if a is None or b is None:
            out[key] = {"report": a, "yfinance": b, "deviation": None, "ok": None}
            continue
        deviation = abs(a - b) / abs(b) if b else (0.0 if a == b else None)
        out[key] = {"report": a, "yfinance": b, "deviation": deviation,
                    "ok": deviation is not None and deviation <= tolerance}
    return out
