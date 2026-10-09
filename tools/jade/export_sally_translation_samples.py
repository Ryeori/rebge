"""Local position keys and native linked-parent graph, not a full animated rig."""
import hashlib
import json
from jade_pose import translation_sample, validate_link_graph
from project_paths import ASSET_ROOT, report_path


def main():
    links = json.loads(report_path('stage4-sally-transform-links.json').read_text(encoding='utf-8'))
    depths = validate_link_graph(links['objects'])
    links['native_consumer'] = '1409b4e70: local linked matrix followed by linked GAO ancestors'
    links['limits'] = 'Parent graph and external root confirmed; indexed animation binding and animated scale composition pending.'
    for obj in links['objects']:
        obj['chain_depth_within_list'] = depths[obj['key']]
    rig_dir = ASSET_ROOT / 'skeletons' / 'sally'
    rig_dir.mkdir(parents=True, exist_ok=True)
    (rig_dir / 'gao-parent-links.json').write_text(json.dumps(links, indent=2), encoding='utf-8')
    output = ASSET_ROOT / 'animations' / 'sally' / 'local-translation-samples'
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted((ASSET_ROOT / 'animations' / 'sally' / 'local-samples').glob('*.json')):
        animation = json.loads(path.read_text(encoding='utf-8'))
        tracks = []
        for track in animation['tracks']:
            samples = []
            for frame in track['frames']:
                points = translation_sample(frame)
                if points is not None:
                    samples.append({'frame_index': frame['index'], 'duration_ticks_raw': frame['tick_raw'],
                                    'jade_position': points[0], 'jade_control_points': points[1:],
                                    'bevy_position': [points[0][0], points[0][2], -points[0][1]]})
            if samples:
                tracks.append({'track_index': track['index'], 'native_slot': track['short1'],
                               'samples': samples})
        result = {'schema': 'jade-local-translation-samples-v1', 'source': animation['source'],
                  'tracks': tracks, 'limits': 'Exact key positions, no native time progression or full pose assembly.'}
        out = output / path.name
        out.write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
        rows.append({'key': path.stem, 'samples': sum(len(t['samples']) for t in tracks),
                     'output': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()})
    report = {'resources': rows, 'parent_graph_objects': len(depths),
              'maximum_chain_depth_within_list': max(depths.values())}
    report_path('stage4-sally-translations.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'resources': len(rows), 'position_samples': sum(r['samples'] for r in rows),
                      'graph_objects': len(depths), 'max_chain_depth': max(depths.values())}))


if __name__ == '__main__':
    main()
