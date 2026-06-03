import getpass
import importlib.util
import os
import subprocess
import sys
import traceback
from pathlib import Path


REQUIRED_PACKAGES = {
    "pandas": "pandas",
    "openpyxl": "openpyxl",
    "xlsxwriter": "xlsxwriter",
    "xlrd": "xlrd",
    "requests": "requests",
    "yaml": "pyyaml",
}


def install_missing_dependencies() -> None:
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)
    if missing:
        print("正在安装缺失依赖: " + ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])
    else:
        print("依赖检查通过。")


def configure_api_key() -> None:
    if os.getenv("DEEPSEEK_API_KEY"):
        print("已检测到 DEEPSEEK_API_KEY，将按 auto 模式启用 AI 辅助。")
        return
    print("未检测到 DEEPSEEK_API_KEY，将以纯规则模式运行。")
    try:
        api_key = getpass.getpass("请输入 DeepSeek API Key，直接回车则跳过：").strip()
    except Exception:
        api_key = input("请输入 DeepSeek API Key，直接回车则跳过：").strip()
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
        print("已临时设置 DEEPSEEK_API_KEY。本次运行有效，不会写入文件。")
    else:
        print("已跳过 API Key，继续使用纯规则模式。")


def print_summary(result) -> None:
    detection_df = result.detection_report_df
    total = len(detection_df) if detection_df is not None else 0
    jd_count = douyin_count = unknown_count = 0
    if detection_df is not None and not detection_df.empty:
        platform_col = next((col for col in detection_df.columns if "平台" in str(col) or "骞冲彴" in str(col)), detection_df.columns[3])
        counts = detection_df[platform_col].value_counts().to_dict()
        jd_count = int(counts.get("jd", 0))
        douyin_count = int(counts.get("douyin", 0))
        unknown_count = int(counts.get("unknown", 0))
    failed_count = len(result.error_report_df) if result.error_report_df is not None else 0
    print("\n运行摘要")
    print(f"- 扫描文件数: {total}")
    print(f"- 京东文件数: {jd_count}")
    print(f"- 抖音文件数: {douyin_count}")
    print(f"- unknown 文件数: {unknown_count}")
    print(f"- 失败记录数: {failed_count}")
    print(f"- 最终工作簿路径: {result.final_workbook_path}")
    print(f"- 最终 ZIP 路径: {result.zip_path}")


def main() -> None:
    print("京东 & 抖音电商数据清洗整合工具 - Colab 检测版")
    install_missing_dependencies()
    configure_api_key()

    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.app import run_pipeline
    from src.io.colab_adapter import ColabAdapter

    adapter = ColabAdapter()
    paths = adapter.prepare_runtime_dirs()
    try:
        uploaded_paths = adapter.upload_files()
        input_dir = adapter.prepare_input_from_uploads(uploaded_paths)
        print(f"输入目录: {input_dir}")
        print(f"输出目录: {paths.outputs}")
        result = run_pipeline(
            input_path=str(input_dir),
            output_path=str(paths.outputs),
            config_path=None,
            ai_mode="auto",
            runtime_mode="colab",
        )
        print_summary(result)
        print("\n开始下载最终 ZIP...")
        adapter.download_file(result.zip_path)
    except Exception as exc:
        print("\nColab 检测运行失败：")
        print(str(exc))
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
