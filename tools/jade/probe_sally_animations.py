"""Bounded animation decoding; retain failed resources without inventing poses."""
import collections
import hashlib
import json
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from jade_animation import decode_animation, encode_animation
from project_paths import report_path, ASSET_ROOT


def main():
    actions = json.loads(report_path('stage4-sally-actions.json').read_text(encoding='utf-8'))
    index = {e['name']: e for e in entries(PATH)}
    output = ASSET_ROOT / 'animations' / 'sally' / 'local-samples'
    output.mkdir(parents=True, exist_ok=True)
    rows, masks = [], collections.Counter()
    with PATH.open('rb') as archive:
        for resource in actions['linked_resources']:
            key = resource['key']
            data = decode(archive, index[key])
            row = {'key': key, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            try:
                parsed = decode_animation(data)
                parsed['source'] = {'archive': 'Resources.pak', 'key': key,
                                    'sha256': row['sha256'],
                                    'converter': 'jade_animation.py/v1'}
                if encode_animation(parsed) != data:
                    raise ValueError('Segment roundtrip mismatch')
                frames = [f for t in parsed['tracks'] for f in t['frames']]
                transforms = [f['transform'] for f in frames if 'transform' in f]
                for t in transforms:
                    masks[f'{t["flags"]:04X}'] += 1
                row.update(status='decoded', tracks=len(parsed['tracks']), frames=len(frames),
                           byte_exact_segment_roundtrip=True,
                           quaternion_samples=sum('quaternion_xyzw' in t for t in transforms),
                           unresolved_deltas=sum('rotation_delta_hex' in t for t in transforms),
                           opaque_tail_bytes=len(parsed['opaque_tail_hex'])//2)
                target = output / f'{key}.json'
                target.write_text(json.dumps(parsed, indent=2, allow_nan=False), encoding='utf-8')
                row['output'] = str(target)
            except (ValueError, OverflowError) as error:
                row.update(status='unsupported', reason=str(error))
            rows.append(row)
    result = {'resources': rows, 'transform_flags': dict(masks),
              'limits': 'Roundtrip verifies boundaries/source preservation, not decoded pose accuracy.'}
    report_path('stage4-sally-animations.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'resources': len(rows), 'statuses': dict(collections.Counter(r['status'] for r in rows)),
                      'frames': sum(r.get('frames', 0) for r in rows),
                      'quaternion_samples': sum(r.get('quaternion_samples', 0) for r in rows),
                      'unresolved_deltas': sum(r.get('unresolved_deltas', 0) for r in rows),
                      'failure_reasons': dict(collections.Counter(r.get('reason') for r in rows if r['status'] != 'decoded'))}, indent=2))


if __name__ == '__main__':
    main()
