import logging
from pathlib import Path
from typing import List

import pandas as pd

from src.constants import DOUYIN_DETAIL_COLUMNS, DOUYIN_NUMERIC_COLUMNS, ERROR_COLUMNS, FIXED_OUTPUT_CATEGORIES
from src.models import DouyinProcessResult, FileRecord
from src.platforms.category_rules import accept_ai_category, classify_douyin_category
from src.utils.date_utils import parse_month_with_ai_fallback
from src.utils.excel_format import write_dataframes_to_workbook
from src.utils.numeric_parser import parse_metric_value
from src.utils.text_utils import normalize_col_name, normalize_text


def _read_excel_sheets(path: str):
    excel = pd.ExcelFile(path)
    return {sheet: pd.read_excel(excel, sheet_name=sheet, header=None, dtype=object) for sheet in excel.sheet_names}


def _locate_header_and_data_row(df: pd.DataFrame):
    for idx in range(len(df)):
        row_values = [normalize_col_name(value) for value in df.iloc[idx].tolist()]
        if any("日期" in value for value in row_values):
            data_idx = idx + 1
            if data_idx >= len(df):
                raise ValueError("找到日期表头但下一行不存在")
            return idx, data_idx
    raise ValueError("未找到包含“日期”的数据表头行")


def _column_map(header_row):
    mapping = {}
    for idx, value in enumerate(header_row):
        key = normalize_col_name(value)
        if key:
            mapping[key] = idx
    return mapping


def _find_required_col(col_map, name):
    key = normalize_col_name(name)
    if key in col_map:
        return col_map[key]
    for col_key, idx in col_map.items():
        if key in col_key or col_key in key:
            return idx
    raise KeyError(f"缺少必要列: {name}")


