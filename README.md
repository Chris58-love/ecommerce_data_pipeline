# 京东 + 抖音电商数据清洗整合工具

本项目是本地运行的 Python 数据处理工具，用于批量扫描文件夹或 ZIP 中的京东、抖音电商表格，自动识别平台，清洗区间数值，聚合口腔护理类目，并输出平台独立工作簿、最终总工作簿、日志和 ZIP 包。

## 当前版本范围

- 支持京东数据清洗、类别聚合、清洗前 Top10 和 AI 分类审核。
- 支持抖音多 sheet 清洗、细分类目提取、五级分类和 AI 五级分类审核。
- 不支持批量改名。
- 不支持小红书。
- 不支持百度搜索指数、抖音搜索指数、抖音综合指数。
- 不开发自动化爬虫。

## 安装

```bash
pip install -r requirements.txt
```

## DeepSeek API Key

无 API Key 时，项目会使用纯规则模式完整运行。有 API Key 时，AI 只用于低置信度识别、列名映射、类目复核、错误建议和摘要等环节，不会无条件覆盖高置信度规则结果。

Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="你的key"
```

macOS / Linux:

```bash
export DEEPSEEK_API_KEY="你的key"
```

当前默认模型为 `deepseek-v4-flash`，配置见 `config/settings.example.yaml`。

## 本地运行

命令行运行：

```bash
python main.py --input ./sample_input --output ./outputs
```

可选参数：

```bash
python main.py --input ./sample_input --output ./outputs --config ./config/settings.yaml --ai auto --mode local
```

交互式运行：

```bash
python main.py
```

## 输入目录示例

```text
sample_input/
  京东数据-口臭/
    2025年5月_京东.xlsx
    2025年6月_京东.xlsx
  抖音数据-牙结石/
    2025-05_抖音.xlsx
    2025-06_抖音.xlsx
```

也可以传入 ZIP 文件，系统会解压到运行临时目录后处理。

## 输出结果

每次运行默认生成独立目录：

```text
outputs/run_YYYYMMDD_HHMMSS/
  workbooks/
    电商数据清洗整合结果_YYYYMMDD_HHMMSS.xlsx
    京东_清洗整合结果.xlsx
    抖音_清洗整合结果.xlsx
  reports/
    错误报告.xlsx
    AI审核报告.xlsx
  logs/
    processing.log
  final_outputs_YYYYMMDD_HHMMSS.zip
```

最终总工作簿包含处理总览、文件识别明细、五级分类整合总表、Top10整合总表、京东相关 sheet、抖音相关 sheet、AI 相关 sheet、人工确认和错误修复建议 sheet。

## AI 辅助说明

- `--ai off`：完全纯规则模式。
- `--ai auto`：有 `DEEPSEEK_API_KEY` 时调用 AI，没有 key 时自动跳过。
- `--ai on`：启用 AI 配置，但缺少 key 或 API 失败仍不会中断流程。
- 所有 AI 调用都会写入 AI 审核报告，包含采纳、未采纳、异常和原始返回摘要。

## 后续扩展

- 可扩展批量改名模块。
- 可扩展小红书处理器。
- 可扩展搜索指数导入。
- 可扩展 Colab 运行模式。

## 测试

```bash
python -m pytest
```
