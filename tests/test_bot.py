from bot import PROVIDERS


def test_supported_protocols_exclude_mtproto():
    assert set(PROVIDERS) == {"Telemt", "HTTP", "SOCKS5"}
