from src.ai.ai_schemas import ALLOWED_PLATFORMS
from src.ai.deepseek_client import DeepSeekClient
from src.platforms.category_rules import accept_ai_category


def test_low_confidence_category_rejected():
    assert not accept_ai_category({"category": "医疗器械", "confidence": 0.5})


def test_invalid_platform_rejected():
    assert "tmall" not in ALLOWED_PLATFORMS


def test_invalid_category_rejected():
    assert not accept_ai_category({"category": "不存在", "confidence": 0.99})


def test_missing_column_rejected():
    actual_columns = {"搜索人数", "成交金额"}
    ai_mapping = {"搜索人数": "搜索人数", "点击人数": "不存在列"}
    accepted = {k: v for k, v in ai_mapping.items() if v in actual_columns}
    assert "点击人数" not in accepted


def test_no_api_key_not_fatal(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = DeepSeekClient({"enabled": True})
    assert client.chat_json("system", "{}") is None
