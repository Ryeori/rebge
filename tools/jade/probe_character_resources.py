"""Bounded resource lookup for keys observed in native character callbacks."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from bpak_reader import entries, decode
from jade_scene_probe import PATH
from probe_hangar import gao_prefix
from jade_mesh import Cursor
from project_paths import report_path


def inspect_keys(keys):
    index = {entry['name']: entry for entry in entries(PATH)}
    callbacks = [row for row in json.loads(report_path('stage4-native-callbacks.json').read_text())['callbacks']
                 if 0x01000000 <= int(row['key'], 16) < 0xffffffff]
    result = []
    with PATH.open('rb') as archive:
        for key in keys:
            key = f'{int(key, 16):08X}'
            row = {'key': key, 'present': key in index}
            if key in index:
                entry = index[key]
                if entry['unpacked'] > 4 * 1024 * 1024:
                    row['skipped'] = 'Bounded probe: resource exceeds 4 MiB'
                else:
                    data = decode(archive, entry)
                    row.update(size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                               first_words=[f'{value:08X}' for value in
                                            struct.unpack_from(f'<{min(8,len(data)//4)}I', data)])
                    hits = []
                    for callback in callbacks:
                        offset = data.find(struct.pack('<I', int(callback['key'], 16)))
                        if offset >= 0:
                            hits.append({'name': callback['name'], 'key': callback['key'],
                                         'offset': offset})
                    row['callback_key_occurrences'] = hits
                    tags = []
                    for offset in range(0, len(data)-7, 8):
                        tag = data[offset+4:offset+8]
                        if tag[:1] == b'.' and all(97 <= v <= 122 for v in tag[1:]):
                            reference = f'{struct.unpack_from("<I", data, offset)[0]:08X}'
                            tags.append({'offset': offset, 'key': reference,
                                         'tag': tag.decode(), 'present': reference in index})
                    row['tagged_reference_occurrences'] = tags
                    if data.startswith(b'.gao'):
                        prefix = gao_prefix(data)
                        row['gao'] = prefix
                        flags = int(prefix['flags'], 16)
                        unsupported = 0  # bit23 reuses action_words[0]; native1409ea250 adds no bytes
                        if unsupported:
                            row['actor_tail_limit'] = (
                                f'Additional native pre-action branches: {unsupported:08X}; '
                                'references not guessed')
                        else:
                            c = Cursor(data); c.pos = prefix['after_visual']
                            if flags & (1 << 22):
                                row['linked_gao'] = f'{c.read("I"):08X}'
                                c.skip(68)
                            if flags & 2:
                                row['pre_action_words'] = c.read('4I')
                            if flags & (1 << 21):
                                count = c.read('I')
                                if count > 65536:
                                    raise ValueError('Unreasonable GAO array count')
                                # Native matrix reader68 plus64 legacy bytes,
                                # or key+word8 when source bit24 is set.
                                stride = 8 if flags & (1 << 24) else 132
                                row['pre_action_array'] = {'count': count, 'stride': stride}
                                c.skip(count * stride)
                            if flags & (1 << 13):
                                row['action_words'] = c.read('4I'); c.skip(28)
                                if flags & (1 << 23):
                                    row['visual_variant_descriptor'] = f"{row['action_words'][0]:08X}"
                            refs = {}
                            for bit, label in ((5, 'behavior'), (25, 'extra25'),
                                               (27, 'brain'), (18, 'extra18'),
                                               (4, 'extra_object')):
                                if flags & (1 << bit):
                                    refs[label] = f'{c.read("I"):08X}'
                            row['actor_references'] = refs
                            row['unparsed_tail_offset']=c.pos
                            if len(data)-c.pos<=4096:
                                row['unparsed_tail_hex']=data[c.pos:].hex()
                            if c.rebuild() != data:
                                raise ValueError('GAO prefix roundtrip failed')
                            row['prefix_roundtrip'] = True
            result.append(row)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keys', nargs='+', required=True)
    parser.add_argument('--output', type=Path,
                        default=report_path('stage4-character-resource-probe.json'))
    args = parser.parse_args()
    rows = inspect_keys(args.keys)
    args.output.write_text(
        json.dumps(rows, indent=2), encoding='utf-8')
    print(json.dumps(rows, indent=2))
