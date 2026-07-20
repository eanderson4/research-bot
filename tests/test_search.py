import research_bot.fetch as fetch_mod
from research_bot.search import ddg_search

DDG_FIXTURE = b"""
<html><body>
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fone&rut=x">First <b>Result</b></a>
  <a class="result__snippet" href="#">Snippet one &amp; more</a>
</div>
<div class="result">
  <a class="result__a" href="https://example.org/two">Second</a>
</div>
</body></html>
"""


def test_ddg_search_parses_results(monkeypatch):
    monkeypatch.setattr(fetch_mod, "http_get", lambda url, timeout=30: (DDG_FIXTURE, "text/html"))
    results = ddg_search("anything", n=8)
    assert results[0]["url"] == "https://example.com/one"  # uddg redirect unwrapped
    assert results[0]["title"] == "First Result"           # tags stripped
    assert "Snippet one & more" in results[0]["snippet"]   # entities unescaped
    assert results[1]["url"] == "https://example.org/two"


def test_ddg_search_respects_n(monkeypatch):
    monkeypatch.setattr(fetch_mod, "http_get", lambda url, timeout=30: (DDG_FIXTURE, "text/html"))
    assert len(ddg_search("anything", n=1)) == 1


def test_ddg_search_empty_page_returns_empty(monkeypatch, capsys):
    monkeypatch.setattr(fetch_mod, "http_get", lambda url, timeout=30: (b"<html>blocked</html>", "text/html"))
    assert ddg_search("anything") == []
    assert "layout change or bot block" in capsys.readouterr().err
