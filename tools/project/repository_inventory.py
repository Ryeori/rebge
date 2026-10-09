"""Inventory this checkout's source bundle without creating a Git repository.

Supports the positive ignore rules used by this project's .gitignore. Git remains
authoritative once the user creates the repository; negated rules are rejected.
"""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    patterns = [s.strip() for s in (ROOT / '.gitignore').read_text().splitlines()
                if s.strip() and not s.lstrip().startswith('#')]
    if any(p.startswith('!') for p in patterns):
        raise ValueError('Negated ignore rules require git check-ignore instead')

    def ignored(path):
        parts = path.parts
        prefixes = ['/'.join(parts[:i]) for i in range(1, len(parts) + 1)]
        for pattern in patterns:
            pattern = pattern.rstrip('/')
            targets = prefixes if '/' in pattern else parts
            if any(fnmatch.fnmatchcase(target, pattern) for target in targets):
                return True
        return False

    files = []
    forbidden = []
    for directory, dirs, names in os.walk(ROOT):
        base = Path(directory).relative_to(ROOT)
        dirs[:] = sorted(d for d in dirs if d != '.git' and not ignored(base / d))
        for name in sorted(names):
            relative = base / name
            if ignored(relative):
                continue
            full = ROOT / relative
            if full.suffix.lower() in {'.exe', '.dll', '.pak', '.wem', '.bnk', '.gpr', '.dmp'}:
                forbidden.append(relative.as_posix())
            files.append(dict(path=relative.as_posix(), bytes=full.stat().st_size,
                              sha256=hashlib.sha256(full.read_bytes()).hexdigest()))
    report = dict(schema='source-repository-inventory-v1', files=files,
                  file_count=len(files), bytes=sum(f['bytes'] for f in files),
                  unexpected_binary_files=forbidden,
                  limits=['Positive local ignore rules; verify git status after repository creation.',
                          'Inventory is not a license or external publication authorization.'])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
    if forbidden:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
