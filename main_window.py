"""主界面只暴露有限的工具管理 API；工具窗口不注入 Python API。"""
import base64
import logging
import os

from resource_utils import resource_path, user_data_dir


class Api:
    def __init__(self, manager, config):
        self._manager = manager
        self._config = config
        self._window = None

    def get_tools(self):
        states = self._manager.states()
        result = []
        for tool in self._manager.tools.values():
            mime = "image/svg+xml" if tool.icon.suffix == ".svg" else "image/png"
            icon = f"data:{mime};base64," + base64.b64encode(tool.icon.read_bytes()).decode("ascii")
            result.append({"id": tool.id, "name": tool.name, "description": tool.description,
                           "type": tool.type, "icon": icon, **states[tool.id]})
        return {"name": self._config["name"], "version": self._config["version"], "tools": result}

    def get_states(self):
        return self._manager.states()

    def open_tool(self, tool_id):
        return self._manager.open_tool(tool_id)

    def close_tool(self, tool_id):
        return self._manager.close_tool(tool_id)

    def open_logs(self):
        try:
            path = user_data_dir() / "logs"
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(path))
            return {"ok": True}
        except OSError as exc:
            logging.exception("打开日志目录失败")
            return {"ok": False, "error": str(exc)}

    def quit_app(self):
        if self._window:
            self._window.destroy()
        return {"ok": True}


def create_main_window(manager, config):
    api = Api(manager, config)
    window = manager.webview.create_window(f"{config['name']} · {config['version']}",
        url=resource_path("ui/index.html").as_uri(), js_api=api,
        width=config.get("window_width", 1120), height=config.get("window_height", 780),
        min_size=(720, 560), background_color="#F5F8FA")
    api._window = window
    # closing 在主窗口销毁前执行，子窗口仍可由 GUI 正常回收。
    window.events.closing += manager.quit_all
    return window, api
