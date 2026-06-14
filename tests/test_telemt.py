from providers.telemt_manager import TelemtProvider


def test_tls_link_returns_first_link():
    assert TelemtProvider._tls_link(
        {"links": {"tls": ["tg://proxy?first", "tg://proxy?second"]}}
    ) == "tg://proxy?first"


def test_tls_link_handles_missing_links():
    assert TelemtProvider._tls_link({}) is None


def test_create_response_shape():
    response = {
        "data": {
            "user": {"links": {"tls": ["tg://proxy?test"]}},
            "secret": "a" * 32,
        }
    }

    assert response["data"]["secret"] == "a" * 32
    assert TelemtProvider._tls_link(response["data"]["user"]) == "tg://proxy?test"
