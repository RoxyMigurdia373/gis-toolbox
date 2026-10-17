"""主程序和每个服务单独轮转日志，避免多进程争用同一个文件。"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from resource_utils import user_data_dir


def setup_logging(name: str = "app", directory: str | Path | None = None) -> Path:
    folder = Path(directory) if directory else user_data_dir() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.log"
    handler = RotatingFileHandler(path, maxBytes=5 * 1024**2, backupCount=3,
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(process)d] %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for old in root.handlers[:]:
        root.removeHandler(old)
        old.close()
    root.addHandler(handler)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return path


class LogStream:
    """windowed exe 的 stdout/stderr 为 None；提供 CLI 可用的日志流。"""
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, level=logging.INFO):
        self.level = level

    def write(self, value):
        for line in str(value).splitlines():
            if line.strip():
                logging.getLogger("service.console").log(self.level, line.rstrip())
        return len(value)

    def flush(self):
        pass

    def isatty(self):
        return False
