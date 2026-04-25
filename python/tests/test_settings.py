from utils.symbols import parse_symbols


def test_parse_symbols_default_case() -> None:
    symbols = parse_symbols("XAUUSD, XAUEUR")
    assert symbols == ["XAUUSD", "XAUEUR"]


def test_parse_symbols_empty_tokens() -> None:
    symbols = parse_symbols(" XAUUSD ,, xaueur ")
    assert symbols == ["XAUUSD", "XAUEUR"]
