"""构建前保存源码和现有 dist；任一备份失败都中止构建。"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def backup(root):
    target = root.parent / 'gis-toolbox-backups' / ('before-build-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    target.mkdir(parents=True, exist_ok=False)
    listing = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root)
    files = [root / n.decode('utf-8') for n in listing.split(b'\0') if n]
    groups = [('source.zip', files, root)]
    dist = root / 'dist' / 'GISToolbox'
    if dist.exists():
        groups.append(('previous-Windows.zip', [p for p in dist.rglob('*') if p.is_file()], dist.parent))
    records = []
    for name, paths, base in groups:
        archive = target / name
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=3) as z:
            for path in sorted(set(paths)):
                if path.is_file():
                    z.write(path, path.relative_to(base))
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise RuntimeError(f'备份校验失败：{archive}')
        with archive.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        records.append({'file': name, 'sha256': digest, 'bytes': archive.stat().st_size})
    (target / 'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(f'Backup verified: {target}', flush=True)
    return target


if __name__ == '__main__':
    backup(Path(__file__).resolve().parents[1])
