"""Export bounded timed channel probes and explicit unsupported coverage."""
import hashlib
import json
from collections import Counter
from jade_animation_sample import sample_local_track, clone_parent_mapping
from project_paths import ASSET_ROOT, report_path


def main():
    links = json.loads(report_path('stage4-sally-transform-links.json').read_text(encoding='utf-8'))
    indexed = [obj for obj in links['objects'] if obj.get('slot') is not None]
    indexed.sort(key=lambda obj: obj['slot'])
    mapping = clone_parent_mapping(indexed)
    reasons = Counter()
    resources = []
    for path in sorted((ASSET_ROOT/'animations'/'sally'/'local-samples').glob('*.json')):
        clip = json.loads(path.read_text(encoding='utf-8'))
        tracks = []
        for track in clip['tracks']:
            duration = sum(frame['tick_raw'] for frame in track['frames'])/60
            row = {'track_index': track['index'], 'slot': track['short1']}
            try:
                row['probes'] = [dict(elapsed_seconds=t, **sample_local_track(track, t))
                                 for t in (0, duration/2, duration, duration+1/60)]
            except ValueError as error:
                row['unsupported'] = str(error)
                reasons[str(error)] += 1
            tracks.append(row)
        resources.append({'key': path.stem,
                          'decoded_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'tracks': tracks})
    result = {'schema': 'jade-timed-local-channel-probes-v1', 'clone_mapping': mapping,
              'resources': resources, 'unsupported_reasons': dict(reasons),
              'limits': 'Four probes per track under explicit terminal-hold policy. '
                        'No actor/world conversion, runtime parent switching, blending, '
                        'event VM, skinning or live parity. Not full animated poses.'}
    target = report_path('stage4-sally-timed-channels.json')
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'resources': len(resources), 'objects': len(mapping),
                      'tracks': sum(len(r['tracks']) for r in resources),
                      'unsupported': sum(reasons.values()), 'reasons': dict(reasons)}))


if __name__ == '__main__':
    main()
