import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from src.constants import (
    ERROR_COLUMNS,
    FIXED_OUTPUT_CATEGORIES,
    JD_ABSOLUTE_METRICS,
    JD_CLEAN_METRICS,
    JD_COLUMN_ALIASES,
    JD_PRODUCT_COLUMNS,
    JD_TOP10_METRICS,
)
from src.models import FileRecord, JDProcessResult
from src.platforms.category_rules import accept_ai_category, classify_jd_keyword
from src.utils.date_utils import parse_month_with_ai_fallback
from src.utils.excel_format import write_dataframes_to_workbook
from src.utils.numeric_parser import parse_metric_value
from src.utils.text_utils import normalize_col_name, normalize_text


TOP10_OUTPUT_COLUMNS = [
    "月份", "排名", "关键词", "原始值", "排序值", "搜索人数", "搜索次数", "点击人数", "点击次数",
    "点击率", "成交金额", "成交单量", "成交转化率", "在线商品数", "来源文件", "来源工作表",
]


def read_table(path: str) -> Dict[str, pd.DataFrame]:
    ext = Path(path).suffix.lower()
    if ext == ".csv":
        return {"CSV": pd.read_csv(path, dtype=object, encoding="utf-8-sig")}
    excel = pd.ExcelFile(path)
    return {sheet: pd.read_excel(excel, sheet_name=sheet, dtype=object) for sheet in excel.sheet_names}


def find_column(columns, candidates) -> Optional[str]:
    normalized = {normalize_col_name(col): col for col in columns}
    for candidate in candidates:
        key = normalize_col_name(candidate)
        if key in normalized:
            return normalized[key]
    for candidate in candidates:
        key = normalize_col_name(candidate)
        for norm, original in normalized.items():
            if key and (key in norm or norm in key):
                return original
    return None


