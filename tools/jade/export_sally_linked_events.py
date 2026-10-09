"""Reproduce observed static ID maps; preserve unresolved literal references."""
import json
import struct
from collections import Counter
from project_paths import GHIDRA_RAW_ROOT, report_path
from jade_vm_link import link_record


def read_table(name):
    if name == 'category2':
        raw = b''.join(bytes.fromhex(json.loads((GHIDRA_RAW_ROOT/f'rebge-stage4-vm-category2-table-part{i}.json').read_text())['result']['structuredContent']['hex_data']) for i in range(5))
    else:
        raw = bytes.fromhex(json.loads((GHIDRA_RAW_ROOT/f'rebge-stage4-vm-{name}-id-table.json').read_text())['result']['structuredContent']['hex_data'])
    return list(struct.iter_unpack('<HH4xQ', raw))


def main():
    tables = {name: read_table(name) for name in ('category', 'type', 'operator', 'category2', 'native')}
    selectors = {}
    for table in tables.values():
        for index, (identifier, _, _) in enumerate(table):
            selectors[identifier] = index
    categories = {identifier: i for i, (identifier, _, _) in enumerate(tables['category'])}
    source = json.loads(report_path('stage4-sally-control-tracks.json').read_text())
    counts = Counter()
    for track in source['tracks']:
        for frame in track['controls']:
            linked = []
            for record in frame.get('native_records', []):
                try:
                    row = link_record(record, categories, selectors)
                except ValueError as error:
                    row = {**record, 'unresolved': str(error)}
                linked.append(row)
                counts['terminal' if row.get('terminal') else 'unresolved' if 'unresolved' in row else 'linked'] += 1
            frame['linked_records'] = linked
    source['link_counts'] = dict(counts)
    source['limits'] = 'Static ID-field linking only. Reference literals require pointer resolution; no VM execution. Earlier direct source-category handler claims superseded.'
    report_path('stage4-sally-linked-events.json').write_text(json.dumps(source, indent=2), encoding='utf-8')
    print(json.dumps(dict(counts)))


if __name__ == '__main__':
    main()
