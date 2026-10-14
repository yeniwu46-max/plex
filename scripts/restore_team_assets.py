"""Restore published PLEX assets with SHA-256 verification (standard library only)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/team-sync/release-assets.json'


def safe_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError(f'Path escapes repository: {relative}')
    return path


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def install(destination: Path, data: bytes, expected: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'Checksum mismatch: {destination.relative_to(ROOT)}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never replace a teammate's edited model or a different local file.
    if destination.exists():
        if digest(destination) != expected:
            raise ValueError(f'Local file differs; preserve or rename it first: {destination.relative_to(ROOT)}')
        return
    with destination.open('xb') as stream:
        stream.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing files without downloading or writing')
    args = parser.parse_args()
    assets = json.loads(MANIFEST.read_text(encoding='utf-8'))['assets']
    failures = []
    checked = 0
    for asset in assets:
        archive = safe_path(asset['path'])
        entries = [asset, *asset['extract']]
        if args.check:
            for entry in entries:
                path = safe_path(entry['path'])
                if not path.is_file() or digest(path) != entry['sha256']:
                    failures.append(entry['path'])
                checked += 1
            continue
        if not archive.exists():
            url = asset['url']
            if not url.startswith('https://github.com/yeniwu46-max/plex/releases/download/'):
                raise ValueError(f'Unexpected asset host: {url}')
            print(f'Downloading {asset["path"]}', flush=True)
            with urllib.request.urlopen(url, timeout=120) as response, tempfile.TemporaryFile() as tmp:
                while chunk := response.read(1024 * 1024):
                    tmp.write(chunk)
                tmp.seek(0)
                install(archive, tmp.read(), asset['sha256'])
        if digest(archive) != asset['sha256']:
            raise ValueError(f'Local archive differs: {asset["path"]}')
        if asset['extract']:
            with zipfile.ZipFile(archive) as z:
                # Only extract explicitly reviewed members, never the entire ZIP.
                for entry in asset['extract']:
                    install(safe_path(entry['path']), z.read(entry['member']), entry['sha256'])
        checked += len(entries)
    for path in failures:
        print(f'MISSING OR DIFFERENT: {path}')
    print(f'Checked {checked} files; {len(failures)} missing or different.')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
