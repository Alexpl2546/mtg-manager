import pytest

from config import _parse_admin_ids, load_settings


def test_parse_admin_ids():
    assert _parse_admin_ids("301615601, 42") == frozenset({301615601, 42})


def test_load_settings_requires_admin_ids(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.delenv("ADMIN_IDS", raising=False)

    with pytest.raises(RuntimeError, match="ADMIN_IDS"):
        load_settings()


def test_load_settings(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_IDS", "301615601")

    settings = load_settings()

    assert settings.bot_token == "test-token"
    assert settings.admin_ids == frozenset({301615601})
