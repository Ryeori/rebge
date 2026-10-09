"""Locate container-backed Wwise banks/media and validate chunk boundaries."""
import json
import struct
from pathlib import Path
from bpak_reader import entries, decode
from project_paths import report_path

GAME = Path('E:/SteamLibrary/steamapps/common/Beyond Good and Evil - 20th Anniversary Edition')


def bank_chunks(data):
    offset, chunks = 0, []
    while offset < len(data):
        if offset+8 > len(data):
            raise ValueError('Truncated bank chunk header')
        tag, size = struct.unpack_from('<4sI', data, offset)
        if offset+8+size > len(data):
            raise ValueError('Bank chunk exceeds resource')
        row = {'tag': tag.decode('ascii'), 'offset': offset, 'size': size}
        if tag == b'BKHD' and size >= 8:
            row['version'], row['bank_id'] = struct.unpack_from('<II', data, offset+8)
        chunks.append(row)
        offset += 8+size
    return chunks


def main():
    rows = []
    for path in sorted(GAME.rglob('*.pak')):
        with path.open('rb') as archive:
            for entry in entries(path):
                if entry['kind'] != 0 or not entry['name'].lower().endswith(('.bnk', '.wem', '.pck')):
                    continue
                row = {'archive': str(path), **entry}
                if entry['name'].lower().endswith('.bnk'):
                    row['chunks'] = bank_chunks(decode(archive, entry))
                rows.append(row)
    report_path('stage4-wwise-bank-inventory.json').write_text(json.dumps({'resources': rows,
        'limits': 'Read-only inventory/chunk validation. No media decoding or bank semantics inferred.'}, indent=2), encoding='utf-8')
    print(json.dumps({'resources': len(rows), 'banks': [r['name'] for r in rows if 'chunks' in r]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
