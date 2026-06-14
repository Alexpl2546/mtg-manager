import json

from utils import storage


def test_write_json_replaces_file_atomically(tmp_path):
    target = tmp_path / "clients.json"

    storage._write_json(target, {"client": {"port": 12345}})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "client": {"port": 12345}
    }
    assert not target.with_suffix(".json.tmp").exists()


def test_read_json_returns_default_for_empty_file(tmp_path):
    target = tmp_path / "clients.json"
    target.write_text("", encoding="utf-8")

    assert storage._read_json(target, {}) == {}
