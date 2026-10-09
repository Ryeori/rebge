"""Read-only selected Sally action transition tables (1409bdbc0/1409ad760)."""
import argparse
import ctypes
from ctypes import wintypes
import datetime
import json
import struct
from pathlib import Path
from jade_runtime_phase import capture_phase_descriptor

parser = argparse.ArgumentParser()
parser.add_argument('--pid', type=int, required=True)
parser.add_argument('--base', type=lambda x: int(x, 0), required=True)
parser.add_argument('--actions', nargs='+', type=int, default=[0, 1, 3, 4, 54])
args = parser.parse_args()
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
handle = kernel.OpenProcess(0x1010, False, args.pid)
if not handle:
    raise ctypes.WinError(ctypes.get_last_error())

def read(address, size):
    if address < 0x10000 or not 0 < size <= 65536:
        raise ValueError('Invalid bounded read')
    buffer = ctypes.create_string_buffer(size)
    count = ctypes.c_size_t()
    if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(count)) or count.value != size:
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.raw

def pointer(address):
    return struct.unpack('<Q', read(address, 8))[0]

try:
    actor = pointer(args.base + 0x2157ec8)
    component = pointer(pointer(actor + 0x20))
    action_table = pointer(component + 0x98)
    count = struct.unpack('<H', read(action_table, 2))[0]
    if not 0 < count <= 4096:
        raise ValueError('Unexpected action count')
    actions = []
    for index in args.actions:
        if not 0 <= index < count:
            raise ValueError('Action index outside runtime table')
        address = pointer(action_table + 16 + index * 8)
        descriptor = capture_phase_descriptor(read, address)
        for phase in descriptor.get('records', []):
            raw = bytes.fromhex(phase['raw_hex'])
            table = struct.unpack_from('<Q', raw, 8)[0]
            if not table:
                continue
            header = read(table, 24)
            entries, n = struct.unpack_from('<QI', header)
            if not 0 <= n <= 4096:
                raise ValueError('Unexpected transition count')
            listing = read(entries, n * 16) if n else b''
            rows = []
            for offset in range(0, len(listing), 16):
                key, record = struct.unpack_from('<QQ', listing, offset)
                value = read(record, 4)
                target, flags, duration = struct.unpack('<HBB', value)
                rows.append(dict(requested=key, target=target, flags=flags,
                    duration_byte=duration, address=hex(record), raw_hex=value.hex(),
                    record_unchanged=read(record,4)==value))
            phase['transition_table'] = dict(address=hex(table), header_hex=header.hex(),
                listing_hex=listing.hex(), rows=rows,
                unchanged=read(table, 24)==header and (not n or read(entries, n*16)==listing))
        actions.append(dict(index=index, descriptor=descriptor))
    path = Path('reports/jade') / ('stage43-action-transition-tables-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    path.write_text(json.dumps(dict(pid=args.pid, actor=hex(actor), component=hex(component),
        action_table=hex(action_table), actions=actions,
        limitations=['Sequential reads; table stability is not callback input proof.']), indent=2)+'\n')
    print(path)
finally:
    kernel.CloseHandle(handle)
