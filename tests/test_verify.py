from research_bot.verify import parse_overall, source_urls, split_sections


def test_parse_overall_pass():
    text = "CLAIM: x | VERDICT: SUPPORTED | EVIDENCE: y\nOVERALL: PASS supported=12 distorted=0 unsupported=1"
    got = parse_overall(text)
    assert got == {"passed": True, "supported": 12, "distorted": 0, "unsupported": 1}


def test_parse_overall_fail_case_insensitive():
    got = parse_overall("overall: fail supported=3 distorted=2 unsupported=5")
    assert got["passed"] is False
    assert got["distorted"] == 2


def test_parse_overall_absent():
    assert parse_overall("no verdict here") is None
    assert parse_overall("") is None
    assert parse_overall(None) is None


NOTES_TWO_SOURCES = """# notes
### https://example.com/a
Fact from A: 42 widgets.

### https://example.com/b
Fact from B: 7 sprockets.
More about B.
"""


def test_source_urls_dedup_and_order():
    text = "### https://x.com/1\nbody\n### https://x.com/2\n### https://x.com/1\n"
    assert source_urls(text) == ["https://x.com/1", "https://x.com/2"]


def test_source_urls_strips_trailing_punctuation():
    assert source_urls("## Source: https://x.com/page).\n") == ["https://x.com/page"]


def test_split_sections_isolates_each_source():
    sections = split_sections(NOTES_TWO_SOURCES)
    assert set(sections) == {"https://example.com/a", "https://example.com/b"}
    assert "42 widgets" in sections["https://example.com/a"]
    assert "sprockets" not in sections["https://example.com/a"]
    assert "More about B" in sections["https://example.com/b"]


def test_split_sections_single_source_keeps_full_text():
    text = "# notes: https://example.com/only\npreamble outside headings\nfacts here\n"
    sections = split_sections(text)
    assert sections == {"https://example.com/only": text}


def test_split_sections_merges_repeated_source():
    text = "### https://x.com/1\nfirst\n### https://x.com/2\nother\n### https://x.com/1\nsecond\n"
    sections = split_sections(text)
    assert "first" in sections["https://x.com/1"]
    assert "second" in sections["https://x.com/1"]
    assert "other" not in sections["https://x.com/1"]
