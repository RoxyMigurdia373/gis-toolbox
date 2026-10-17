"""只读程序资源与可写用户数据分离，支持 PyInstaller onedir。"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile
from functools import lru_cache


def resource_path(relative: str = "") -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("资源路径不能超出程序目录")
    return result


@lru_cache(maxsize=1)
def user_data_dir() -> Path:
    candidates = [Path(os.environ.get("APPDATA", Path.home())) / "GISToolbox",
                  Path(tempfile.gettempdir()) / "GISToolbox"]
    last_error = None
    for folder in candidates:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=folder):
                pass
            return folder
        except OSError as exc:
            last_error = exc
    raise OSError("用户目录和系统临时目录均不可写") from last_error


def temp_dir() -> Path:
    folder = user_data_dir() / "temp"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def find_ogr2ogr() -> str | None:
    # 优先系统 PATH；不将整套 QGIS DLL 注入 Python 的进程环境。
    system = shutil.which("ogr2ogr")
    if system:
        return system
    bundled = resource_path("gdal/ogr2ogr.exe")
    return str(bundled) if bundled.is_file() else None


class SingleInstanceLock:
    """操作系统文件锁：进程异常结束也会自动释放，锁文件本身可长期存在。"""
    def __init__(self, path: Path | None = None):
        self.path = path or user_data_dir() / ".lock"
        self.file = None

    def acquire(self) -> bool:
        self.file = self.path.open("a+b")
        self.file.seek(0, os.SEEK_END)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.file.close()
            self.file = None
            return False

    def release(self):
        if self.file is not None:
            self.file.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.file, fcntl.LOCK_UN)
            finally:
                self.file.close()
                self.file = None
