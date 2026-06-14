from utils.validation import normalize_client_name, validate_client_name


def test_normalize_client_name():
    assert normalize_client_name("  Test User  ") == "test_user"


def test_validate_client_name():
    assert validate_client_name("client-01")
    assert not validate_client_name("a")
    assert not validate_client_name("../client")
    assert not validate_client_name('name = "secret"')
