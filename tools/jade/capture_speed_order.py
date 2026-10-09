"""Bounded readonly speed/direction observer; sequential reads, no hooks."""
import argparse
import ctypes
import datetime
import json
import struct
import time
from ctypes import wintypes
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pid', type=int, required=True)
p.add_argument('--base', type=lambda x: int(x, 0), required=True)
a = p.parse_args()
k = ctypes.WinDLL('kernel32', use_last_error=True)
k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k.OpenProcess.restype = wintypes.HANDLE
k.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k.ReadProcessMemory.restype = wintypes.BOOL
k.CloseHandle.argtypes = [wintypes.HANDLE]
h = k.OpenProcess(0x1010, False, a.pid)
if not h:
    raise ctypes.WinError(ctypes.get_last_error())

def read(address, size):
    if address < 0x10000 or not 0 < size <= 4096:
        raise ValueError('Invalid bounded memory read')
    buf = ctypes.create_string_buffer(size)
    count = ctypes.c_size_t()
    if not k.ReadProcessMemory(h, address, buf, size, ctypes.byref(count)) or count.value != size:
        raise ctypes.WinError(ctypes.get_last_error())
    return buf.raw

def ptr(address):
    return struct.unpack('<Q', read(address, 8))[0]

def glob(address):
    return a.base + address - 0x140000000

rows, error, iterations = [], None, 0
start = time.perf_counter()
try:
    actor = ptr(glob(0x142157ec8))
    component = ptr(ptr(actor + 0x20))
    brain = ptr(ptr(ptr(actor + 0x28) + 8) + 0x78)
    last = None
    while time.perf_counter() - start < 3 and iterations < 60000 and len(rows) < 6000:
        iterations += 1
        tick = time.perf_counter() - start
        state = read(brain + 0x10c4, 0x38)
        direction = read(brain + 0xa50, 12)
        gate = read(brain + 0x1dc, 4)
        norm_pointer = ptr(glob(0x142141a68))
        norm = read(norm_pointer, 4)
        world_pointer = ptr(actor + 0x10)
        world = read(world_pointer, 68)
        comp = read(component + 0x70, 0x40)
        instance = struct.unpack_from('<Q', comp, 0)[0]
        header = read(instance, 3)
        flags = read(actor + 4, 4)
        delta = read(glob(0x1420a3318), 4)
        filtered = read(brain + 0x1e4, 12)
        input_pointer = ptr(glob(0x1421550a0))
        raw_input = read(input_pointer, 12)
        signature = (state, direction, gate, norm, world, comp, header, flags, delta, filtered, raw_input)
        if signature != last:
            unchanged = (read(brain + 0x10c4, 0x38) == state and
                         read(brain + 0xa50, 12) == direction and
                         read(norm_pointer, 4) == norm and
                         read(world_pointer, 68) == world and
                         read(component + 0x70, 0x40) == comp and
                         read(instance, 3) == header and
                         read(brain + 0x1e4, 12) == filtered and
                         read(input_pointer, 12) == raw_input and
                         read(glob(0x1420a3318), 4) == delta)
            rows.append(dict(index=len(rows), elapsed=tick, unchanged=unchanged,
                state_hex=state.hex(), direction_hex=direction.hex(), gate_hex=gate.hex(),
                norm_hex=norm.hex(), world_hex=world.hex(), component_hex=comp.hex(),
                header_hex=header.hex(), flags_hex=flags.hex(), delta_hex=delta.hex(),
                filtered_hex=filtered.hex(), raw_input_hex=raw_input.hex()))
            last = signature
        if ptr(glob(0x142157ec8)) != actor:
            raise ValueError('Actor changed during observation')
except Exception as exc:
    error = repr(exc)
finally:
    k.CloseHandle(h)
    path = Path('reports/jade') / ('stage43-speed-order-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
    path.write_text(json.dumps(dict(pid=a.pid, module_base=hex(a.base), rows=rows,
        iterations=iterations, error=error, limitations=[
            'Sequential reads; unchanged brackets do not prove atomic callback state.',
            'Changed rows retained; elapsed is observer wall time.']), indent=2) + '\n')
    print(json.dumps(dict(report=str(path), rows=len(rows), iterations=iterations, error=error)))
if error:
    raise RuntimeError(error)
