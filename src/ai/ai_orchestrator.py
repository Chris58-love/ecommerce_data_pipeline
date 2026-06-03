from typing import Dict, Iterable, Optional

from src.ai.ai_confidence import threshold
from src.ai.ai_schemas import ALLOWED_CATEGORIES, ALLOWED_PLATFORMS, ALLOWED_SHEET_TYPES
from src.ai.prompts import (
    build_category_review_prompt,
    build_column_mapping_prompt,
    build_date_inference_prompt,
    build_error_fix_prompt,
    build_final_summary_prompt,
    build_keyword_extraction_prompt,
    build_merge_consistency_prompt,
    build_numeric_anomaly_review_prompt,
    build_platform_detection_prompt,
    build_sheet_type_detection_prompt,
    build_top10_review_prompt,
)


class AIOrchestrator:
    def __init__(self, client, audit_logger, enabled: bool = True):
        self.client = client
        self.audit = audit_logger
        self.enabled = enabled
        self.system_prompt = "你是电商数据清洗助手，必须只输出严格 JSON。"

    def _call(self, task_type, prompt, platform="", filename="", sheet_name="", rule_result="", input_summary=""):
        if not self.enabled or not self.client or not self.client.is_available():
            self.audit.log_event(task_type=task_type, platform=platform, filename=filename, sheet_name=sheet_name, input_summary=input_summary, rule_result=rule_result, status="skipped", reject_reason="AI未启用或缺少API Key")
            return None
        result = self.client.chat_json(self.system_prompt, prompt)
        if result is None:
            self.audit.log_event(task_type=task_type, platform=platform, filename=filename, sheet_name=sheet_name, input_summary=input_summary, rule_result=rule_result, status="error", error_message="AI返回为空或非法JSON")
        return result

    def detect_platform_ai(self, filename, parent_dir, relative_path, sheet_names, headers, samples) -> Dict:
        prompt = build_platform_detection_prompt(filename, parent_dir, relative_path, sheet_names, headers, samples)
        result = self._call("platform_detection", prompt, filename=filename, input_summary=relative_path)
        if not result:
            return {"platform": "unknown", "keyword": "", "confidence": 0.0, "reason": "AI不可用"}
        platform = result.get("platform", "unknown")
        conf = float(result.get("confidence") or 0)
        accepted = platform in ALLOWED_PLATFORMS and conf >= threshold("platform_detection")
        self.audit.log_event(task_type="platform_detection", filename=filename, input_summary=relative_path, ai_result=str(result), confidence=conf, accepted=accepted, accept_reason="置信度达标" if accepted else "", reject_reason="" if accepted else "平台非法或置信度不足", status="success")
        return result if accepted else {**result, "platform": "unknown"}

    def extract_keyword_ai(self, filename, parent_dir):
        prompt = build_keyword_extraction_prompt(filename, parent_dir)
        result = self._call("keyword_extraction", prompt, filename=filename)
        return result or {"keyword": "", "confidence": 0.0, "reason": "AI不可用"}

    def detect_sheet_type_ai(self, sheet_name, headers, samples):
        prompt = build_sheet_type_detection_prompt(sheet_name, headers, samples)
        result = self._call("sheet_type_detection", prompt, sheet_name=sheet_name)
        if not result or result.get("sheet_type") not in ALLOWED_SHEET_TYPES:
            return {"sheet_type": "unknown", "confidence": 0.0}
        return result

    def infer_columns_ai(self, required_columns, actual_columns, **kwargs):
        prompt = build_column_mapping_prompt(required_columns, actual_columns)
        result = self._call("column_mapping", prompt, **kwargs)
        if not result:
            return {}
        mapping = result.get("mapping") or {}
        actual_set = set(actual_columns)
        accepted = {key: value for key, value in mapping.items() if value in actual_set}
        rejected = len(accepted) != len(mapping)
        self.audit.log_event(task_type="column_mapping", ai_result=str(result), confidence=float(result.get("confidence") or 0), accepted=not rejected and float(result.get("confidence") or 0) >= threshold("column_mapping"), reject_reason="存在AI编造列名" if rejected else "")
        return accepted if float(result.get("confidence") or 0) >= threshold("column_mapping") else {}

    def infer_date_month_ai(self, filename, parent_dir="", **kwargs):
        prompt = build_date_inference_prompt(filename, parent_dir, kwargs.get("sheet_names"), kwargs.get("samples"))
        result = self._call("date_inference", prompt, filename=filename)
        if not result:
            return {"month": None, "confidence": 0.0}
        return result if float(result.get("confidence") or 0) >= threshold("date_inference") else {"month": None, "confidence": float(result.get("confidence") or 0)}

    def classify_category_ai(self, platform, items, filename="", sheet_name=""):
        prompt = build_category_review_prompt(platform, items, sorted(ALLOWED_CATEGORIES))
        return self._call("category_review", prompt, platform=platform, filename=filename, sheet_name=sheet_name, input_summary=str(items)) or {}

    def review_numeric_anomalies_ai(self, field_name, samples):
        return self._call("numeric_anomaly_review", build_numeric_anomaly_review_prompt(field_name, samples)) or {"can_auto_apply": False}

    def review_top10_ai(self, records):
        return self._call("top10_review", build_top10_review_prompt(records)) or {"issues": [], "summary": "AI不可用"}

    def review_merge_consistency_ai(self, summary):
        return self._call("merge_consistency_review", build_merge_consistency_prompt(summary)) or {"issues": [], "summary": "AI不可用"}

    def suggest_error_fix_ai(self, errors):
        return self._call("error_fix_suggestion", build_error_fix_prompt(errors)) or {"suggestions": [], "confidence": 0.0}

    def generate_processing_summary_ai(self, stats):
        result = self._call("final_summary", build_final_summary_prompt(stats))
        if result and result.get("summary"):
            return result
        return {"summary": f"本次共扫描 {stats.get('扫描文件数', 0)} 个文件，京东 {stats.get('京东文件数', 0)} 个，抖音 {stats.get('抖音文件数', 0)} 个。无 API Key 时已使用纯规则模式完成处理。", "confidence": 1.0}
