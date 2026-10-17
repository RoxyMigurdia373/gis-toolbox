"""生成可分发 Windows ZIP、独立源码 ZIP 与 SHA256 校验清单。"""
import hashlib
from pathlib import Path
import shutil
import zipfile


def archive(paths, output, root, prefix):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(paths):
            z.write(path, str(Path(prefix) / path.relative_to(root)))
    print(f'{output.name}: {output.stat().st_size / 1024**2:.1f} MiB', flush=True)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    distribution = root / 'dist/GISToolbox'
    if not (distribution / 'GISToolbox.exe').is_file():
        raise FileNotFoundError('请先构建 Windows 发布目录')
    release = root / 'release'
    release.mkdir(exist_ok=True)
    shutil.copy2(root / 'README.md', distribution / 'README.md')
    shutil.copy2(root / 'VALIDATION.md', distribution / 'VALIDATION.md')
    windows_zip = release / 'GISToolbox-1.0.0-Windows-x64.zip'
    archive([p for p in distribution.rglob('*') if p.is_file()], windows_zip, distribution, 'GISToolbox')
    ignored = {'.venv', 'build', 'dist', 'release', '__pycache__', '.pytest_cache', '.git', 'artifacts'}
    source = [p for p in root.rglob('*') if p.is_file()
              and not any(part in ignored for part in p.relative_to(root).parts)
              and p.suffix not in ('.pyc', '.log')]
    source_zip = release / 'gis-toolbox-1.0.0-source.zip'
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
