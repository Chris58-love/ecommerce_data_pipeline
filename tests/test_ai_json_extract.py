from src.utils.json_utils import extract_first_json_object


def test_plain_json():
    assert extract_first_json_object('{"a":1}') == {"a": 1}


def test_markdown_json():
    assert extract_first_json_object('```json\n{"a":1}\n```') == {"a": 1}


def test_text_around_json():
    assert extract_first_json_object('说明 {"a":1} 结束') == {"a": 1}


def test_invalid_json():
    assert extract_first_json_object("not json") is None
