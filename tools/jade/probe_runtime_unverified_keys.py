"""Classify keys lacking a payload oracle without treating them as matches."""
import json
import struct
from collections import Counter
from project_paths import ASSET_ROOT, report_path


def main():
    snapshot = json.loads(report_path('stage4-sally-runtime-20261008-145025.json').read_text())
    rows = []
    for name, key in [('primary', '26000546'), ('transition', '2600313F')]:
        source = json.loads((ASSET_ROOT/'animations/sally/local-samples'/f'{key}.json').read_text())
        live = snapshot['animation_state']['instances'][name]['clip_link']['tracks']
        for track, runtime in zip(source['tracks'], live):
            for index, (frame, captured) in enumerate(zip(track['frames'], runtime['frame_headers'])):
                transform = frame.get('transform', {})
                if any(field in transform and field in captured for field in ('quaternion_xyzw','vector_xyz')):
                    continue
                channels, payload = transform.get('float3_channels'), captured.get('runtime_payload_hex')
                if channels is not None and payload is not None:
                    expected = b''.join(struct.pack('<3f', *channel) for channel in channels)
                    if len(expected) == len(bytes.fromhex(payload)):
                        continue
                rows.append({'instance':name,'resource_key':key,'track_index':track['index'],
                             'frame_index':index,'frame_flags':frame['flags'],
                             'source_transform':transform,'runtime_frame':captured})
    counts = Counter((row['frame_flags'] & 0x7c0,
                      row['source_transform'].get('flags')) for row in rows)
    result = {'unverified_keys':len(rows),
              'categories':[{'frame_kind':kind,'transform_flags':flags,'count':count}
                            for (kind,flags),count in counts.items()], 'keys':rows}
    report_path('stage43-unverified-key-categories.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'count':len(rows),'categories':result['categories'],'examples':rows[:2]}))


if __name__ == '__main__':
    main()
