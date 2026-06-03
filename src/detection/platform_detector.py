import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.models import DetectionResult, FileRecord
from src.utils.text_utils import extract_keyword_from_folder_name, normalize_col_name, normalize_text


JD_HINTS = {"关键词", "搜索人数", "搜索次数", "点击人数", "点击次数", "点击率", "成交金额", "成交单量", "成交转化率", "在线商品数"}
DOUYIN_HINTS = {"商品标题", "细分类目", "销量", "销售额", "浏览量", "订单量", "日期"}


def _name_rule(text: str):
    value = normalize_text(text)
    lower = value.lower()
    if any(k in value for k in ["京东"]) or any(k in lower for k in ["jd", "jingdong"]):
        return "jd"
    if any(k in value for k in ["抖音"]) or any(k in lower for k in ["douyin", "dy"]):
        return "douyin"
    return "unknown"


def _extract_keyword(record: FileRecord) -> str:
    keyword = extract_keyword_from_folder_name(record.parent_dir)
    if keyword:
        return keyword
    for marker in ["京东", "JD", "jd", "jingdong", "抖音", "douyin", "dy"]:
        name = Path(record.filename).stem
        lower_name = name.lower()
        if marker.lower() in lower_name:
            parts = name.replace("_", "-").replace("—", "-").split("-")
            if len(parts) > 1:
                return normalize_text(parts[-1])
    return ""


def _read_schema_sample(path: str) -> Dict:
    sheet_names, headers, samples = [], [], []
    ext = Path(path).suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(path, nrows=5, dtype=object, encoding="utf-8-sig")
            sheet_names = ["CSV"]
            headers = list(df.columns)
            samples = df.head(3).fillna("").astype(str).values.tolist()
        else:
            excel = pd.ExcelFile(path)
            sheet_names = excel.sheet_names[:8]
            for sheet in sheet_names[:3]:
                df = pd.read_excel(excel, sheet_name=sheet, nrows=8, dtype=object)
                headers.extend([str(col) for col in df.columns if str(col) != "nan"])
                samples.extend(df.head(3).fillna("").astype(str).values.tolist())
    except Exception as exc:
        logging.warning("读取结构样本失败 %s: %s", path, exc)
    return {"sheet_names": sheet_names, "headers": headers, "samples": samples}


def _schema_rule(sample: Dict) -> DetectionResult:
    text = {normalize_col_name(x) for x in sample.get("headers", [])}
    flat_rows = {normalize_col_name(x) for row in sample.get("samples", []) for x in row}
    names = text | flat_rows
    jd_score = sum(1 for hint in JD_HINTS if normalize_col_name(hint) in names)
    douyin_score = sum(1 for hint in DOUYIN_HINTS if normalize_col_name(hint) in names)
    if jd_score >= 3 and jd_score > douyin_score:
        return DetectionResult("jd", "", min(0.95, 0.55 + jd_score * 0.08), "schema_rule", f"命中京东字段 {jd_score} 个")
    if douyin_score >= 3 and douyin_score > jd_score:
        return DetectionResult("douyin", "", min(0.95, 0.55 + douyin_score * 0.08), "schema_rule", f"命中抖音字段 {douyin_score} 个")
    return DetectionResult("unknown", "", 0.0, "unknown", "规则未识别", True)


class PlatformDetector:
    def __init__(self, ai_orchestrator=None, min_confidence: float = 0.75, ai_fallback_enabled: bool = True):
        self.ai = ai_orchestrator
        self.min_confidence = min_confidence
        self.ai_fallback_enabled = ai_fallback_enabled

    def detect(self, record: FileRecord) -> DetectionResult:
        keyword = _extract_keyword(record)
        parent_platform = _name_rule(record.parent_dir)
        if parent_platform != "unknown":
            return DetectionResult(parent_platform, keyword, 0.95, "folder_rule", f"父级目录命中 {parent_platform}")

        file_platform = _name_rule(record.filename)
        if file_platform != "unknown":
            return DetectionResult(file_platform, keyword, 0.85, "file_rule", f"文件名命中 {file_platform}")

        sample = _read_schema_sample(record.path)
        schema_result = _schema_rule(sample)
        if schema_result.platform != "unknown" and schema_result.confidence >= self.min_confidence:
            schema_result.keyword = keyword
            return schema_result

        if self.ai_fallback_enabled and self.ai:
            ai_result = self.ai.detect_platform_ai(
                filename=record.filename,
                parent_dir=record.parent_dir,
                relative_path=record.relative_path,
                sheet_names=sample.get("sheet_names", []),
                headers=sample.get("headers", [])[:50],
                samples=sample.get("samples", [])[:5],
            )
            platform = ai_result.get("platform", "unknown")
            confidence = float(ai_result.get("confidence") or 0)
            if platform in {"jd", "douyin", "unknown"} and confidence >= self.min_confidence:
                return DetectionResult(platform, ai_result.get("keyword") or keyword, confidence, "ai", ai_result.get("reason", "AI识别"))
            return DetectionResult("unknown", keyword, confidence, "ai", ai_result.get("reason", "AI置信度不足"), True)

        schema_result.keyword = keyword
        schema_result.need_manual_confirm = True
        return schema_result
