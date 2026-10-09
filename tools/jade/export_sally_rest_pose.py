"""Assemble the original GAO linked transforms, without an animation binding guess."""
import hashlib
import json
from jade_pose import assemble_rest_pose, validate_link_graph
from project_paths import ASSET_ROOT, report_path


def main():
    links = json.loads(report_path('stage4-sally-transform-links.json').read_text(encoding='utf-8'))
    matrices = assemble_rest_pose(links['objects'])
    depths = validate_link_graph(links['objects'])
    rows = []
    for obj in links['objects']:
        matrix = matrices[obj['key']]
        x, y, z = matrix[12:15]
        rows.append({'key': obj['key'], 'slot': obj['slot'], 'parent': obj.get('linked_gao'),
                     'source_sha256': obj['source_sha256'], 'chain_depth': depths[obj['key']],
                     'jade_world_matrix': matrix, 'bevy_world_position': [x, z, -y],
                     'source_gao_world_matrix_max_difference': max(abs(a-b) for a,b in zip(matrix, obj['gao_matrix']))})
    result = {'schema': 'jade-gao-rest-pose-v1', 'objects': rows,
              'native_evidence': ['1409b4e70', '140ae9c00', '140ae9420'],
              'limits': 'Original linked GAO pose, not an animated pose. No skinning or indexed animation binding. '
                        'Scale bit8 explicitly rejected.'}
    target = ASSET_ROOT / 'skeletons' / 'sally' / 'gao-rest-pose.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    report = {'output': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'objects': len(rows), 'maximum_chain_depth': max(depths.values()),
              'max_difference_from_source_gao': max(r['source_gao_world_matrix_max_difference'] for r in rows),
              'limits': result['limits']}
    report_path('stage4-sally-rest-pose.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
