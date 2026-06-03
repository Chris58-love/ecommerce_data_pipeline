import math
import re
import unicodedata
from typing import Any, Optional, Tuple, Tuple


EMPTY_MARKERS = {"", "-", "--", "~", "~~", "/", "\\", "无", "暂无", "空", "nan", "none", "null", "不详"}
UNIT_FACTORS = {"": 1, "千": 1000, "k": 1000, "K": 1000, "万": 10000, "w": 10000, "W": 10000, "亿": 100000000}


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return ""
        return str(value)
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = text.replace("，", ",").replace(",", "")
    text = text.replace("人民币", "").replace("元", "").replace("￥", "").replace("¥", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("－", "-").replace("—", "-").replace("–", "-")
    text = text.replace("～", "~").replace("至", "~").replace("到", "~")
    text = text.replace("大于等于", "≥").replace("小于等于", "≤")
    text = text.replace("大于", ">").replace("小于", "<")
    return text


def parse_number_with_unit(text: Any) -> Optional[float]:
    cleaned = _normalize(text)
    if cleaned.lower() in EMPTY_MARKERS:
        return None
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)(千|万|亿|[kKwW])?", cleaned)
    if not match:
        return None
    return float(match.group(1)) * UNIT_FACTORS.get(match.group(2) or "", 1)


def _split_interval(text: str):
    if "~" in text:
        parts = text.split("~", 1)
    else:
        match = re.search(r"(?<=\d)-(?=\d)", text)
        if not match:
            return None
        parts = [text[: match.start()], text[match.end() :]]
    return parts if len(parts) == 2 else None


def parse_absolute_interval(value: Any) -> Optional[float]:
    text = _normalize(value)
    if text.lower() in EMPTY_MARKERS:
        return None
    if "%" in text:
        return None

    upper = re.fullmatch(r"(?:<|≤)(\d+(?:\.\d+)?)(千|万|亿|[kKwW])?", text) or re.fullmatch(
        r"(\d+(?:\.\d+)?)(千|万|亿|[kKwW])?以下", text
    )
    if upper:
        return float(upper.group(1)) * UNIT_FACTORS.get(upper.group(2) or "", 1) / 2

    lower = re.fullmatch(r"(?:>|≥)(\d+(?:\.\d+)?)(千|万|亿|[kKwW])?", text) or re.fullmatch(
        r"(\d+(?:\.\d+)?)(千|万|亿|[kKwW])?以上", text
    )
    if lower:
        return float(lower.group(1)) * UNIT_FACTORS.get(lower.group(2) or "", 1)

    parts = _split_interval(text)
    if parts:
        left = parse_number_with_unit(parts[0])
        right = parse_number_with_unit(parts[1])
        if left is None or right is None:
            return None
        return (left + right) / 2

    return parse_number_with_unit(text)


def parse_rate_interval(value: Any) -> Optional[float]:
    text = _normalize(value).replace("%", "")
    if text.lower() in EMPTY_MARKERS:
        return None

    upper = re.fullmatch(r"(?:<|≤)(\d+(?:\.\d+)?)", text) or re.fullmatch(r"(\d+(?:\.\d+)?)以下", text)
    if upper:
        return float(upper.group(1)) / 2

    lower = re.fullmatch(r"(?:>|≥)(\d+(?:\.\d+)?)", text) or re.fullmatch(r"(\d+(?:\.\d+)?)以上", text)
    if lower:
        return float(lower.group(1))

    parts = _split_interval(text)
    if parts:
        left = parse_number_with_unit(parts[0])
        right = parse_number_with_unit(parts[1])
        if left is None or right is None:
            return None
        return (left + right) / 2
    return parse_number_with_unit(text)


def parse_metric_value(value: Any, metric_name: str = "", metric_type: str = "absolute") -> Tuple[bool, Optional[float], str, str]:
    if metric_type == "rate":
        parsed = parse_rate_interval(value)
    else:
        if "%" in _normalize(value):
            return False, None, "绝对数字段出现百分比", "error"
        parsed = parse_absolute_interval(value)

    if parsed is None:
        if _normalize(value).lower() in EMPTY_MARKERS:
            return False, None, "空值", "empty"
        return False, None, "无法解析数值", "error"

    if metric_type in {"integer", "absolute"} and metric_name not in {"成交金额", "销售额", "amount"}:
        parsed = int(round(parsed))
    elif metric_type == "amount" or metric_name in {"成交金额", "销售额"}:
        parsed = round(float(parsed), 2)
    else:
        parsed = round(float(parsed), 4)
    return True, parsed, "", "success"
