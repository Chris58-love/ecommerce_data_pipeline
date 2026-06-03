from pathlib import Path
from typing import Dict

import pandas as pd

from src.utils.excel_format import write_dataframes_to_workbook


def build_error_fix_dataframe(result: dict) -> pd.DataFrame:
    suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
    if not suggestions:
        return pd.DataFrame(columns=["错误类型", "原因", "修复建议"])
    return pd.DataFrame([{
        "错误类型": item.get("error_type", ""),
        "原因": item.get("reason", ""),
        "修复建议": item.get("fix", ""),
    } for item in suggestions])


def build_summary_text_dataframe(result: dict) -> pd.DataFrame:
    return pd.DataFrame([{"处理摘要": (result or {}).get("summary", "")}])


def build_final_workbook(
    output_path: str,
    overview_df: pd.DataFrame,
    detection_df: pd.DataFrame,
    five_level_total_df: pd.DataFrame,
    top10_total_df: pd.DataFrame,
    jd_result=None,
    douyin_result=None,
    ai_report_dfs: Dict[str, pd.DataFrame] = None,
    manual_confirm_df: pd.DataFrame = None,
    error_fix_df: pd.DataFrame = None,
    ai_summary_df: pd.DataFrame = None,
):
    sheets = {
        "处理总览": overview_df,
        "文件识别明细": detection_df,
        "五级分类整合总表": five_level_total_df,
        "Top10整合总表": top10_total_df,
    }
    if jd_result and jd_result.clean_df is not None:
        sheets.update({
            "京东_所有月份整合数据": jd_result.aggregate_df,
            "京东_清洗后数据": jd_result.clean_df,
            "京东_其他类别商品": jd_result.other_df,
            "京东_AI分类审核明细": jd_result.ai_review_df,
        })
    if douyin_result and douyin_result.detail_df is not None:
        sheets.update({
            "抖音_清洗后明细": douyin_result.detail_df,
            "抖音_整合表": douyin_result.integration_df,
            "抖音_五级分类整合表": douyin_result.five_level_df,
            "抖音_其他分类明细": douyin_result.other_category_df,
            "抖音_AI五级分类审核明细": douyin_result.ai_review_df,
        })
    sheets.update(ai_report_dfs or {})
    sheets["需人工确认明细"] = manual_confirm_df if manual_confirm_df is not None else pd.DataFrame()
    sheets["错误修复建议"] = error_fix_df if error_fix_df is not None else pd.DataFrame()
    sheets["AI处理摘要"] = ai_summary_df if ai_summary_df is not None else pd.DataFrame()
    write_dataframes_to_workbook(output_path, sheets)
    return output_path
