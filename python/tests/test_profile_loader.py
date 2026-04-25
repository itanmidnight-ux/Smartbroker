from broker.profile_loader import load_profile


def test_load_demo_profile() -> None:
    profile = load_profile("metaquotes_demo")
    assert profile["mode"] == "paper"


def test_load_live_profile() -> None:
    profile = load_profile("weltrade_real")
    assert profile["mode"] == "live"
