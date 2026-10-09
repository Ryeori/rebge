"""Candidate matching by ordered frame headers, never by pointer guesses."""
import argparse
import json
import struct
from pathlib import Path
from project_paths import report_path
from jade_animation import packed_quaternion_float32
from jade_runtime_tracks import decode_runtime_transform


def signature(tracks, runtime=False):
    return [(track['indexed_slot'] if runtime else track['short1'],
             [(frame['tick_raw'], frame['flags'] & ~6)
              for frame in track['frame_headers' if runtime else 'frames']])
            for track in tracks]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    root = Path(__file__).resolve().parents[2]
    sources = [(p.stem, json.loads(p.read_text())) for p in
               sorted((root/'assets/animations/sally/local-samples').glob('*.json'))]
    results = {}
    for name, instance in snapshot['animation_state']['instances'].items():
        link = instance.get('clip_link', {})
        if link.get('status') != 'captured':
            continue
        target = signature(link['tracks'], True)
        candidates = [key for key, source in sources if signature(source['tracks']) == target]
        results[name] = {'track_count': link['track_count'], 'header_candidates': candidates}
        comparisons = []
        for key in candidates:
            source = next(source for candidate, source in sources if candidate == key)
            checked, missing, errors, equivalent_errors, sign_flips = 0, 0, [], [], 0
            for original, native in zip(source['tracks'], link['tracks']):
                for frame, live in zip(original['frames'], native['frame_headers']):
                    live = dict(live)
                    if 'runtime_payload_hex' in live:
                        live.update(decode_runtime_transform(live['transform_flags'],
                                                             bytes.fromhex(live['runtime_payload_hex'])))
                    transform = frame.get('transform', {})
                    field = next((field for field in ('quaternion_xyzw', 'vector_xyz')
                                  if field in transform and field in live), None)
                    if field is None:
                        channels = transform.get('float3_channels')
                        payload = live.get('runtime_payload_hex')
                        if channels is not None and payload is not None:
                            expected = b''.join(struct.pack('<3f', *channel) for channel in channels)
                            actual = bytes.fromhex(payload)
                            if len(expected) == len(actual):
                                errors.append(0.0 if expected == actual else float('inf'))
                                equivalent_errors.append(errors[-1])
                                checked += 1
                                continue
                        missing += 1
                        continue
                    expected = (packed_quaternion_float32(transform['packed_rotation'])
                                if field == 'quaternion_xyzw' and 'packed_rotation' in transform else
                                [struct.unpack('<f', struct.pack('<f', value))[0]
                                 for value in transform[field]])
                    direct_error = max(abs(a-b) for a, b in zip(expected, live[field]))
                    errors.append(direct_error)
                    opposite_error = (max(abs(a+b) for a,b in zip(expected,live[field]))
                                      if field == 'quaternion_xyzw' else direct_error)
                    equivalent_errors.append(min(direct_error, opposite_error))
                    if opposite_error < direct_error:
                        sign_flips += 1
                    checked += 1
            comparisons.append({'resource_key': key, 'checked_keys': checked,
                                'unverified_keys': missing,
                                'maximum_component_error': max(errors, default=None),
                                'quaternion_sign_flips': sign_flips,
                                'maximum_rotation_equivalent_error': max(equivalent_errors, default=None),
                                'all_checked_within_1e_6': bool(errors) and max(errors) <= 1e-6})
        results[name]['payload_comparisons'] = comparisons
    out = report_path('stage43-runtime-clip-candidates.json')
    result = {'snapshot': str(args.snapshot), 'instances': results,
              'limits': 'Payload comparisons cover decoded quaternion/vector and float3 channel keys only. '
                        'No live pose, interpolation or gameplay parity follows from matching keys. '
                        'Flags bits2/4 ignored because native loader/evaluator rewrite them.'}
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
