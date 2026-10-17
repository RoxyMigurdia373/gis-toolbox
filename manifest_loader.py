"""manifest 是唯一工具注册来源；单个坏文件不会阻止其他工具加载。"""
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re

from resource_utils import resource_path


@dataclass(frozen=True)
class ToolManifest:
    id: str
    name: str
    description: str
    type: str
    directory: Path
    entry: Path
    icon: Path
    port_preference: int | None = None
    requires_ogr2ogr: bool = False


def load_manifests(root: Path | None = None) -> dict[str, ToolManifest]:
    root = (root or resource_path()).resolve()
    tools_root = root / "tools"
    result = {}
    for path in sorted(tools_root.glob("*/manifest.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("manifest 顶层必须是 JSON 对象")
            for key in ("id", "name", "description", "type", "entry", "icon", "working_dir"):
                if not isinstance(data.get(key), str) or not data[key].strip():
                    raise ValueError(f"缺少或无效字段：{key}")
            if not re.fullmatch(r"[a-z][a-z0-9_]*", data["id"]):
                raise ValueError("id 只能使用小写字母、数字、下划线，并以字母开头")
            if data["id"] in result:
                raise ValueError("重复的工具 id")
            if data["type"] not in ("streamlit", "static"):
                raise ValueError("type 必须为 streamlit 或 static")
            directory = (root / data["working_dir"]).resolve()
            if directory != path.parent.resolve() or not directory.is_relative_to(tools_root.resolve()):
                raise ValueError("working_dir 必须指向 manifest 所在工具目录")
            entry = (directory / data["entry"]).resolve()
            icon = (directory / data["icon"]).resolve()
            for item in (entry, icon):
                if not item.is_relative_to(directory) or not item.is_file():
                    raise ValueError(f"资源不存在或越出工具目录：{item.name}")
            expected = (".py",) if data["type"] == "streamlit" else (".html", ".htm")
            if entry.suffix.lower() not in expected:
                raise ValueError("入口扩展名与工具类型不匹配")
            port = data.get("port_preference")
            if data["type"] == "streamlit" and (type(port) is not int or not 1 <= port <= 65535):
                raise ValueError("Streamlit 工具需要有效的 port_preference")
            requires = data.get("requires_ogr2ogr", False)
            if not isinstance(requires, bool):
                raise ValueError("requires_ogr2ogr 必须为布尔值")
            result[data["id"]] = ToolManifest(data["id"], data["name"], data["description"],
                                             data["type"], directory, entry, icon, port, requires)
        except (ValueError, OSError, TypeError) as exc:
            logging.getLogger(__name__).warning("跳过 %s：%s", path, exc)
    return result
