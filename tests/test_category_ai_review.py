from src.platforms.category_rules import accept_ai_category


def test_jd_ai_accept_medical():
    assert accept_ai_category({"category": "医疗器械", "confidence": 0.9})


def test_jd_ai_reject_invalid():
    assert not accept_ai_category({"category": "家电", "confidence": 0.99})


def test_douyin_ai_accept_care():
    assert accept_ai_category({"category": "漱口水/护理用品", "confidence": 0.80})


def test_low_confidence_reject():
    assert not accept_ai_category({"category": "漱口水/护理用品", "confidence": 0.50})
