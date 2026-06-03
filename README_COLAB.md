# Google Colab 运行说明

这是“京东 + 抖音电商数据清洗整合工具”的 Colab 检测入口。Colab 版本只用于运行检测，不改动本地 CLI，也不依赖 ipywidgets 或 Google Drive 挂载。

## 方式一：上传完整项目 ZIP

1. 将本项目目录打包为 `ecommerce_data_pipeline.zip`。
2. 打开 `JD_DY_COLAB_RUNNER.ipynb`。
3. 运行 Cell 1 安装依赖。
4. 运行 Cell 2。如果 `/content/ecommerce_data_pipeline` 不存在，按提示上传项目 ZIP，Notebook 会自动解压。
5. 运行 Cell 3，启动检测入口：

```python
from colab_runner import main
main()
```

随后按提示上传数据 ZIP 或多个 Excel/CSV 文件。

## 方式二：从 GitHub clone 项目

如果后续项目有仓库，可在 Colab 中运行：

```bash
!git clone <你的仓库地址> /content/ecommerce_data_pipeline
%cd /content/ecommerce_data_pipeline
!python colab_runner.py
```

## 上传数据

运行 `colab_runner.py` 后，会弹出 Colab 上传控件。支持两种输入：

- 一个数据 ZIP。
- 多个 `.xlsx`、`.xls`、`.csv` 文件。

推荐 ZIP 内目录结构：

```text
京东数据-口臭/
  2025年5月_京东.xlsx
  2025年6月_京东.xlsx

抖音数据-牙结石/
  2025-05_抖音.xlsx
  2025-06_抖音.xlsx
```

如果上传多个 Excel/CSV，系统会统一保存到：

```text
/content/ecommerce_data_pipeline_runtime/input/uploaded_files/
```

如果上传一个数据 ZIP，系统会安全解压到：

```text
/content/ecommerce_data_pipeline_runtime/input/
```

## DeepSeek API Key

无 API Key 时也能完整运行，AI 辅助会自动跳过并使用纯规则模式。

方式一：在 Colab 中提前设置：

```python
import os
os.environ["DEEPSEEK_API_KEY"] = "你的key"
```

方式二：运行 `colab_runner.py` 时，按提示临时输入：

```text
请输入 DeepSeek API Key，直接回车则跳过：
```

API Key 只会写入当前 Colab 进程环境变量，不会写入文件，也不会打印到日志。

## 输出结果

Colab 运行目录固定为：

```text
/content/ecommerce_data_pipeline_runtime/
```

输出会保存到：

```text
/content/ecommerce_data_pipeline_runtime/outputs/run_YYYYMMDD_HHMMSS/
```

包含：

- 最终 ZIP。
- 最终总工作簿。
- 京东结果工作簿。
- 抖音结果工作簿。
- `processing.log`。
- 错误报告。
- AI 审核报告。

运行结束后会自动触发下载最终 ZIP。

## 本地运行不受影响

本地仍可使用：

```bash
python main.py --input ./sample_input --output ./outputs
```
