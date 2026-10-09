"""Prepare a private Engine.pak candidate; never writes to the installation."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('E:/SteamLibrary/steamapps/common/Beyond Good and Evil - 20th Anniversary Edition/Data/Paks/Engine.pak')
OUT = ROOT / 'reports/ghidra/cheats-config'


def parse(data):
    magic, version, priority, flags, count, size = struct.unpack_from('<4s5I', data)
    assert magic == b'BPAK'
    pos = len(data) - size
    rows = []
    for _ in range(count):
        start = pos
        kind = data[pos]
        pos += 1
        n, = struct.unpack_from('<I', data, pos)
        pos += 4
        if kind == 0:
            name = data[pos:pos+n].decode('utf-8')
            pos += n
        else:
            assert kind == 1
            name = f'{n:08X}'
        prefix = data[start:pos]
        unpacked, packed, opaque, offset = struct.unpack_from('<IIQQ', data, pos)
        pos += 24
        assert offset + 24 + (packed or unpacked) <= len(data) - size
        payload = data[offset+24:offset+24+(packed or unpacked)]
        rows.append((name, prefix, unpacked, packed, opaque, payload))
    assert pos == len(data)
    return (version, priority, flags), rows


def main():
    original = SOURCE.read_bytes()
    header, rows = parse(original)
    ini = (ROOT / 'reports/ghidra/BGE-original-20261010.ini').read_bytes()
    assert b'[Cheats]' not in ini
    patched = ini + b'\r\n\r\n[Cheats]\r\nEnabled=1\r\n'
    payloads, index = bytearray(), bytearray()
    for name, prefix, unpacked, packed, opaque, payload in rows:
        if name == 'BGE.ini':
            assert unpacked == len(ini)
            unpacked, packed, payload = len(patched), 0, patched
        index += prefix + struct.pack('<IIQQ', unpacked, packed, opaque, len(payloads))
        payloads += payload
    candidate = struct.pack('<4s5I', b'BPAK', *header, len(rows), len(index)) + payloads + index
    checked_header, checked = parse(candidate)
    assert header == checked_header
    checks = []
    for old, new in zip(rows, checked, strict=True):
        assert old[:2] == new[:2] and old[4] == new[4]
        if old[0] == 'BGE.ini':
            assert new[5] == patched and new[3] == 0
        else:
            assert old == new
        checks.append(dict(name=old[0], changed=old != new, stored_sha256=hashlib.sha256(new[5]).hexdigest()))
    assert sum(c['changed'] for c in checks) == 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'Engine-cheats.pak').write_bytes(candidate)
    (OUT / 'BGE-cheats.ini').write_bytes(patched)
    report = dict(source=str(SOURCE), source_sha256=hashlib.sha256(original).hexdigest(),
                  candidate_sha256=hashlib.sha256(candidate).hexdigest(), header=header,
                  entries=checks, verification='structural round trip; unchanged stored payloads exact; not game-tested')
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