def _extract_fine_category(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "未知"
    first_row = df.iloc[0].tolist()
    fine_col = None
    for idx, value in enumerate(first_row):
        if normalize_col_name(value) == "细分类目":
            fine_col = idx
            break
    if fine_col is None:
        return "未知"
    candidates = []
    if len(df) > 1 and fine_col < df.shape[1]:
        candidates.append(df.iat[1, fine_col])
    if fine_col + 1 < df.shape[1]:
        candidates.append(df.iat[0, fine_col + 1])
    for candidate in candidates:
        text = normalize_text(candidate)
        if text and normalize_col_name(text) != "细分类目":
            return text
    return "未知"


class DouyinProcessor:
    def __init__(self, output_dir: str, ai_orchestrator=None):
        self.output_dir = output_dir
        self.ai = ai_orchestrator

    def review_ai_category(self, title: str, fine_category: str, rule_category: str = "其他") -> dict:
        if not self.ai:
            return {"accepted": False, "category": rule_category, "confidence": 0.0, "reason": "AI不可用"}
        result = self.ai.classify_category_ai(
            "douyin",
            {"商品标题": title, "细分类目": fine_category, "本地规则分类结果": rule_category},
        )
        accepted = accept_ai_category(result or {})
        return {
            "accepted": accepted,
            "category": result.get("category", rule_category) if accepted else rule_category,
            "confidence": float(result.get("confidence") or 0) if result else 0,
            "reason": result.get("reason", "") if result else "AI无结果",
        }

    def process(self, records: List[FileRecord]) -> DouyinProcessResult:
        detail_rows, failed_rows, ai_rows, duplicate_rows = [], [], [], []
        source_files = [r.filename for r in records]
        keyword = next((r.keyword for r in records if r.keyword), "")

        for record in records:
            if record.extension == ".csv":
                failed_rows.append([record.filename, "", "抖音处理器暂不支持 CSV", "跳过"])
                continue
            month = parse_month_with_ai_fallback(record.filename, record.parent_dir, self.ai)
            try:
                sheets = _read_excel_sheets(record.path)
            except Exception as exc:
                failed_rows.append([record.filename, "", f"文件读取失败: {exc}", "跳过该文件"])
                continue
            for sheet_name, df in sheets.items():
                try:
                    row = self._extract_sheet_record(df, sheet_name, month, record.filename, ai_rows)
                    detail_rows.append(row)
                except Exception as exc:
                    logging.exception("抖音 sheet 处理失败 %s %s", record.filename, sheet_name)
                    failed_rows.append([record.filename, sheet_name, str(exc), "跳过该Sheet"])

        detail_df = pd.DataFrame(detail_rows, columns=DOUYIN_DETAIL_COLUMNS + ["来源文件", "来源工作表"])
        if not detail_df.empty:
            duplicate_mask = detail_df.duplicated(subset=["月份", "商品标题"], keep=False)
            if duplicate_mask.any():
                for _, row in detail_df[duplicate_mask].iterrows():
                    duplicate_rows.append([row["来源文件"], row["来源工作表"], f"同月商品重复: {row['月份']} {row['商品标题']}", "保留最后一次"])
                detail_df = detail_df.drop_duplicates(subset=["月份", "商品标题"], keep="last")
            detail_df = detail_df.sort_values(by=["月份", "商品标题"]).reset_index(drop=True)

        output_detail_df = detail_df[DOUYIN_DETAIL_COLUMNS].copy() if not detail_df.empty else pd.DataFrame(columns=DOUYIN_DETAIL_COLUMNS)
        integration_df = self._build_integration(output_detail_df)
        five_level_df = self._build_five_level(output_detail_df, keyword, source_files)
        other_df = output_detail_df[output_detail_df["五级分类"] == "其他"].copy() if not output_detail_df.empty else pd.DataFrame(columns=DOUYIN_DETAIL_COLUMNS)
        ai_review_df = pd.DataFrame(ai_rows, columns=["商品标题", "细分类目", "规则分类", "AI分类", "AI置信度", "是否采纳", "原因"])
        failed_df = pd.DataFrame(failed_rows + duplicate_rows, columns=["文件", "Sheet", "原因", "处理方式"])

        output_path = str(Path(self.output_dir) / "抖音_清洗整合结果.xlsx")
        write_dataframes_to_workbook(output_path, {
            "清洗后明细": output_detail_df,
            "整合表": integration_df,
            "五级分类整合表": five_level_df.drop(columns=["平台", "主题关键词", "来源文件"], errors="ignore"),
            "其他分类明细": other_df,
            "AI五级分类审核明细": ai_review_df,
            "失败明细": failed_df,
        })
        errors = [{"平台": "douyin", "文件名": r[0], "工作表名": r[1], "行号": "", "列名": "", "原始值": "", "错误类型": "处理失败", "错误原因": r[2], "处理方式": r[3]} for r in failed_rows]
        return DouyinProcessResult(keyword=keyword, detail_df=output_detail_df, integration_df=integration_df, five_level_df=five_level_df, other_category_df=other_df, ai_review_df=ai_review_df, failed_items_df=failed_df, output_path=output_path, source_files=source_files, errors=errors)

    def _extract_sheet_record(self, df, sheet_name, month, filename, ai_rows):
        header_idx, data_idx = _locate_header_and_data_row(df)
        header = df.iloc[header_idx].tolist()
        data = df.iloc[data_idx]
        col_map = _column_map(header)
        values = {}
        for col, metric_type in [("销量", "integer"), ("销售额", "amount"), ("浏览量", "integer"), ("订单量", "integer")]:
            idx = _find_required_col(col_map, col)
            ok, parsed, reason, status = parse_metric_value(data.iloc[idx], col, metric_type)
            values[col] = parsed if ok else 0
        fine_category = _extract_fine_category(df)
        category, confidence, reason = classify_douyin_category(fine_category, sheet_name)
        if fine_category == "未知" or category == "其他" or confidence < 0.7:
            ai_result = self.review_ai_category(sheet_name, fine_category, category)
            ai_rows.append([sheet_name, fine_category, category, ai_result["category"], ai_result["confidence"], ai_result["accepted"], ai_result["reason"]])
            if ai_result["accepted"]:
                category = ai_result["category"]
        return {
            "月份": month,
            "商品标题": normalize_text(sheet_name),
            "细分类目": fine_category,
            "五级分类": category,
            "销量": int(round(float(values["销量"] or 0))),
            "销售额": round(float(values["销售额"] or 0), 2),
            "浏览量": int(round(float(values["浏览量"] or 0))),
            "订单量": int(round(float(values["订单量"] or 0))),
            "来源文件": filename,
            "来源工作表": sheet_name,
        }

    def _build_integration(self, detail_df):
        if detail_df.empty:
            return pd.DataFrame(columns=DOUYIN_DETAIL_COLUMNS)
        grouped = detail_df.groupby(["月份", "细分类目", "五级分类"], as_index=False)[DOUYIN_NUMERIC_COLUMNS].sum()
        grouped["商品标题"] = grouped["细分类目"]
        grouped = grouped[DOUYIN_DETAIL_COLUMNS]
        grouped["销量"] = grouped["销量"].round().astype(int)
        grouped["浏览量"] = grouped["浏览量"].round().astype(int)
        grouped["订单量"] = grouped["订单量"].round().astype(int)
        grouped["销售额"] = grouped["销售额"].round(2)
        return grouped.sort_values(by=["月份", "五级分类", "细分类目"]).reset_index(drop=True)

    def _build_five_level(self, detail_df, keyword, source_files):
        columns = ["平台", "主题关键词", "时间", "分类名", "销量", "销售额", "浏览量", "订单量", "来源文件"]
        if detail_df.empty:
            return pd.DataFrame(columns=columns)
        grouped = detail_df.groupby(["月份", "五级分类"], as_index=False)[DOUYIN_NUMERIC_COLUMNS].sum()
        rows = []
        for month in sorted(detail_df["月份"].dropna().unique()):
            for category in FIXED_OUTPUT_CATEGORIES:
                matched = grouped[(grouped["月份"] == month) & (grouped["五级分类"] == category)]
                row = {"平台": "douyin", "主题关键词": keyword, "时间": month, "分类名": category, "来源文件": ",".join(source_files)}
                for col in DOUYIN_NUMERIC_COLUMNS:
                    row[col] = float(matched.iloc[0][col]) if not matched.empty else 0
                rows.append(row)
        result = pd.DataFrame(rows, columns=columns)
        result["销量"] = result["销量"].round().astype(int)
        result["浏览量"] = result["浏览量"].round().astype(int)
        result["订单量"] = result["订单量"].round().astype(int)
        result["销售额"] = result["销售额"].round(2)
        return result
