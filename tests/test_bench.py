from research_bot.bench import extract_json


def test_extract_json_plain():
    assert extract_json('{"overall": 7}') == {"overall": 7}


def test_extract_json_with_prose_and_fences():
    text = 'Here is my score:\n```json\n{"scores": {"coverage": 8}, "overall": 7.5}\n```\nDone.'
    assert extract_json(text)["overall"] == 7.5


def test_extract_json_skips_leading_garbage_braces():
    assert extract_json("{not json} then {\"ok\": true}") == {"ok": True}


def test_extract_json_none_cases():
    assert extract_json("no json at all") is None
    assert extract_json("") is None
    assert extract_json(None) is None
