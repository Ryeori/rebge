"""Private Wwise source extraction with hashes and bounded embedded media index."""
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from bpak_reader import decode
from probe_wwise_banks import bank_chunks
from project_paths import ASSET_ROOT, report_path


def media_index(data):
    chunks = {c['tag']: c for c in bank_chunks(data)}
    if 'DIDX' not in chunks:
        return []
    if 'DATA' not in chunks or chunks['DIDX']['size'] % 12:
        raise ValueError('Invalid embedded media index')
    index, payload = chunks['DIDX'], chunks['DATA']
    rows = []
    for media_id, offset, size in struct.iter_unpack('<III', data[index['offset']+8:index['offset']+8+index['size']]):
        if offset+size > payload['size']:
            raise ValueError('Embedded media exceeds DATA')
        rows.append({'media_id': media_id, 'offset': payload['offset']+8+offset, 'size': size})
    return rows


def riff_format(data):
    if len(data) < 12 or data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        return {'unsupported': 'Not RIFF WAVE'}
    pos = 12
    while pos+8 <= len(data):
        tag, size = struct.unpack_from('<4sI', data, pos)
        if pos+8+size > len(data):
            return {'unsupported': 'Truncated RIFF chunk'}
        if tag == b'fmt ' and size >= 16:
            codec, channels, rate, average, align, bits = struct.unpack_from('<HHIIHH', data, pos+8)
            return {'codec_tag': codec, 'channels': channels, 'sample_rate': rate, 'bits': bits}
        pos += 8+size+(size & 1)
    return {'unsupported': 'Missing fmt chunk'}


def main():
    inventory = json.loads(report_path('stage4-wwise-bank-inventory.json').read_text())['resources']
    rows, codecs = [], Counter()
    handles = {}
    try:
        for n, entry in enumerate(inventory):
            path = Path(entry['archive'])
            if path not in handles:
                handles[path] = path.open('rb')
            raw = decode(handles[path], entry)
            bank = entry['name'].lower().endswith('.bnk')
            target = ASSET_ROOT/'audio'/'wwise-source'/path.stem/('banks' if bank else 'streamed')/Path(entry['name']).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            row = {'archive': path.name, 'resource_name': entry['name'],
                   'path': str(target.relative_to(ASSET_ROOT)), 'size': len(raw),
                   'sha256': hashlib.sha256(raw).hexdigest()}
            if bank:
                row['embedded_media'] = media_index(raw)
                for media in row['embedded_media']:
                    media['sha256'] = hashlib.sha256(raw[media['offset']:media['offset']+media['size']]).hexdigest()
            else:
                row['format'] = riff_format(raw)
                codecs[str(row['format'].get('codec_tag', 'unsupported'))] += 1
            rows.append(row)
            if n % 1000 == 0:
                print(f'Extracted {n+1}/{len(inventory)}', flush=True)
    finally:
        for handle in handles.values():
            handle.close()
    result = {'schema': 'wwise-private-source-manifest-v1', 'resources': rows,
              'codec_counts': dict(codecs), 'limits': 'Original encoded audio and banks, not editable PCM. Embedded media remain in banks with validated offsets; event/media semantics pending.'}
    report_path('stage4-wwise-audio-source-export.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'files': len(rows), 'bytes': sum(r['size'] for r in rows),
                      'embedded_media': sum(len(r.get('embedded_media', [])) for r in rows),
                      'codecs': dict(codecs)}), flush=True)


if __name__ == '__main__':
    main()
