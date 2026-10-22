"""Prepare the existing SQLite/systemd host without changing its running service."""
from pathlib import Path
import argparse
import json
import shutil
import sqlite3
import subprocess

ROOT = Path('/opt/plex-a3')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('release')
    args = parser.parse_args()
    release = Path(args.release).resolve()
    if release.parent != ROOT / 'releases':
        raise SystemExit('Release must be a direct child of /opt/plex-a3/releases.')
    current, new = ROOT / 'backend', release / 'backend'
    if not (new / 'app').is_dir():
        raise SystemExit('Unpack the code-only bundle first.')
    for file in current.glob('.env*'):
        if file.is_file() and file.name != '.env.example':
            shutil.copy2(file, new / file.name)
            (new / file.name).chmod(0o600)
    for name in ('instance','media'):
        source = (current / name).resolve(strict=True)
        if ROOT not in source.parents:
            raise SystemExit('Runtime directory is outside the configured deployment root.')
        destination = new / name
        if not destination.exists():
            destination.symlink_to(source, target_is_directory=True)
        elif destination.resolve() != source:
            raise SystemExit('Refusing to replace a different runtime directory.')
    backup = release / 'preflight.db'
    if backup.exists():
        raise SystemExit('Preflight copy already exists; use a fresh release directory.')
    source = sqlite3.connect(f'file:{current / "instance/learning_system.db"}?mode=ro',uri=True)
    target = sqlite3.connect(backup)
    source.backup(target); source.close(); target.close()
    backup.chmod(0o600)
    print(json.dumps({'prepared':str(release),'preflight_database':str(backup)}))

if __name__ == '__main__':
    main()
