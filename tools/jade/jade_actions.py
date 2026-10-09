"""Confirmed ordinary-branch action prefix (1409bdbc0); tail remains opaque."""
import struct

RECORD = struct.Struct('<III4BHBB')


def decode_transition_tables(action):
    """Ordinary padded source branch1409bdbc0, runtime entries key64/pointer64.

    Source keys occupy8 bytes: native loader consumes low signed32 and skips
    the remaining word. Preserve that word; do not interpret it as a predicate.
    These are action transition rules, not the VM conditions requesting actions.
    """
    data = bytes.fromhex(action['opaque_tail_hex'])
    offset = 0
    tables = []
    for phase, record in enumerate(action['records']):
        if record['word1'] in (0, 0xffffffff):
            continue
        if offset + 16 > len(data):
            raise ValueError('Truncated transition table header')
        header = struct.unpack_from('<4I', data, offset)
        count = header[1]
        if count > 4096 or offset + 16 + count * 12 > len(data):
            raise ValueError('Invalid transition table bounds')
        rows = []
        for index in range(count):
            key, skipped = struct.unpack_from('<II', data, offset + 16 + index * 8)
            target, flags, duration = struct.unpack_from('<HBB', data, offset + 16 + count * 8 + index * 4)
            rows.append(dict(requested=key, skipped_key_word=skipped, target=target,
                flags=flags, duration_byte=duration))
        end = offset + 16 + count * 12
        tables.append(dict(phase=phase, source_offset=action['tail_offset']+offset,
            header_words=list(header), rows=rows, raw_hex=data[offset:end].hex()))
        offset = end
    return dict(tables=tables, unparsed_tail_hex=data[offset:].hex(),
        limitations='VM request predicates are external; skipped header/key words retained without inferred semantics.')


def decode_action(data):
    if len(data) < 4:
        raise ValueError('Truncated action header')
    count, byte1, reserved = struct.unpack_from('<BBH', data)
    end = 4 + count * RECORD.size
    if end > len(data):
        raise ValueError('Truncated action records')
    records = []
    for offset in range(4, end, RECORD.size):
        values = RECORD.unpack_from(data, offset)
        records.append({'resource_key': f'{values[0]:08X}',
                        'word1': values[1],
                        'third_resource_key': f'{values[2]:08X}',
                        'bytes12_15': list(values[3:7]),
                        'word16': values[7], 'byte18': values[8],
                        'padding19': values[9]})
    return {'schema': 'jade-action-prefix-v1', 'header_byte1': byte1,
            'header_reserved_u16': reserved, 'records': records,
            'tail_offset': end, 'opaque_tail_hex': data[end:].hex(),
            'limitations': 'Record semantics and conditional tail not fully decoded.'}


def encode_action(action):
    records = action['records']
    data = bytearray(struct.pack('<BBH', len(records), action['header_byte1'],
                                 action['header_reserved_u16']))
    for record in records:
        data.extend(RECORD.pack(int(record['resource_key'], 16), record['word1'],
                                int(record['third_resource_key'], 16),
                                *record['bytes12_15'], record['word16'],
                                record['byte18'], record['padding19']))
    data.extend(bytes.fromhex(action['opaque_tail_hex']))
    return bytes(data)
