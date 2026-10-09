"""Optional local automation dependencies; no installation or device mutation."""
import os
from pathlib import Path
import sys


def configure_imports():
    project = Path(__file__).resolve().parents[2]
    roots = []
    for key in ('REBGE_UM_ROOT', 'REBGE_VGAMEPAD_ROOT'):
        if os.environ.get(key):
            path = Path(os.environ[key]).expanduser()
            if not path.is_dir():
                raise RuntimeError(f'{key} directory is missing: {path}')
            roots.append(path)
    # Backward-compatible local installs, never copied into the source repo.
    roots.append(project / 'tools/game-automation/python/vgamepad-0.1.0')
    cache = Path.home() / '.codex/plugins/cache/universal-modder/universal-modder'
    if cache.is_dir():
        roots.extend(sorted(cache.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True))
    for root in reversed(roots):
        if root.is_dir():
            sys.path.insert(0, str(root))

