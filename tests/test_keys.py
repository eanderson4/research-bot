import json

from research_bot import keys


def _clear_key_env(monkeypatch):
    for envs in keys.ENV_KEY_MAP.values():
        for e in envs:
            monkeypatch.delenv(e, raising=False)


def test_keys_file_loaded(tmp_path, monkeypatch):
    _clear_key_env(monkeypatch)
    kf = tmp_path / "keys.json"
    kf.write_text(json.dumps({"deepseek_api_key": " sk-x ", "kagi_api_key": ""}))
    monkeypatch.setenv("RESEARCH_KEYS_FILE", str(kf))
    ks = keys.load_keys()
    assert ks["deepseek_api_key"] == "sk-x"  # stripped
    assert "kagi_api_key" not in ks          # empty values dropped


def test_env_overrides_file(tmp_path, monkeypatch):
    _clear_key_env(monkeypatch)
    kf = tmp_path / "keys.json"
    kf.write_text(json.dumps({"deepseek_api_key": "from-file"}))
    monkeypatch.setenv("RESEARCH_KEYS_FILE", str(kf))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    assert keys.load_keys()["deepseek_api_key"] == "from-env"


def test_missing_file_is_fine(tmp_path, monkeypatch):
    _clear_key_env(monkeypatch)
    monkeypatch.setenv("RESEARCH_KEYS_FILE", str(tmp_path / "nope.json"))
    monkeypatch.setattr(keys.Path, "home", lambda: tmp_path)
    assert keys.load_keys() == {}
