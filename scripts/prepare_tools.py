"""首次整合源项目的快照。已有目标目录时停止，防止覆盖后续桌面版修改。"""
import json
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parents[1]
    specifications = [
        ("farmland_osm", "farmland_context", "耕地地块周边地物分析", "提取 OSM 地物，计算到公路、铁路、村庄的距离，导出 GeoJSON/SHP", 8501),
        ("vector_size_splitter", "split_by_size", "按文件大小切分矢量数据", "将 GeoJSON、SHP、GPKG 按指定体积拆分，生成分片 ZIP 与清单", 8502),
        ("shp2kml", "shp_to_kml", "SHP 转 KML / KMZ", "批量转换 Shapefile 为 KML/KMZ，处理中文编码与坐标系", 8503),
    ]
    for source, tool_id, name, description, port in specifications:
        target = root / "tools" / tool_id
        if target.exists():
            raise FileExistsError(f"目标已存在，不覆盖：{target}")
        shutil.copytree(root.parent / source, target, ignore=shutil.ignore_patterns(
            ".git", ".venv", "__pycache__", ".pytest_cache", "build", "dist"))
        data = dict(id=tool_id, name=name, description=description, type="streamlit", entry="app.py",
                    icon="assets/icon.png", port_preference=port, working_dir=f"tools/{tool_id}")
        if tool_id == "shp_to_kml":
            data["requires_ogr2ogr"] = True
        (target / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # 原项目使用较新版 Streamlit 的 download_button(on_click='ignore')。
        # 1.40.1 不支持该字符串；结果已保存在 session_state，默认 rerun 可安全下载。
        app = target / "app.py"
        text = app.read_text(encoding="utf-8")
        text = text.replace(', on_click="ignore"', '').replace(", on_click='ignore'", '')
        text = text.replace('width="stretch"', 'use_container_width=True')
        app.write_text(text, encoding="utf-8")
        print(f"Copied {tool_id}")


if __name__ == "__main__":
    main()
