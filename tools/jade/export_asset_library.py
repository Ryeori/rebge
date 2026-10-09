"""Private, typed asset library from verified Jade readers; no game modification."""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from bpak_reader import entries, decode
from jade_mesh import parse_mesh
from jade_texture import color_image
from jade_scene_probe import PATH
from jade_localization import export as export_texts
from project_paths import PROJECT_ROOT, ASSET_ROOT, report_path


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def build_library(root):
    root = root.resolve()
    game = PATH.parents[2]
    if not root.is_relative_to(PROJECT_ROOT) or root == PROJECT_ROOT or root.is_relative_to(game):
        raise ValueError('Library must be a subdirectory of this project, outside the game installation')
    folders = ('models/meshes', 'textures', 'materials', 'scenes/D90057F0',
               'texts/en', 'texts/ru', 'animations', 'skeletons', 'collisions',
               'sounds/sfx', 'sounds/music', 'sounds/voice', 'ui', 'vfx',
               'source/Resources.pak')
    for folder in folders:
        (root / folder).mkdir(parents=True, exist_ok=True)
    evidence = json.loads(report_path('hangar-export-validation.json').read_text())
    old_root = Path(evidence['output'])
    scene = json.loads((old_root / 'scene.json').read_text())
    index = {entry['name']: entry for entry in entries(PATH)}
    catalog = {'schema': 1, 'converter': 'rebge-verified-library-v1',
               'root': str(root), 'assets': [], 'unresolved': [],
               'pending_categories': ['animations', 'skeletons', 'collisions',
                                      'sounds', 'ui', 'vfx']}
    with PATH.open('rb') as archive:
        def export_resource(key, category, convert, relative, limits):
            data = decode(archive, index[key])
            destination = root / relative
            convert(data, destination)
            raw_relative = f'source/Resources.pak/{key}.bin'
            (root / raw_relative).write_bytes(data)
            catalog['assets'].append({
                'archive': 'Resources.pak', 'key': key, 'type': category,
                'path': relative, 'source_path': raw_relative,
                'source_sha256': hashlib.sha256(data).hexdigest(),
                'export_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                'limitations': limits})

        for key, info in evidence['meshes'].items():
            if info['kind'] != 1:
                continue
            export_resource(key, 'mesh', lambda data, path: save_json(path, parse_mesh(data)),
                            f'models/meshes/{key}.json',
                            ['Source axes/scale; original payload retained for unknown mesh tails',
                             'Skeleton bindings and native rendering are not yet implemented'])
        for key in evidence['textures']:
            export_resource(key, 'texture', lambda data, path: color_image(data)[1].save(path),
                            f'textures/{key}.png',
                            ['Full-resolution first color stream; mipmaps and auxiliary streams retained in source payload'])
        material_keys = set(evidence['materials']) | {batch['material'] for batch in scene['batches']}
        for key in sorted(material_keys - {'00000000', 'FFFFFFFF'}):
            if key not in evidence['materials']:
                data = decode(archive, index[key])
                kind, legacy = struct.unpack_from('<2I', data)
                position = 8 + legacy
                if kind != 4 or position + 4 > len(data):
                    raise ValueError(f'Unexpected material group {key}')
                count = struct.unpack_from('<I', data, position)[0]
                if count > 256 or position + 4 + count * 4 > len(data):
                    raise ValueError(f'Invalid material group {key}')
                references = [f'{value:08X}' for value in
                              struct.unpack_from(f'<{count}I', data, position + 4)]
                export_resource(key, 'material_group',
                                lambda data, path, references=references:
                                    save_json(path, {'kind': 4, 'materials': references}),
                                f'materials/{key}.json', ['Source header retained; runtime flags unresolved'])
                catalog['assets'][-1]['dependencies'] = references
                continue
            info = evidence['materials'][key]
            export_resource(key, 'material', lambda data, path, info=info: save_json(path, info),
                            f'materials/{key}.json',
                            ['First-layer viewer interpretation; native material flags remain unresolved'])
            catalog['assets'][-1]['dependencies'] = info['layers']

    # Scene geometry retains confirmed transforms; textures resolve relative to library root.
    relative = 'scenes/D90057F0/scene.json'
    save_json(root / relative, scene)
    with PATH.open('rb') as archive:
        scene_source = decode(archive, index['D90057F0'])
    scene_source_path = 'source/Resources.pak/D90057F0.bin'
    (root / scene_source_path).write_bytes(scene_source)
    catalog['assets'].append({'key': 'D90057F0', 'archive': 'Resources.pak',
                             'type': 'scene', 'path': relative,
                             'source_path': scene_source_path,
                             'source_sha256': hashlib.sha256(scene_source).hexdigest(),
                             'export_sha256': hashlib.sha256((root / relative).read_bytes()).hexdigest(),
                             'dependencies': sorted({batch['mesh'] for batch in scene['batches']}),
                             'limitations': evidence['limitations']})
    export_texts(game, report_path('jade-language-key-mapping.json'), root / 'texts',
                 report_path('asset-library-localization.json'))
    for path in sorted((root / 'texts').glob('*/*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        catalog['assets'].append({'type': 'text_group', 'key': data['group'],
                                 'archive': 'Text-en_US.pak' if data['locale'] == 'en' else 'Text-ru.pak',
                                 'locale': data['locale'], 'path': path.relative_to(root).as_posix(),
                                 'txi_key': data['txi_key'], 'txs_key': data['txs_key'],
                                 'source_hashes': {'txi': data['txi_sha256'], 'txs': data['txs_sha256']},
                                 'export_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    catalog['unresolved'].extend(evidence['unsupported'])
    # Verify every registered output; catalog is written only after all succeed.
    for entry in catalog['assets']:
        if hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() != entry['export_sha256']:
            raise ValueError(f'Export digest mismatch: {entry["path"]}')
    save_json(root / 'catalog.json', catalog)
    summary = {'root': str(root), 'assets': len(catalog['assets']),
               'types': {kind: sum(row['type'] == kind for row in catalog['assets'])
                         for kind in sorted({row['type'] for row in catalog['assets']})},
               'unresolved': catalog['unresolved'], 'pending_categories': catalog['pending_categories'],
               'all_export_hashes_verified': True}
    save_json(report_path('asset-library-validation.json'), summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path,
                        default=ASSET_ROOT)
    build_library(parser.parse_args().output)
