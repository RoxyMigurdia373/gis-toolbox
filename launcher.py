"""开发入口：python launcher.py；打包入口：GISToolbox.exe。"""
import multiprocessing
import sys

# 必须在导入 GUI、解析参数、获取单实例锁之前执行。
if __name__ == "__main__":
    multiprocessing.freeze_support()

import logging
import os
import tomllib

from logger import setup_logging
from resource_utils import SingleInstanceLock, resource_path, user_data_dir


def show_message(message, title="GIS 工具箱"):
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x40)
    elif sys.stderr:
        print(message, file=sys.stderr)


def main():
    lock = None
    manager = None
    try:
        sys.dont_write_bytecode = True
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        setup_logging()
        lock = SingleInstanceLock()
        if not lock.acquire():
            show_message("GIS 工具箱已经在运行，请从任务栏切换到已有窗口。")
            return 0
        config = tomllib.loads(resource_path("config/app_config.toml").read_text(encoding="utf-8"))
        from manifest_loader import load_manifests
        from tool_manager import ToolManager
        from main_window import create_main_window
        os.environ["QT_API"] = "pyside6"
        import webview
        from qt_compat import configure_qt_downloads, configure_webview_settings
        configure_webview_settings(webview)
        configure_qt_downloads("qtwebengine")

        tools = load_manifests()
        if not tools:
            raise RuntimeError("未找到可用工具，请检查 tools 目录和 manifest.json。")
        manager = ToolManager(tools, config, webview)
        create_main_window(manager, config)
        logging.info("启动 %s %s，工具 %s，用户目录 %s", config["name"], config["version"], list(tools), user_data_dir())
        webview.start(gui="qt", debug=False, http_server=False,
                      private_mode=False, storage_path=str(user_data_dir() / "webview"))
        return 0
    except Exception as exc:
        logging.exception("主程序启动失败")
        show_message(f"启动失败：{exc}\n\n请查看用户目录 GISToolbox/logs/app.log。\n"
                     "请完整解压发布包，保留 _internal 目录。支持 Windows 10/11 64 位。")
        return 1
    finally:
        if manager:
            manager.quit_all()
        if lock:
            lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
