"""Inventory native event/jump keys without pretending to execute the Jade VM."""
import json
import struct
from collections import Counter
from project_paths import ASSET_ROOT, report_path


def decode_event_records(raw):
    """140aeace0 ordinary source8 -> runtime16: signed value, ushort, two bytes."""
    if len(raw) % 8:
        raise ValueError('Misaligned event source records')
    return [{'value_i32': value, 'selector_u16': selector,
             'metadata_u8': metadata, 'dispatch_u8': dispatch}
            for value, selector, metadata, dispatch in struct.iter_unpack('<iHBB', raw)]


def label_target(frames, flags):
    """140b272a0 kind200 scan: first same high-nibble non-200/non-400 key."""
    return next((i for i, frame in enumerate(frames)
                 if frame['flags'] & 0xF000 == flags & 0xF000
                 and frame['flags'] & 0x7C0 not in (0x200, 0x400)), None)


def main():
    rows, kinds, records = [], Counter(), Counter()
    for path in sorted((ASSET_ROOT/'animations'/'sally'/'local-samples').glob('*.json')):
        clip = json.loads(path.read_text(encoding='utf-8'))
        for track in clip['tracks']:
            controls = []
            for frame in track['frames']:
                kind = frame['flags'] & 0x7C0
                if kind == 0x80:
                    continue
                kinds[f'{kind:04X}'] += 1
                row = {'frame_index': frame['index'], 'kind': f'{kind:04X}',
                       'flags': f"{frame['flags']:04X}", 'duration_ticks': frame['tick_raw'],
                       'source_hex': frame['source_hex']}
                if kind == 0x40:
                    raw = bytes.fromhex(frame['aux_records_hex'])
                    if len(raw) % 8:
                        raise ValueError('Misaligned event source records')
                    row['opaque_u32_pairs'] = [list(pair) for pair in struct.iter_unpack('<II', raw)]
                    row['native_records'] = decode_event_records(raw)
                    for pair in row['opaque_u32_pairs']:
                        records[f'{pair[1]:08X}'] += 1
                    row['runtime'] = 'Expanded instructions dispatched via PTR_FUN_141958b78; conditional wait flags8/10'
                elif kind == 0x200:
                    row['same_track_label_target'] = label_target(track['frames'], frame['flags'])
                elif kind == 0x400:
                    row['runtime'] = 'Cross-track search140b27df0 and transition140b27c10 unresolved'
                controls.append(row)
            if controls:
                rows.append({'resource_key': path.stem, 'track_index': track['index'],
                             'slot': track['short1'], 'source_flags': track['source_flags'],
                             'frames': len(track['frames']), 'controls': controls})
    output = {'schema': 'jade-control-track-inventory-v1', 'tracks': rows,
              'kind_counts': dict(kinds), 'opaque_second_word_counts': dict(records),
              'limits': 'Native record fields decoded via140aeace0; opcode/selector meanings unresolved. No VM execution or gameplay effects reproduced.'}
    report_path('stage4-sally-control-tracks.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({'tracks': len(rows), 'control_keys': sum(kinds.values()),
                      'kind_counts': dict(kinds), 'event_records': sum(records.values())}))


if __name__ == '__main__':
    main()
