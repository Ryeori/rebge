"""Compare explicit packed-XYZ decode arithmetic with a saved native oracle."""
import json
import math
import struct
from project_paths import ASSET_ROOT, report_path
from jade_animation import packed_quaternion_float32


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def main():
    snapshot = json.loads(report_path('stage4-sally-runtime-20261008-145025.json').read_text())
    rows = []
    for name, key in [('primary', '26000546'), ('transition', '2600313F')]:
        source = json.loads((ASSET_ROOT/'animations/sally/local-samples'/f'{key}.json').read_text())
        live = snapshot['animation_state']['instances'][name]['clip_link']['tracks']
        original_errors, native_errors, missing = [], [], {}
        for track, runtime in zip(source['tracks'], live):
            for frame, captured in zip(track['frames'], runtime['frame_headers']):
                transform = frame.get('transform', {})
                if 'packed_rotation' in transform and 'quaternion_xyzw' in captured:
                    actual = captured['quaternion_xyzw']
                    original = [f32(v) for v in transform['quaternion_xyzw']]
                    recomputed = packed_quaternion_float32(transform['packed_rotation'])
                    original_errors.append(max(abs(a-b) for a,b in zip(original,actual)))
                    native_errors.append(max(abs(a-b) for a,b in zip(recomputed,actual)))
                elif not any(field in transform and field in captured for field in ('quaternion_xyzw','vector_xyz')):
                    reason = ('delta_rotation' if 'rotation_delta_hex' in transform else
                              'float3_channels' if 'float3_channels' in transform else 'other')
                    missing[reason] = missing.get(reason,0)+1
        rows.append({'instance':name,'key':key,'packed_keys_checked':len(native_errors),
                     'previous_max_error':max(original_errors,default=None),
                     'float32_max_error':max(native_errors,default=None),
                     'float32_exact_keys':sum(error==0 for error in native_errors),
                     'unverified_categories':missing})
    result = {'rows': rows, 'limits':'Saved unsynchronised oracle; explicit packed XYZ only. '
              'No delta decoding, pose interpolation or gameplay parity established.'}
    report_path('stage43-animation-float-precision.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
