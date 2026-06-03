from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FileRecord:
    path: str
    filename: str
    parent_dir: str
    relative_path: str
    extension: str
    detected_platform: str = "unknown"
    keyword: str = ""
    status: str = "pending"
    error: str = ""


@dataclass
class DetectionResult:
    platform: str
    keyword: str
    confidence: float
    source: str
    reason: str
    need_manual_confirm: bool = False


@dataclass
class AIEvent:
    task_id: str = ""
    task_type: str = ""
    platform: str = ""
    filename: str = ""
    sheet_name: str = ""
    row_number: Any = ""
    column_name: str = ""
    input_summary: str = ""
    rule_result: str = ""
    ai_result: str = ""
    confidence: float = 0.0
    accepted: bool = False
    accept_reason: str = ""
    reject_reason: str = ""
    status: str = ""
    error_message: str = ""
    raw_response: str = ""
    created_at: str = ""


@dataclass
class JDProcessResult:
    platform: str = "jd"
    keyword: str = ""
    aggregate_df: Any = None
    top10_dfs: Dict[str, Any] = field(default_factory=dict)
    clean_df: Any = None
    other_df: Any = None
    ai_review_df: Any = None
    report_dfs: Dict[str, Any] = field(default_factory=dict)
    five_level_df: Any = None
    output_path: str = ""
    source_files: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DouyinProcessResult:
    platform: str = "douyin"
    keyword: str = ""
    detail_df: Any = None
    integration_df: Any = None
    five_level_df: Any = None
    other_category_df: Any = None
    ai_review_df: Any = None
    failed_items_df: Any = None
    output_path: str = ""
    source_files: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FinalProcessResult:
    output_dir: str = ""
    final_workbook_path: str = ""
    jd_workbook_path: str = ""
    douyin_workbook_path: str = ""
    zip_path: str = ""
    log_path: str = ""
    detection_report_df: Any = None
    error_report_df: Any = None
    ai_report_dfs: Dict[str, Any] = field(default_factory=dict)
