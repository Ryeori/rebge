"""Validate Sally's 235 table slots (199 actions) and linked resource headers."""
import collections
import hashlib
import json
import struct
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from jade_actions import decode_action, encode_action
from project_paths import report_path


def main():
    index = {entry['name']: entry for entry in entries(PATH)}
    rows, resources, empty_slots = [], {}, []
    with PATH.open('rb') as archive:
        table = decode(archive, index['71004D9B'])
        if len(table) % 8:
            raise ValueError('Unaligned action list')
        for offset in range(0, len(table), 8):
            key, tag = struct.unpack_from('<I4s', table, offset)
            if key == 0 and tag == bytes(4):
                empty_slots.append(offset // 8)
                continue
            if tag != b'.act':
                raise ValueError('Unexpected action tag')
            key = f'{key:08X}'
            raw = decode(archive, index[key])
            action = decode_action(raw)
            if encode_action(action) != raw:
                raise ValueError(f'Action roundtrip failed: {key}')
            rows.append({'key': key, 'size': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest(),
                         'byte_exact_roundtrip': True, **action})
            for record in action['records']:
                target = record['resource_key']
                if target in resources or target in ('00000000', 'FFFFFFFF'):
                    continue
                row = {'key': target, 'present': target in index}
                if target in index:
                    data = decode(archive, index[target])
                    if len(data) < 4:
                        raise ValueError('Truncated linked resource header')
                    count, flags = struct.unpack_from('<HH', data)
                    row.update(size=len(data), count_u16=count, flags_u16=flags,
                               sha256=hashlib.sha256(data).hexdigest())
                resources[target] = row
    result = {'source_list': '71004D9B', 'slot_count': len(table)//8,
              'empty_slots': empty_slots, 'actions': rows,
              'linked_resources': list(resources.values()),
              'limits': 'Prefixes verified; opaque tails retained, not interpreted. '
                       'Linked-resource count/flags are loader fields, not proven bone/frame semantics.'}
    output = report_path('stage4-sally-actions.json')
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'actions': len(rows),
                      'empty_slots': len(empty_slots),
                      'roundtrips': sum(r['byte_exact_roundtrip'] for r in rows),
                      'record_counts': dict(collections.Counter(len(r['records']) for r in rows)),
                      'linked_resources': len(resources),
                      'missing': [k for k, r in resources.items() if not r['present']],
                      'opaque_tail_bytes': sum(len(r['opaque_tail_hex'])//2 for r in rows)}, indent=2))


if __name__ == '__main__':
    main()
