"""限制清理路径在项目内部，再调用 PyInstaller。"""
from pathlib import Path
import shutil
import subprocess
import sys


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for name in ('build', 'dist'):
        path = root / name
        resolved = path.resolve()
        if resolved.parent != root or path.is_symlink():
            raise RuntimeError(f'拒绝清理项目外部或链接目录：{resolved}')
        if path.exists():
            shutil.rmtree(path)
    result = subprocess.call([sys.executable, '-m', 'PyInstaller',
                              str(root / 'build.spec'), '--clean', '--noconfirm'], cwd=root)
    if result == 0:
        shutil.copy2(root / 'README.md', root / 'dist/GISToolbox/README.md')
    raise SystemExit(result)
