#!/usr/bin/env python3
"""Convert course materials to Markdown for RAG indexing (MarkItDown optional)."""
from __future__ import annotations

import argparse
from pathlib import Path


def convert_file(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in {'.md', '.markdown', '.txt'}:
        target.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
        return True
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(source))
        target.write_text(result.text_content or '', encoding='utf-8')
        return True
    except ImportError:
        print(f'[skip] MarkItDown not installed for {source.name}; copy as plain text fallback')
        target.write_text(source.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
        return False
    except Exception as exc:
        print(f'[error] {source.name}: {exc}')
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest course materials into rag_docs/')
    parser.add_argument(
        '--source',
        type=Path,
        default=Path('backend/data/course_materials'),
        help='Directory with PDF/DOCX/PPT/MD sources',
    )
    parser.add_argument(
        '--target',
        type=Path,
        default=Path('backend/data/rag_docs'),
        help='Output directory for Markdown chunks',
    )
    args = parser.parse_args()
    if not args.source.is_dir():
        print(f'Source directory not found: {args.source}')
        return
    args.target.mkdir(parents=True, exist_ok=True)
    converted = 0
    for path in sorted(args.source.rglob('*')):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {'.pdf', '.docx', '.pptx', '.md', '.markdown', '.txt', '.html'}:
            continue
        out_name = path.stem + '.md'
        if convert_file(path, args.target / out_name):
            converted += 1
    print(f'Done. {converted} file(s) written to {args.target.resolve()}')


if __name__ == '__main__':
    main()
