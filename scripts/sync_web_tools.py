"""Promote explicitly reviewed web commits; --check is read-only and the default."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root).decode('utf-8').strip()


def digest(data):
    # Git may use CRLF on Windows and LF in cloud checkouts.
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Back up, then import reviewed commits from config/web_sources.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.apply and args.check:
        parser.error('Choose --apply or --check')
    sources = json.loads((ROOT / 'config/web_sources.json').read_text(encoding='utf-8'))
    changes = []
    records = []
    for source in sources:
        checkout = (ROOT.parent / source['checkout']).resolve()
        if checkout.parent != ROOT.parent or git(checkout, 'status', '--porcelain'):
            raise RuntimeError(f'Invalid or dirty web checkout: {checkout}')
        commit = git(checkout, 'rev-parse', 'HEAD')
        if commit != source['commit']:
            raise RuntimeError(f"{source['tool']}: review the new web commit and update config/web_sources.json first")
        record = {'repository': source['repository'], 'commit': commit, 'files': {}}
        for name in source['files']:
            path = Path(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'Unsafe relative file: {name}')
            src = checkout / path
            git(checkout, 'ls-files', '--error-unmatch', name)
            data = src.read_bytes()
            dest = ROOT / 'tools' / source['tool'] / path
            record['files'][name] = digest(data)
            if not dest.exists() or digest(dest.read_bytes()) != digest(data):
                changes.append((dest, data))
        records.append((ROOT / 'tools' / source['tool'] / 'WEB_SOURCE.json', record))
    if not args.apply:
        for dest, _ in changes:
            print(f'DIFF {dest.relative_to(ROOT)}')
        for path, record in records:
            if not path.exists() or json.loads(path.read_text(encoding='utf-8')) != record:
                changes.append((path, b''))
                print(f'DIFF {path.relative_to(ROOT)}')
        print(f'{len(changes)} differences across {len(sources)} web sources')
        return bool(changes)
    from backup_version import backup
    backup(ROOT)
    for dest, data in changes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    for path, record in records:
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Imported {len(sources)} reviewed web commits; run regressions before packaging.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
