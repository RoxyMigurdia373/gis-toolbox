"""交互式添加完成的工具；复制后由 manifest 自动发现，无需修改主程序。"""
import json
from pathlib import Path
import re
import shutil


def main():
    root = Path(__file__).resolve().parent
    tool_id = input("工具 ID（小写字母、数字、下划线）：").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", tool_id):
        raise ValueError("无效工具 ID")
    target = root / "tools" / tool_id
    if target.exists():
        raise ValueError("目标目录已存在，不覆盖原有工具")
    name = input("工具名称：").strip()
    description = input("一句话简介：").strip()
    kind = input("类型（streamlit/static）：").strip()
    if not name or not description or kind not in ("streamlit", "static"):
        raise ValueError("名称、简介和有效类型不能为空")
    source = Path(input("现有工具目录绝对路径：").strip().strip('"')).resolve()
    if not source.is_dir() or target.is_relative_to(source):
        raise ValueError("源目录不存在，或目标在源目录内部")
    entry = input(f"入口文件（默认 {'app.py' if kind == 'streamlit' else 'index.html'}）：").strip()
    entry = entry or ("app.py" if kind == "streamlit" else "index.html")
    entry_path = (source / entry).resolve()
    if not entry_path.is_relative_to(source) or not entry_path.is_file():
        raise ValueError("入口文件不存在或越出源目录")
    expected = (".py",) if kind == "streamlit" else (".html", ".htm")
    if entry_path.suffix.lower() not in expected:
        raise ValueError("入口扩展名与工具类型不匹配")
    data = dict(id=tool_id, name=name, description=description, type=kind,
                entry=entry, icon="assets/icon.png", working_dir=f"tools/{tool_id}")
    if kind == "streamlit":
        port = int(input("优先端口（默认 8504）：").strip() or "8504")
        if not 8501 <= port <= 8600:
            raise ValueError("端口必须在 8501–8600 范围内")
        data["port_preference"] = port
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(
        ".git", ".venv", "__pycache__", "build", "dist", "node_modules", ".pytest_cache"))
    assets = target / "assets"
    assets.mkdir(exist_ok=True)
    if not (assets / "icon.png").exists():
        shutil.copy2(root / "tools/farmland_context/assets/icon.png", assets / "icon.png")
    (target / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已添加：{target}。若有新的第三方依赖，请更新 requirements.txt/build.spec 后重新打包。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"添加失败：{exc}")
        raise SystemExit(1)
