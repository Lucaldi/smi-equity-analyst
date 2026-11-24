"""Offline-Tests für die deterministischen Teile des News-Fetchers (kein Netzwerk)."""
from tools import news_fetcher as nf


def test_relevance_by_name_alias_and_ticker():
    assert nf.is_relevant("Nestle Eyes Autonomous Factory Lines", "NESN.SW", "Nestlé")
    assert nf.is_relevant("Cartier Owner's Stock Slides", "CFR.SW", "Richemont")
    assert nf.is_relevant("Is Sika (SWX:SIKA) Cheap?", "SIKA.SW", "Sika")
    assert not nf.is_relevant("Vicat shares rise as J.P. Morgan flags cement pricing", "GIVN.SW", "Givaudan")


def test_ubs_research_about_other_firms_is_excluded():
    assert not nf.is_relevant("UBS cuts Tele2 as cost savings fade", "UBSG.SW", "UBS")
    assert not nf.is_relevant("Amazon Stocks Rise After UBS Trims Target", "UBSG.SW", "UBS")
    assert nf.is_relevant("UBS Set to Revise Capital Targets", "UBSG.SW", "UBS")


def test_title_suffix_is_removed():
    assert nf._TITLE_SUFFIX.sub("", "Roche drug misses goal | Reuters") == "Roche drug misses goal"
    assert nf._TITLE_SUFFIX.sub("", "Holcim raises outlook - Financial Times") == "Holcim raises outlook"
    assert nf._TITLE_SUFFIX.sub("", "Swiss Re - the story") == "Swiss Re - the story"


def test_clean_title():
    assert nf.clean_title("Amrize stock falls as CFO steps down By Investing.com") == "Amrize stock falls as CFO steps down"
    assert nf.clean_title("Swiss Re posts 9% profit increase - reuters.com") == "Swiss Re posts 9% profit increase"
    assert nf.clean_title("Givaudan sales beat market view on fine fragrance ...") == "Givaudan sales beat market view on fine fragrance"
    assert nf.clean_title("Swiss Life Holding AG (SLHN.S) | Stock Price & Latest News") == ""
    assert nf.clean_title("Givaudan SA") == ""


def test_truncated_title_counts_as_duplicate():
    full = nf.normalize_title("Amrize cuts 2026 profit outlook as roofing weakness and costs bite; shares down 5%")
    cut = nf.normalize_title("Amrize cuts 2026 profit outlook as roofing weakness and")
    assert nf.is_duplicate(cut, {full})
    assert not nf.is_duplicate(nf.normalize_title("Holcim raises 2026 earnings outlook"), {full})


def test_to_iso_date():
    assert nf.to_iso_date("2026-11-24T15:00:00Z") == "2026-11-24"
    assert nf.to_iso_date("Mon, 24 Nov 2026 15:00:00 GMT") == "2026-11-24"
    assert nf.to_iso_date("") == ""
    assert nf.to_iso_date("unbekannt") == ""


def test_fetch_tavily_without_key_returns_empty(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert nf.fetch_tavily("NESN.SW", "Nestlé") == []
