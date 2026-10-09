"""Audit original eye submeshes against the simplified preview material path.

This diagnoses lost material inputs; it does not infer native UV generation.
"""
import json
import struct
from pathlib import Path
from PIL import Image
from project_paths import ASSET_ROOT, report_path


def main():
    scene = json.loads((ASSET_ROOT / 'scenes/sally-playback/controlled-scene.json').read_text())
    mesh = json.loads((ASSET_ROOT / 'models/meshes/sally-6200318D.json').read_text())
    rows = []
    for selector, material_key in ((2, '0700654E'), (3, '07006BC8')):
        batch = next(b for b in scene['batches'] if b['mesh'] == '6200318D' and b['selector'] == selector)
        material = json.loads((ASSET_ROOT / f'materials/sally-{material_key}.json').read_text())
        layers = []
        for layer in material['layers']:
            link, word, flags, value_a, value_b, texture = struct.unpack('<HHIffI', bytes.fromhex(layer['source_hex']))
            image = Image.open(ASSET_ROOT / f'textures/sally-{texture:08X}.png').convert('RGBA')
            layers.append(dict(texture=f'{texture:08X}', source_hex=layer['source_hex'],
                              link_word=link, word_2=word, flags_hex=f'{flags:08X}',
                              values_f32=[value_a, value_b], alpha_range=image.getextrema()[3]))
        submesh = next(s for s in mesh['submeshes'] if s['unknown'] == selector and s['triangles'])
        rows.append(dict(selector=selector, material=material_key, triangles=len(submesh['triangles']),
                         preview_texture=batch['texture'],
                         runtime_projection=batch.get('uv_projection'),
                         preview_uv_min=[min(batch['vertices'][axis::5]) for axis in (3, 4)],
                         preview_uv_max=[max(batch['vertices'][axis::5]) for axis in (3, 4)],
                         source_layers=layers))
    report = dict(eyes=rows, findings=[
        'Both 44-triangle eye submeshes are present in the exported animated scene.',
        'The original iris texture 0802ABB0 exists and has opaque alpha; texture alpha masking alone does not explain the missing iris.',
        'The previous preview assigned source mesh UVs directly to the first material layer and dropped all layer parameters and the second layer 0802ABAE.',
        'The animated preview now applies the bounded native mode6 indexed bone X/Z projection and packed UV scale/offset; second layer remains excluded.',
    ], limitations=[
        'Mode6 no-scale indexed bone X/Z subset reconstructed from decompilation; no independent native GPU UV buffer comparison.',
        'Animated UV offsets, rotations, other projection modes and second-layer composition remain excluded.',
        'No guessed UV normalization or replacement eye texture has been applied.',
    ], native_consumers=['140a36ba0', '140a3e300', '140a3c700', '140a3f750'],
        assembly_evidence='reports/ghidra/raw/stage43-eye-uv-transform-assembly-20261009.json',
        visual_check='reports/bevy/captures/sally-eyes-front-20261009.png: iris and pupil visible in inspected close-up',
        status='Base eye UV projection fixed; full native eye shader parity remains open')
    output = report_path('stage43-sally-eye-material-audit-20261009.json')
    output.write_text(json.dumps(report, indent=2))
    print(output)


if __name__ == '__main__':
    main()
