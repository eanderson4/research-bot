import json

from research_bot import store


def test_pair_paths_deterministic_and_sanitized(tmp_path):
    url = "https://ex.com/a b/../<script>?q=1&r=2"
    j1, m1 = store.pair_paths(tmp_path, url)
    j2, m2 = store.pair_paths(tmp_path, url)
    assert (j1, m1) == (j2, m2)
    assert j1.parent == tmp_path  # hostile key cannot traverse out of the store
    assert j1.name.endswith(".json") and m1.name.endswith(".md")
    for ch in "<>?&/ ":
        assert ch not in j1.name


def test_pair_paths_distinct_keys_distinct_files(tmp_path):
    j1, _ = store.pair_paths(tmp_path, "key-one")
    j2, _ = store.pair_paths(tmp_path, "key-two")
    assert j1 != j2


def test_write_pair_round_trip_no_temp_leftovers(tmp_path):
    jp, mp = store.pair_paths(tmp_path, "k")
    store.write_pair(jp, mp, {"ts": "2026-01-01", "n": 3}, "body text")
    assert json.loads(jp.read_text())["n"] == 3
    assert mp.read_text() == "body text\n"
    assert list(tmp_path.glob("*.tmp*")) == []
