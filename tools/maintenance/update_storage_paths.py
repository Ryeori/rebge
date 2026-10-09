"""Update project metadata after moving private data into this workspace."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAPPINGS = {
    'C:/Users/Dan/AppData/Local/rebge/assets': ROOT / 'assets',
    'C:/Users/Dan/AppData/Local/rebge/captures': ROOT / 'reports/bevy/captures',
    'C:/Users/Dan/AppData/Local/Temp/rebge-assets': ROOT / 'assets/legacy-exports',
}


def replace(text):
    for old, new in MAPPINGS.items():
        text = text.replace(old, new.as_posix())
        text = text.replace(old.replace('/', '\\'), str(new))
    return text


def walk(value):
    if isinstance(value, str):
        return replace(value)
    if isinstance(value, list):
        return [walk(item) for item in value]
    if isinstance(value, dict):
        return {key: walk(item) for key, item in value.items()}
    return value


for path in (ROOT / 'reports').rglob('*.json'):
    if path.name in ('storage-migration.json', 'layout-migration.json'):
        continue
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    updated = walk(value)
    if updated != value:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')

catalog_path = ROOT / 'assets/catalog.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
catalog['root'] = str(ROOT / 'assets')
for row in catalog['assets']:
    path = ROOT / 'assets' / row['path']
    if hashlib.sha256(path.read_bytes()).hexdigest() != row['export_sha256']:
        raise ValueError(f'Asset changed during relocation: {row["path"]}')
catalog_path.write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')

for path in [ROOT / 'README.md', *(ROOT / 'docs').glob('*.md')]:
    text = replace(path.read_text(encoding='utf-8-sig'))
    text = text.replace('%LOCALAPPDATA%/rebge/assets/', './assets/')
    text = text.replace('%LOCALAPPDATA%/rebge/captures/', './reports/bevy/captures/')
    text = text.replace('$env:TEMP\\rebge-assets\\stage1-localization', '.\\assets\\legacy-exports\\stage1-localization')
    text = text.replace('$env:TEMP/rebge-assets/stage2-hangar', './assets/legacy-exports/stage2-hangar')
    text = text.replace('TEMP/rebge-stage4-', 'reports/ghidra/raw/rebge-stage4-')
    path.write_text(text, encoding='utf-8')

print(f'{len(catalog["assets"])} asset hashes verified after relocation')
