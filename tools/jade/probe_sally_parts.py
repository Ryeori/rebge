"""Inspect the observed Sally 47-GAO chain without assigning skeleton semantics."""
import hashlib
import json
import struct
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from probe_character_resources import inspect_keys
from jade_mesh import parse_mesh
from project_paths import report_path


def main():
    index = {entry['name']: entry for entry in entries(PATH)}
    with PATH.open('rb') as archive:
        data = decode(archive, index['7100AF2A'])
        if len(data) % 8:
            raise ValueError('Unaligned tagged object list')
        pairs = [struct.unpack_from('<I4s', data, offset)
                 for offset in range(0, len(data), 8)]
        if any(tag != b'.gao' for _, tag in pairs):
            raise ValueError('Unexpected object-list tag')
        keys = [f'{key:08X}' for key, _ in pairs]
        objects = inspect_keys(keys)
        meshes = {}
        for obj in objects:
            for key in obj.get('gao', {}).get('visual_keys', [])[:1]:
                if isinstance(key, int):
                    key = f'{key:08X}'
                if key in meshes or key not in index:
                    continue
                raw = decode(archive, index[key])
                row = {'key': key, 'size': len(raw),
                       'sha256': hashlib.sha256(raw).hexdigest()}
                try:
                    mesh = parse_mesh(raw)
                    positions = mesh['positions']
                    row.update(vertices=len(positions),
                               triangles=sum(len(s['triangles']) for s in mesh['submeshes']),
                               submeshes=len(mesh['submeshes']), mask=mesh['mask'],
                               trailing_size=mesh['trailing_size'],
                               bounds=[[min(p[i] for p in positions),
                                        max(p[i] for p in positions)]
                                       for i in range(3)] if positions else [])
                except (ValueError, NotImplementedError, struct.error) as error:
                    row['unsupported'] = str(error)
                meshes[key] = row
    result = {'source_list': '7100AF2A',
              'source_sha256': hashlib.sha256(data).hexdigest(),
              'object_count': len(objects), 'objects': objects,
              'geometry': list(meshes.values()),
              'limitations': ['List order is preserved; bone identity is unproven.',
                              'Geometry role and native consumers remain unproven.',
                              'Mesh roundtrip preserves unknown bytes; it does not interpret them.']}
    output = report_path('stage4-sally-all-parts.json')
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'objects': len(objects),
                      'geometry': len(meshes),
                      'vertex_counts': sorted({r['vertices'] for r in meshes.values()
                                               if 'vertices' in r}),
                      'unsupported': [r for r in meshes.values() if 'unsupported' in r]}, indent=2))


if __name__ == '__main__':
    main()
