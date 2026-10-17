"""生成可分发 Windows ZIP、独立源码 ZIP 与 SHA256 校验清单。"""
import hashlib
from pathlib import Path
import shutil
import zipfile
import tomllib
import subprocess
import re


def archive(paths, output, root, prefix):
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(paths):
            z.write(path, str(Path(prefix) / path.relative_to(root)))
    print(f'{output.name}: {output.stat().st_size / 1024**2:.1f} MiB', flush=True)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / 'config/app_config.toml').read_text(encoding='utf-8'))['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?', version):
        raise ValueError('非法版本号')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root).strip():
        raise RuntimeError('请先提交源码改动，再生成发布包。')
    distribution = root / 'dist/GISToolbox'
    if not (distribution / 'GISToolbox.exe').is_file():
        raise FileNotFoundError('请先构建 Windows 发布目录')
    built_version = tomllib.loads((distribution / '_internal/config/app_config.toml').read_text(encoding='utf-8'))['version']
    if built_version != version:
        raise RuntimeError('已构建程序版本与源码版本不一致，请重新构建。')
    release = root / 'release' / ('v' + version)
    release.mkdir(parents=True, exist_ok=False)
    shutil.copy2(root / 'README.md', distribution / 'README.md')
    shutil.copy2(root / 'VALIDATION.md', distribution / 'VALIDATION.md')
    windows_zip = release / f'GISToolbox-{version}-Windows-x64.zip'
    archive([p for p in distribution.rglob('*') if p.is_file()], windows_zip, distribution, 'GISToolbox')
    ignored = {'.venv', 'build', 'dist', 'release', '__pycache__', '.pytest_cache', '.git', 'artifacts'}
    source = [p for p in root.rglob('*') if p.is_file()
              and not any(part in ignored for part in p.relative_to(root).parts)
              and p.suffix not in ('.pyc', '.log')]
    source_zip = release / f'gis-toolbox-{version}-source.zip'
    archive(source, source_zip, root, 'gis-toolbox')
    lines = []
    for path in (windows_zip, source_zip):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024**2), b''):
                digest.update(block)
        lines.append(f'{digest.hexdigest()}  {path.name}')
    (release / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Release artifacts and checksums ready.', flush=True)
