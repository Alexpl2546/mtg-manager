from utils.keyboards import action_keyboard, protocol_keyboard


def _button_texts(markup) -> list[str]:
    return [
        button.text
        for row in markup.keyboard
        for button in row
    ]


def test_protocol_keyboard_does_not_offer_mtproto():
    texts = _button_texts(protocol_keyboard())

    assert texts == ["Telemt", "HTTP", "SOCKS5"]
    assert "MTProto" not in texts


def test_action_keyboard_does_not_offer_mtg_domain_settings():
    assert "🌐 Домен" not in _button_texts(action_keyboard("Telemt"))
