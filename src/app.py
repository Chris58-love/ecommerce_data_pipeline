import argparse
import logging
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.aggregation.final_workbook_builder import build_error_fix_dataframe, build_final_workbook, build_summary_text_dataframe
from src.aggregation.five_level_merger import merge_five_level
from src.aggregation.top10_merger import merge_top10
from src.ai.ai_audit_logger import AIAuditLogger
from src.ai.ai_orchestrator import AIOrchestrator
from src.ai.deepseek_client import DeepSeekClient
from src.constants import ERROR_COLUMNS, MANUAL_CONFIRM_COLUMNS
from src.detection.platform_detector import PlatformDetector
from src.io.archive_handler import prepare_input_path
from src.io.file_loader import scan_table_files
from src.io.output_manager import create_output_dir
from src.models import FinalProcessResult
from src.platforms.douyin_processor import DouyinProcessor
from src.platforms.jd_processor import JDProcessor
from src.utils.logging_utils import setup_logging


DEFAULT_CONFIG = {
    "deepseek": {
        "enabled": True,
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v4-flash",
        "timeout_seconds": 60,
        "max_retries": 2,
    },
    "runtime": {"mode": "local", "temp_dir": "./.runtime", "output_dir": "./outputs"},
    "detection": {"ai_fallback_enabled": True, "min_confidence": 0.75},
    "output": {"zip_results": True, "timestamp_output_dir": True},
}


def load_config(path: str = "") -> dict:
    config = DEFAULT_CONFIG.copy()
    if path:
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        config = _deep_merge(config, loaded)
    return config


def _deep_merge(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="京东 + 抖音电商数据清洗整合工具")
    parser.add_argument("--input", help="输入文件夹或 ZIP 路径")
    parser.add_argument("--output", help="输出目录")
    parser.add_argument("--config", default="", help="配置文件路径")
    parser.add_argument("--ai", choices=["on", "off", "auto"], default="auto", help="DeepSeek 智能辅助开关")
    parser.add_argument("--mode", default="local", choices=["local"], help="运行模式")
    return parser.parse_args()


def prompt_interactive(args):
    print("欢迎使用京东 & 抖音电商数据清洗整合工具")
    if not args.input:
        args.input = input("请输入输入文件夹或 ZIP 路径：").strip().strip('"')
    if not args.output:
        args.output = input("请输入输出目录：").strip().strip('"') or "./outputs"
    if args.ai == "auto":
        value = input("是否启用 DeepSeek 智能辅助？ auto/on/off：").strip().lower()
        if value in {"on", "off", "auto"}:
            args.ai = value
    return args


def detection_report(records, detection_results):
    rows = []
    for record, result in zip(records, detection_results):
        rows.append({
            "文件名": record.filename,
            "父级目录": record.parent_dir,
            "相对路径": record.relative_path,
            "识别平台": result.platform,
            "主题关键词": result.keyword,
            "识别来源": result.source,
            "置信度": result.confidence,
            "识别原因": result.reason,
            "是否需要人工确认": result.need_manual_confirm,
            "状态": record.status,
            "错误信息": record.error,
        })
    return pd.DataFrame(rows)


def build_manual_confirm_df(detection_df, error_df):
    rows = []
    if detection_df is not None and not detection_df.empty:
        for _, row in detection_df[detection_df["是否需要人工确认"] == True].iterrows():
            rows.append(["平台识别", row["识别平台"], row["文件名"], "", "", "", row["相对路径"], row["识别来源"], "", row["识别原因"], "请人工确认平台和主题关键词"])
    return pd.DataFrame(rows, columns=MANUAL_CONFIRM_COLUMNS)


