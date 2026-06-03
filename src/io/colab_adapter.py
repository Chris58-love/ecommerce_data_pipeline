import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List


SUPPORTED_DATA_EXTENSIONS = {".xlsx", ".xls", ".csv"}
IGNORED_NAMES = {"__MACOSX", ".DS_Store"}


@dataclass
class ColabPaths:
    root: Path
    uploads: Path
    input: Path
    outputs: Path
    temp: Path


class ColabAdapter:
    def __init__(self, runtime_root: str = "/content/ecommerce_data_pipeline_runtime"):
        self.paths = ColabPaths(
            root=Path(runtime_root),
            uploads=Path(runtime_root) / "uploads",
            input=Path(runtime_root) / "input",
            outputs=Path(runtime_root) / "outputs",
            temp=Path(runtime_root) / "temp",
        )

    def prepare_runtime_dirs(self) -> ColabPaths:
        for path in [self.paths.root, self.paths.uploads, self.paths.input, self.paths.outputs, self.paths.temp]:
            path.mkdir(parents=True, exist_ok=True)
        return self.paths

    def upload_files(self) -> List[Path]:
        try:
            from google.colab import files
        except Exception as exc:
            raise RuntimeError("当前环境不是 Google Colab，无法使用 files.upload()。") from exc

        print("请选择并上传一个数据 ZIP，或多个 .xlsx/.xls/.csv 文件。")
        uploaded = files.upload()
        saved_paths = []
        for filename, content in uploaded.items():
            target = self.paths.uploads / Path(filename).name
            with open(target, "wb") as f:
                f.write(content)
            saved_paths.append(target)
        return saved_paths

    def prepare_input_from_uploads(self, uploaded_paths: List[Path]) -> Path:
        if not uploaded_paths:
            raise RuntimeError("未上传任何文件。")
        self._clear_dir(self.paths.input)

        if len(uploaded_paths) == 1 and uploaded_paths[0].suffix.lower() == ".zip":
            zip_path = uploaded_paths[0]
            if self._looks_like_project_zip(zip_path):
                raise RuntimeError(
                    "检测到上传的 ZIP 更像项目代码包。请先在 Notebook 的项目上传单元解压项目，再运行 colab_runner.py 上传数据包。"
                )
            self._safe_extract_zip(zip_path, self.paths.input)
            return self.paths.input

        input_dir = self.paths.input / "uploaded_files"
        input_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for path in uploaded_paths:
            if path.suffix.lower() not in SUPPORTED_DATA_EXTENSIONS:
                print(f"跳过非表格文件: {path.name}")
                continue
            shutil.copy2(path, input_dir / path.name)
            copied += 1
        if copied == 0:
            raise RuntimeError("未找到可处理的 .xlsx/.xls/.csv 文件。")
        return input_dir

    def download_file(self, path: str) -> None:
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"下载文件不存在: {target}")
        try:
            from google.colab import files
        except Exception as exc:
            raise RuntimeError("当前环境不是 Google Colab，无法使用 files.download()。") from exc
        files.download(str(target))

    def _safe_extract_zip(self, zip_path: Path, destination: Path) -> None:
        destination = destination.resolve()
        with zipfile.ZipFile(zip_path, "r") as zipf:
            for member in zipf.infolist():
                member_path = Path(member.filename)
                if member.is_dir():
                    continue
                if any(part in IGNORED_NAMES for part in member_path.parts):
                    continue
                if member_path.name.startswith("~$"):
                    continue
                target = (destination / member_path).resolve()
                try:
                    target.relative_to(destination)
                except ValueError:
                    raise RuntimeError(f"ZIP 内存在不安全路径，已停止解压: {member.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipf.open(member) as source, open(target, "wb") as dest:
                    shutil.copyfileobj(source, dest)

    def _looks_like_project_zip(self, zip_path: Path) -> bool:
        with zipfile.ZipFile(zip_path, "r") as zipf:
            names = [name.replace("\\", "/") for name in zipf.namelist()]
        return any(name.endswith("src/app.py") for name in names) and any(name.endswith("main.py") for name in names)

    def _clear_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
