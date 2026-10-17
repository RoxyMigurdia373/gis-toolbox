# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir；pywebview 的导入包名是 webview，而非 pywebview。"""
from pathlib import Path
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / folder), folder) for folder in ('ui', 'config', '.streamlit')]
for path in (root / 'tools').rglob('*'):
    relative = path.relative_to(root)
    if path.is_file() and not any(part in ('__pycache__', '.git', '.venv', '.pytest_cache') for part in relative.parts) and path.suffix not in ('.pyc', '.log'):
        datas.append((str(path), str(relative.parent)))
datas.append((str(root / 'icon.ico'), '.'))
binaries = []
hiddenimports = ['streamlit.web.cli', 'streamlit.runtime.scriptrunner.magic_funcs',
                 'streamlit.runtime.scriptrunner.script_runner', 'fiona.ogrext', 'pyogrio._io',
                 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'pythonnet', 'clr',
                 'sqlite3', 'xml.sax.saxutils']
for package in ('streamlit', 'geopandas', 'pyogrio', 'shapely', 'fiona', 'pyproj',
                'webview', 'ijson', 'simplejson', 'pythonnet', 'clr_loader'):
    data, binary, hidden = collect_all(package)
    datas += data
    binaries += binary
    hiddenimports += hidden
for package in ('streamlit', 'pywebview'):
    datas += copy_metadata(package, recursive=True)

# 可选、可再分发的独立 GDAL CLI 目录；不混用不同发行版的 DLL。
# 未配置时正常构建，工具自动使用 Fiona + PyProj。
gdal_dir = Path(os.environ.get('GIS_GDAL_DIR', root / 'vendor' / 'gdal'))
if (gdal_dir / 'ogr2ogr.exe').is_file():
    datas.append((str(gdal_dir), 'gdal'))
    print(f'Bundling optional GDAL CLI: {gdal_dir}')
else:
    print('No optional ogr2ogr bundle; Fiona + PyProj fallback enabled.')

a = Analysis([str(root / 'launcher.py')], pathex=[str(root)],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['matplotlib', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
                       'IPython', 'jupyter', 'notebook', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GISToolbox',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, icon=str(root / 'icon.ico'),
          contents_directory='_internal')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GISToolbox')