def zip_outputs(run_dir: str, output_paths: list, log_path: str, error_report_path: str, ai_report_path: str) -> str:
    zip_path = str(Path(run_dir) / f"final_outputs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in output_paths + [log_path, error_report_path, ai_report_path]:
            if path and Path(path).exists():
                zipf.write(path, arcname=Path(path).name)
    return zip_path


def run_pipeline(input_path: str, output_path: str, config_path=None, ai_mode: str = "auto", runtime_mode: str = "local") -> FinalProcessResult:
    if isinstance(config_path, dict):
        config = config_path
    else:
        config = load_config(config_path or "")
    config.setdefault("runtime", {})
    config["runtime"]["mode"] = runtime_mode
    start_time = datetime.now()
    output_dirs = create_output_dir(output_path, config.get("output", {}).get("timestamp_output_dir", True))
    log_path = str(Path(output_dirs["logs"]) / "processing.log")
    setup_logging(log_path)
    logging.info("开始运行，输入路径=%s 输出目录=%s", input_path, output_dirs["root"])

    ai_enabled = ai_mode != "off"
    deepseek_cfg = dict(config.get("deepseek", {}))
    deepseek_cfg["enabled"] = bool(deepseek_cfg.get("enabled", True)) and ai_enabled
    audit_logger = AIAuditLogger()
    client = DeepSeekClient(deepseek_cfg)
    orchestrator = AIOrchestrator(client, audit_logger, enabled=ai_enabled)

    prepared_input = prepare_input_path(input_path, output_dirs["temp"])
    print("开始扫描文件...")
    records = scan_table_files(prepared_input)
    logging.info("扫描到表格文件数=%s", len(records))

    print("开始识别平台...")
    detector = PlatformDetector(
        orchestrator,
        min_confidence=float(config.get("detection", {}).get("min_confidence", 0.75)),
        ai_fallback_enabled=bool(config.get("detection", {}).get("ai_fallback_enabled", True)),
    )
    detections = []
    for record in records:
        try:
            result = detector.detect(record)
            record.detected_platform = result.platform
            record.keyword = result.keyword
            record.status = "detected"
            detections.append(result)
        except Exception as exc:
            logging.exception("平台识别失败 %s", record.path)
            record.status = "failed"
            record.error = str(exc)
            detections.append(type("DetectionFallback", (), {"platform": "unknown", "keyword": "", "confidence": 0.0, "source": "unknown", "reason": str(exc), "need_manual_confirm": True})())

    detection_df = detection_report(records, detections)
    jd_files = [r for r in records if r.detected_platform == "jd"]
    douyin_files = [r for r in records if r.detected_platform == "douyin"]

    print("开始处理京东数据...")
    jd_result = JDProcessor(output_dirs["workbooks"], orchestrator).process(jd_files) if jd_files else None
    print("开始处理抖音数据...")
    douyin_result = DouyinProcessor(output_dirs["workbooks"], orchestrator).process(douyin_files) if douyin_files else None

    five_level_total_df = merge_five_level(
        jd_result.five_level_df if jd_result else None,
        douyin_result.five_level_df if douyin_result else None,
    )
    top10_total_df = merge_top10(jd_result.top10_dfs if jd_result else {}, jd_result.keyword if jd_result else "")

    all_errors = []
    if jd_result:
        all_errors.extend(jd_result.errors)
    if douyin_result:
        all_errors.extend(douyin_result.errors)
    error_df = pd.DataFrame(all_errors, columns=ERROR_COLUMNS) if all_errors else pd.DataFrame(columns=ERROR_COLUMNS)
    manual_confirm_df = build_manual_confirm_df(detection_df, error_df)

    merge_review = orchestrator.review_merge_consistency_ai({
        "五级分类行数": len(five_level_total_df),
        "Top10行数": len(top10_total_df),
        "京东文件数": len(jd_files),
        "抖音文件数": len(douyin_files),
    })
    error_fix = orchestrator.suggest_error_fix_ai(error_df.head(30).to_dict("records"))

    stats = {
        "扫描文件数": len(records),
        "京东文件数": len(jd_files),
        "抖音文件数": len(douyin_files),
        "unknown 文件数": len([r for r in records if r.detected_platform == "unknown"]),
    }
    summary = orchestrator.generate_processing_summary_ai(stats)
    end_time = datetime.now()

    overview_df = pd.DataFrame([{
        "运行开始时间": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "运行结束时间": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "输入路径": str(Path(input_path).resolve()),
        "输出路径": output_dirs["root"],
        "扫描文件数": len(records),
        "京东文件数": len(jd_files),
        "抖音文件数": len(douyin_files),
        "unknown 文件数": len([r for r in records if r.detected_platform == "unknown"]),
        "成功处理文件数": len(jd_files) + len(douyin_files),
        "失败文件数": len(error_df["文件名"].dropna().unique()) if not error_df.empty else 0,
        "AI 调用次数": len(audit_logger.events),
        "AI 采纳次数": int(audit_logger.to_dataframe()["是否采纳"].sum()) if audit_logger.events else 0,
        "需人工确认项数": len(manual_confirm_df),
        "最终工作簿路径": "",
        "最终 ZIP 路径": "",
    }])

    final_workbook_path = str(Path(output_dirs["workbooks"]) / f"电商数据清洗整合结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    ai_report_dfs = {
        "AI处理总览": audit_logger.build_summary_dataframe(),
        "AI识别明细": audit_logger.to_dataframe(),
        "AI未采纳明细": audit_logger.build_rejected_dataframe(),
        "AI异常明细": audit_logger.build_error_dataframe(),
    }
    error_fix_df = build_error_fix_dataframe(error_fix)
    ai_summary_df = build_summary_text_dataframe(summary)
    build_final_workbook(final_workbook_path, overview_df, detection_df, five_level_total_df, top10_total_df, jd_result, douyin_result, ai_report_dfs, manual_confirm_df, error_fix_df, ai_summary_df)

    error_report_path = str(Path(output_dirs["reports"]) / "错误报告.xlsx")
    ai_report_path = str(Path(output_dirs["reports"]) / "AI审核报告.xlsx")
    from src.utils.excel_format import write_dataframes_to_workbook
    write_dataframes_to_workbook(error_report_path, {"错误报告": error_df, "需人工确认明细": manual_confirm_df, "错误修复建议": error_fix_df})
    write_dataframes_to_workbook(ai_report_path, {**ai_report_dfs, "合并一致性审核": pd.DataFrame([merge_review]), "AI处理摘要": ai_summary_df})

    output_paths = [final_workbook_path]
    if jd_result:
        output_paths.append(jd_result.output_path)
    if douyin_result:
        output_paths.append(douyin_result.output_path)
    zip_path = zip_outputs(output_dirs["root"], output_paths, log_path, error_report_path, ai_report_path)

    overview_df.loc[0, "最终工作簿路径"] = final_workbook_path
    overview_df.loc[0, "最终 ZIP 路径"] = zip_path
    build_final_workbook(final_workbook_path, overview_df, detection_df, five_level_total_df, top10_total_df, jd_result, douyin_result, ai_report_dfs, manual_confirm_df, error_fix_df, ai_summary_df)

    logging.info("最终工作簿=%s", final_workbook_path)
    logging.info("最终ZIP=%s", zip_path)
    print(f"最终结果已生成：{final_workbook_path}")
    print(f"最终 ZIP 已生成：{zip_path}")
    return FinalProcessResult(
        output_dir=output_dirs["root"],
        final_workbook_path=final_workbook_path,
        jd_workbook_path=jd_result.output_path if jd_result else "",
        douyin_workbook_path=douyin_result.output_path if douyin_result else "",
        zip_path=zip_path,
        log_path=log_path,
        detection_report_df=detection_df,
        error_report_df=error_df,
        ai_report_dfs=ai_report_dfs,
    )


def main():
    args = parse_args()
    if not args.input or not args.output:
        args = prompt_interactive(args)
    config = load_config(args.config)
    if args.output:
        config["runtime"]["output_dir"] = args.output
    run_pipeline(args.input, config["runtime"]["output_dir"], config, args.ai)