class JDProcessor:
    def __init__(self, output_dir: str, ai_orchestrator=None):
        self.output_dir = output_dir
        self.ai = ai_orchestrator

    def review_ai_category(self, keyword: str, rule_category: str = "其他") -> dict:
        if not self.ai:
            return {"accepted": False, "category": rule_category, "confidence": 0.0, "reason": "AI不可用"}
        result = self.ai.classify_category_ai("jd", [{"keyword": keyword, "rule_category": rule_category}])
        items = result.get("items") if isinstance(result, dict) else None
        item = items[0] if items else result
        accepted = accept_ai_category(item or {})
        return {
            "accepted": accepted,
            "category": item.get("category", rule_category) if accepted else rule_category,
            "confidence": float(item.get("confidence") or 0) if item else 0,
            "reason": item.get("reason", "") if item else "AI无结果",
        }

    def process(self, records: List[FileRecord]) -> JDProcessResult:
        clean_frames, full_frames, errors, reports = [], [], [], []
        top10_records = {metric: [] for metric in JD_TOP10_METRICS}
        ai_review_rows = []
        source_files = [r.filename for r in records]
        keyword = next((r.keyword for r in records if r.keyword), "")

        for record in records:
            month = parse_month_with_ai_fallback(record.filename, record.parent_dir, self.ai)
            try:
                sheets = read_table(record.path)
            except Exception as exc:
                errors.append(["jd", record.filename, "", "", "", "", "文件读取失败", str(exc), "跳过该文件"])
                continue
            for sheet_name, df in sheets.items():
                try:
                    result = self._process_sheet(df, record, sheet_name, month, top10_records, errors, ai_review_rows)
                    full_frames.append(result["full_df"])
                    clean_frames.append(result["clean_df"])
                    reports.append(result["report"])
                except Exception as exc:
                    logging.exception("京东 sheet 处理失败 %s %s", record.filename, sheet_name)
                    errors.append(["jd", record.filename, sheet_name, "", "", "", "Sheet处理失败", str(exc), "跳过该Sheet"])

        clean_df = pd.concat(clean_frames, ignore_index=True) if clean_frames else self.empty_clean_df()
        full_df = pd.concat(full_frames, ignore_index=True) if full_frames else pd.DataFrame()
        aggregate_df, other_df, five_level_df = self._aggregate(clean_df, keyword)
        top10_dfs = {metric: self._build_top10_df(rows) for metric, rows in top10_records.items()}
        ai_review_df = pd.DataFrame(ai_review_rows, columns=["关键词", "规则分类", "AI分类", "AI置信度", "是否采纳", "原因"])
        report_df = pd.DataFrame(reports)
        error_df = pd.DataFrame(errors, columns=ERROR_COLUMNS)

        output_path = str(Path(self.output_dir) / "京东_清洗整合结果.xlsx")
        sheets = {
            "所有月份整合数据": aggregate_df,
            **top10_dfs,
            "清洗后数据": clean_df,
            "其他类别商品": other_df,
            "AI分类审核明细": ai_review_df,
            "处理报告": report_df,
            "清洗错误明细": error_df,
        }
        write_dataframes_to_workbook(output_path, sheets)
        return JDProcessResult(keyword=keyword, aggregate_df=aggregate_df, top10_dfs=top10_dfs, clean_df=clean_df, other_df=other_df, ai_review_df=ai_review_df, report_dfs={"处理报告": report_df, "清洗错误明细": error_df, "full_df": full_df}, five_level_df=five_level_df, output_path=output_path, source_files=source_files, errors=[dict(zip(ERROR_COLUMNS, row)) for row in errors])

    def _process_sheet(self, df, record, sheet_name, month, top10_records, errors, ai_review_rows):
        df = df.dropna(how="all").copy()
        product_col = find_column(df.columns, JD_PRODUCT_COLUMNS)
        metric_mapping = {metric: find_column(df.columns, aliases) for metric, aliases in JD_COLUMN_ALIASES.items()}
        missing = [metric for metric, col in metric_mapping.items() if col is None]
        if missing and self.ai:
            ai_mapping = self.ai.infer_columns_ai(missing, [str(c) for c in df.columns], platform="jd", filename=record.filename, sheet_name=sheet_name)
            metric_mapping.update({key: value for key, value in ai_mapping.items() if key in metric_mapping})
        if not product_col:
            product_col = df.columns[0] if len(df.columns) else "关键词"

        full_df = df.copy()
        full_df.insert(0, "来源工作表", sheet_name)
        full_df.insert(0, "来源文件", record.filename)
        full_df.insert(0, "月份", month)
        full_df["关键词"] = df[product_col].map(normalize_text) if product_col in df.columns else ""

        clean_rows = []
        success_count = 0
        fail_count = 0
        for idx, row in df.iterrows():
            clean_row = {"月份": month, "来源文件": record.filename, "来源工作表": sheet_name, "关键词": normalize_text(row.get(product_col, ""))}
            for metric, col in metric_mapping.items():
                raw_value = row.get(col, None) if col else None
                ok, parsed, reason, status = parse_metric_value(raw_value, metric, "amount" if metric == "成交金额" else "integer")
                clean_col = f"{metric}_clean"
                clean_row[clean_col] = parsed if ok else 0
                full_df.loc[idx, clean_col] = parsed if ok else None
                if ok:
                    success_count += 1
                elif status == "error":
                    fail_count += 1
                    errors.append(["jd", record.filename, sheet_name, int(idx) + 2, col or metric, raw_value, "数值解析失败", reason, "置空并继续"])
            category, confidence, reason = classify_jd_keyword(clean_row["关键词"])
            if category == "其他" or confidence < 0.7:
                ai_result = self.review_ai_category(clean_row["关键词"], category)
                ai_review_rows.append([clean_row["关键词"], category, ai_result["category"], ai_result["confidence"], ai_result["accepted"], ai_result["reason"]])
                if ai_result["accepted"]:
                    category = ai_result["category"]
            clean_row["类别"] = category
            clean_rows.append(clean_row)

        self._collect_top10(df, record, sheet_name, month, product_col, top10_records)
        report = {
            "文件名": record.filename,
            "工作表名": sheet_name,
            "月份": month,
            "总行数": len(df),
            "识别商品列": product_col,
            "识别指标列数": sum(1 for col in metric_mapping.values() if col),
            "缺失指标列数": sum(1 for col in metric_mapping.values() if not col),
            "成功解析单元格数": success_count,
            "失败单元格数": fail_count,
            "状态": "成功" if len(df) else "空表",
        }
        return {"full_df": full_df, "clean_df": pd.DataFrame(clean_rows), "report": report}

    def _collect_top10(self, df, record, sheet_name, month, product_col, top10_records):
        display_cols = {metric: find_column(df.columns, aliases) for metric, aliases in {
            "搜索人数": JD_COLUMN_ALIASES["搜索人数"], "搜索次数": JD_COLUMN_ALIASES["搜索次数"],
            "点击人数": JD_COLUMN_ALIASES["点击人数"], "点击次数": JD_COLUMN_ALIASES["点击次数"],
            "点击率": ["点击率", "搜索点击率", "CTR", "点击率区间", "搜索点击率区间"],
            "成交金额": JD_COLUMN_ALIASES["成交金额"], "成交单量": JD_COLUMN_ALIASES["成交单量"],
            "成交转化率": ["成交转化率", "转化率", "交易转化率", "支付转化率", "下单转化率"],
            "在线商品数": JD_COLUMN_ALIASES["在线商品数"],
        }.items()}
        for metric, cfg in JD_TOP10_METRICS.items():
            col = find_column(df.columns, cfg["aliases"])
            if not col:
                continue
            rows = []
            for _, row in df.iterrows():
                ok, parsed, _, _ = parse_metric_value(row.get(col), metric, cfg["type"])
                if not ok:
                    continue
                rows.append({
                    "月份": month,
                    "关键词": normalize_text(row.get(product_col, "")),
                    "原始值": row.get(col),
                    "排序值": parsed,
                    **{name: row.get(src, "") if src else "" for name, src in display_cols.items()},
                    "来源文件": record.filename,
                    "来源工作表": sheet_name,
                })
            rows = sorted(rows, key=lambda x: x["排序值"], reverse=True)[:10]
            for rank, row in enumerate(rows, 1):
                row["排名"] = rank
                top10_records[metric].append(row)

    def _build_top10_df(self, rows):
        if not rows:
            return pd.DataFrame(columns=TOP10_OUTPUT_COLUMNS)
        return pd.DataFrame(rows)[TOP10_OUTPUT_COLUMNS]

    def _aggregate(self, clean_df, keyword):
        if clean_df.empty:
            aggregate_cols = ["月份", "类别"] + JD_CLEAN_METRICS
            return pd.DataFrame(columns=aggregate_cols), pd.DataFrame(), pd.DataFrame()
        for col in JD_CLEAN_METRICS:
            if col not in clean_df.columns:
                clean_df[col] = 0
            clean_df[col] = pd.to_numeric(clean_df[col], errors="coerce").fillna(0)
        months = sorted([m for m in clean_df["月份"].dropna().unique() if m], key=lambda x: str(x))
        valid = clean_df[clean_df["类别"].isin(FIXED_OUTPUT_CATEGORIES)].copy()
        grouped = valid.groupby(["月份", "类别"], as_index=False)[JD_CLEAN_METRICS].sum() if not valid.empty else pd.DataFrame()
        rows = []
        for month in months:
            for category in FIXED_OUTPUT_CATEGORIES:
                row = {"月份": month, "类别": category}
                matched = grouped[(grouped["月份"] == month) & (grouped["类别"] == category)] if not grouped.empty else pd.DataFrame()
                for metric in JD_CLEAN_METRICS:
                    row[metric] = float(matched.iloc[0][metric]) if not matched.empty else 0
                rows.append(row)
        aggregate_df = pd.DataFrame(rows, columns=["月份", "类别"] + JD_CLEAN_METRICS)
        other_df = clean_df[clean_df["类别"] == "其他"].copy()
        five_level_df = aggregate_df.rename(columns={"月份": "时间", "类别": "分类名"})
        five_level_df.insert(0, "主题关键词", keyword)
        five_level_df.insert(0, "平台", "jd")
        five_level_df["来源文件"] = ",".join(sorted(set(clean_df["来源文件"].dropna().astype(str))))
        return aggregate_df, other_df, five_level_df

    @staticmethod
    def empty_clean_df():
        return pd.DataFrame(columns=["月份", "来源文件", "来源工作表", "关键词"] + JD_CLEAN_METRICS + ["类别"])
