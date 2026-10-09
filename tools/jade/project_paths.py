"""Workspace paths independent of the caller's current directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / 'assets'
GHIDRA_RAW_ROOT = PROJECT_ROOT / 'reports' / 'ghidra' / 'raw'


def report_path(name):
    name = Path(name)
    if name.name != str(name):
        raise ValueError('Report name must be a filename')
    if name.name.startswith('jade-reference-'):
        return PROJECT_ROOT / 'references' / 'jade' / name
    category = 'ghidra' if name.name.startswith('ghidra-') else 'jade'
    return PROJECT_ROOT / 'reports' / category / name
