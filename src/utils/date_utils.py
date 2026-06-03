import re
from typing import Optional

from .text_utils import normalize_text


def normalize_month_text(text: str) -> Optional[str]:
    value = normalize_text(text)
    if not value:
        return None
    value = value.replace("_", "-").replace("/", "-").replace(".", "-")
    patterns = [
        r"(20\d{2})\s*年\s*(0?[1-9]|1[0-2])\s*月",
        r"(20\d{2})-(0?[1-9]|1[0-2])",
        r"(20\d{2})(0[1-9]|1[0-2])(?:[0-3]\d)?(?:\D+20\d{2}(?:0[1-9]|1[0-2])(?:[0-3]\d)?)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
    return None


def extract_month_from_filename(filename: str) -> Optional[str]:
    return normalize_month_text(filename)


def validate_month_input(text: str) -> str:
    month = normalize_month_text(text)
    if not month:
        raise ValueError("月份格式错误，请输入类似 2025年5月、2025-05 或 202505。")
    return month


def month_to_sort_key(month_text: str):
    month = normalize_month_text(month_text)
    if not month:
        return (9999, 99)
    year, month_num = month.split("-")
    return int(year), int(month_num)


def month_to_chinese(month_text: str) -> str:
    month = normalize_month_text(month_text)
    if not month:
        return "未识别月份"
    year, month_num = month.split("-")
    return f"{int(year)}年{int(month_num)}月"


def parse_month_with_ai_fallback(filename: str, parent_dir: str = "", ai_orchestrator=None, **kwargs) -> str:
    for candidate in [filename, parent_dir]:
        month = normalize_month_text(candidate)
        if month:
            return month
    if ai_orchestrator:
        result = ai_orchestrator.infer_date_month_ai(filename=filename, parent_dir=parent_dir, **kwargs)
        month = normalize_month_text(result.get("month")) if isinstance(result, dict) else None
        if month:
            return month
    return "未识别月份"
