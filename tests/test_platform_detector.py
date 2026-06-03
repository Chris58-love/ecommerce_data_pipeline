from src.detection.platform_detector import PlatformDetector
from src.models import FileRecord


def make_record(parent):
    return FileRecord(path="missing.xlsx", filename="data.xlsx", parent_dir=parent, relative_path=f"{parent}/data.xlsx", extension=".xlsx")


def test_jd_folder_rule():
    result = PlatformDetector(ai_fallback_enabled=False).detect(make_record("京东数据-口臭"))
    assert result.platform == "jd"
    assert result.keyword == "口臭"


def test_jd_folder_rule_english():
    assert PlatformDetector(ai_fallback_enabled=False).detect(make_record("JD数据-口臭")).platform == "jd"


def test_douyin_folder_rule():
    result = PlatformDetector(ai_fallback_enabled=False).detect(make_record("抖音数据-牙结石"))
    assert result.platform == "douyin"
    assert result.keyword == "牙结石"


def test_douyin_folder_rule_english():
    assert PlatformDetector(ai_fallback_enabled=False).detect(make_record("douyin数据-牙结石")).platform == "douyin"


def test_unknown_folder_rule():
    result = PlatformDetector(ai_fallback_enabled=False).detect(make_record("未知文件夹"))
    assert result.platform == "unknown"
