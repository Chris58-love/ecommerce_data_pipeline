from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import uuid4

import pandas as pd

from src.models import AIEvent


class AIAuditLogger:
    def __init__(self):
        self.events = []

    def log_event(self, **kwargs) -> AIEvent:
        event = AIEvent(
            task_id=kwargs.get("task_id") or str(uuid4()),
            task_type=kwargs.get("task_type", ""),
            platform=kwargs.get("platform", ""),
            filename=kwargs.get("filename", ""),
            sheet_name=kwargs.get("sheet_name", ""),
            row_number=kwargs.get("row_number", ""),
            column_name=kwargs.get("column_name", ""),
            input_summary=kwargs.get("input_summary", ""),
            rule_result=kwargs.get("rule_result", ""),
            ai_result=kwargs.get("ai_result", ""),
            confidence=float(kwargs.get("confidence") or 0),
            accepted=bool(kwargs.get("accepted", False)),
            accept_reason=kwargs.get("accept_reason", ""),
            reject_reason=kwargs.get("reject_reason", ""),
            status=kwargs.get("status", ""),
            error_message=kwargs.get("error_message", ""),
            raw_response=str(kwargs.get("raw_response", "")),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.events.append(event)
        return event

    def to_dataframe(self):
        columns = [
            "AI任务ID", "AI任务类型", "平台", "文件名", "工作表名", "行号", "列名", "输入摘要",
            "规则结果", "AI返回结果", "AI置信度", "是否采纳", "采纳原因", "未采纳原因",
            "状态", "错误信息", "原始返回", "创建时间",
        ]
        rows = []
        for event in self.events:
            rows.append([
                event.task_id, event.task_type, event.platform, event.filename, event.sheet_name,
                event.row_number, event.column_name, event.input_summary, event.rule_result,
                event.ai_result, event.confidence, event.accepted, event.accept_reason,
                event.reject_reason, event.status, event.error_message, event.raw_response, event.created_at,
            ])
        return pd.DataFrame(rows, columns=columns)

    def build_summary_dataframe(self):
        df = self.to_dataframe()
        if df.empty:
            return pd.DataFrame([{"AI调用次数": 0, "AI采纳次数": 0, "AI异常次数": 0}])
        return pd.DataFrame([{
            "AI调用次数": len(df),
            "AI采纳次数": int(df["是否采纳"].sum()),
            "AI异常次数": int((df["状态"] == "error").sum()),
        }])

    def build_rejected_dataframe(self):
        df = self.to_dataframe()
        return df[(df["是否采纳"] == False) & (df["状态"] != "error")].copy() if not df.empty else df

    def build_error_dataframe(self):
        df = self.to_dataframe()
        return df[df["状态"] == "error"].copy() if not df.empty else df
