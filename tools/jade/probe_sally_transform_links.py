"""Extract native bit22 parent links, including external ancestors."""
import hashlib
import json
import struct
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from probe_hangar import gao_prefix
from project_paths import report_path


def main():
    parts = json.loads(report_path('stage4-sally-all-parts.json').read_text(encoding='utf-8'))
    index = {e['name']: e for e in entries(PATH)}
    rows = []
    with PATH.open('rb') as archive:
        pending = [(slot, obj['key']) for slot, obj in enumerate(parts['objects'])]
        seen = set()
        while pending:
            slot, object_key = pending.pop(0)
            if object_key in seen:
                continue
            seen.add(object_key)
            if len(seen) > 128:
                raise ValueError('Ancestor traversal exceeds bounded scope')
            raw = decode(archive, index[object_key])
            prefix = gao_prefix(raw)
            flags = int(prefix['flags'], 16)
            row = {'slot': slot, 'key': object_key, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                   'flags': prefix['flags'], 'gao_matrix': prefix['matrix']}
            offset = prefix['after_visual']
            if flags & (1 << 22):
                if offset + 72 > len(raw):
                    raise ValueError('Truncated linked GAO/matrix')
                key, = struct.unpack_from('<I', raw, offset)
                row.update(linked_gao=f'{key:08X}', link_offset=offset,
                           linked_matrix=list(struct.unpack_from('<16f', raw, offset+4)),
                           linked_matrix_flags=struct.unpack_from('<I', raw, offset+68)[0],
                           source_segment_hex=raw[offset:offset+72].hex())
                parent = f'{key:08X}'
                if parent not in ('00000000', 'FFFFFFFF') and parent not in seen:
                    pending.append((None, parent))
            rows.append(row)
    slots = {r['key']: r['slot'] for r in rows}
    for row in rows:
        row['linked_slot'] = slots.get(row.get('linked_gao'))
    result = {'source_list': '7100AF2A', 'objects': rows,
              'limits': 'Native parent direction confirmed by1409b4e70; animation list binding '
                        'and scale-aware animated composition remain pending.'}
    report_path('stage4-sally-transform-links.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'objects': len(rows), 'links': [
        {k: r.get(k) for k in ('slot', 'key', 'linked_gao', 'linked_slot')} for r in rows]}, indent=2))


if __name__ == '__main__':
    main()
