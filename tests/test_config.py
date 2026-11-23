from main import load_tickers


def test_smi_has_20_tickers():
    tickers = load_tickers()
    assert len(tickers) == 20
    assert all(t.endswith(".SW") for t in tickers)
