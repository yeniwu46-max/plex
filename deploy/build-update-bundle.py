"""Build a code-only update from Git's file inventory; never copy runtime data."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if output.exists():
        raise SystemExit('Choose a new output path; existing releases are never overwritten.')
    names = subprocess.check_output(
        ['git', 'ls-files', '-c', '-o', '--exclude-standard', '-z'], cwd=ROOT,
    ).decode('utf-8').split('\0')
    files = {}
    for name in set(names):
        if not name.startswith(('backend/', 'deploy/code-sandbox/', 'deploy/plex-server/')):
            continue
        path = ROOT / name
        if not path.is_file() or any(part in {'instance', 'media', '.cache', '__pycache__', 'reports'} for part in path.parts):
            continue
        if path.name.startswith('.env') and path.name != '.env.example':
            continue
        if path.suffix in {'.db', '.sqlite', '.sqlite3', '.pyc', '.log', '.pem', '.key'}:
            continue
        files[name] = path
    dist = ROOT / 'frontend/dist'
    if not (dist / 'index.html').is_file():
        raise SystemExit('Run npm run build in frontend first.')
    for path in dist.rglob('*'):
        if path.is_file():
            files['frontend-dist/' + path.relative_to(dist).as_posix()] = path
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, 'w:gz') as archive:
        for name, path in sorted(files.items()):
            archive.add(path, arcname=name, recursive=False)
    manifest = {'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())}}
    output.with_suffix(output.suffix + '.manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'archive':str(output),'files':len(files),'bytes':output.stat().st_size,'sha256':manifest['archive_sha256']}))


if __name__ == '__main__':
    main()
