"""Readonly short observation of temporary actor/root reference refresh scope.

Requires a fresh sequence from the same process; no game input or hooks.
Marker equality is a sequential-read guard, never an atomic callback proof.
"""
import argparse
import ctypes
import datetime
import hashlib
import json
import struct
import time
from ctypes import wintypes
from pathlib import Path
from project_paths import report_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sequence', type=Path)
    parser.add_argument('--start-delay', type=float, default=3)
    args = parser.parse_args()
    if not 0 <= args.start_delay <= 10:
        raise ValueError('Start delay must be 0..10 seconds')
    source = args.sequence.read_bytes()
    previous = json.loads(source)
    sample = previous['samples'][-1]
    actor = int(sample['actor']['address'], 16)
    reference = int(sample['actor_reference_address'], 16)
    base = int(previous['module_base'], 16)
    if reference < 0x10000 or int(sample['actor']['flags'], 16) & 0x400000:
        raise ValueError('Existing direct actor reference required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.ReadProcessMemory.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1010, False, previous['pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        if address < 0x10000 or not 0 < size <= 128:
            raise ValueError('Bounded read required')
        buffer = ctypes.create_string_buffer(size)
        count = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(count)) or count.value != size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw

    def pointer(address):
        return struct.unpack('<Q', read(address, 8))[0]

    def global_address(address):
        return base + address - 0x140000000

    def markers():
        return (read(global_address(0x1419a1480), 4),
                read(global_address(0x14193f708), 4),
                read(global_address(0x1420c3448), 56),
                read(global_address(0x1420a3318), 4),
                read(global_address(0x1419a02bc), 4),
                read(global_address(0x1420d6618), 16))

    try:
        if pointer(global_address(0x142157ec8)) != actor:
            raise ValueError('Actor changed; capture a fresh sequence')
        original_world = pointer(actor + 0x10)
        flags = struct.unpack('<I', read(actor + 4, 4))[0]
        if not flags & 0x4000000 or flags & 0x400000:
            raise ValueError('Existing direct actor reference required')
        if original_world + (0x88 if flags & 0x10000 else 0x44) != reference:
            raise ValueError('Reference storage changed; capture a fresh sequence')
        time.sleep(args.start_delay)
        rows, last = [], None
        started = time.perf_counter()
        iterations = 0
        while time.perf_counter() - started < 3 and iterations < 100000 and len(rows) < 4096:
            tick = time.perf_counter() - started
            before = markers()
            world_pointer = pointer(actor + 0x10)
            world_raw = read(world_pointer, 68)
            reference_raw = read(reference, 68)
            original_raw = read(original_world, 68)
            reference_after = read(reference, 68)
            original_after = read(original_world, 68)
            pointer_after = pointer(actor + 0x10)
            after = markers()
            key = (before, after, world_pointer, pointer_after, world_raw, reference_raw, original_raw,
                   reference_after, original_after)
            if key != last:
                context = struct.unpack('<7Q', before[2])
                gate = struct.unpack('<I', before[1])[0]
                candidate = (before == after and world_pointer == pointer_after and gate == 0
                             and context[0] == actor and context[5] == global_address(0x14195aee0)
                             and before[3] == b'\x00' * 4)
                rows.append(dict(elapsed_seconds=tick,
                    markers_before_hex=[v.hex() for v in before],
                    markers_after_hex=[v.hex() for v in after],
                    markers_unchanged=before == after, refresh_scope_candidate=candidate,
                    actor_world_pointer=hex(world_pointer), actor_world_pointer_after=hex(pointer_after),
                    temporary_world_pointer=world_pointer != original_world,
                    current_actor_matrix_hex=world_raw.hex(), reference_matrix_hex=reference_raw.hex(),
                    original_actor_matrix_hex=original_raw.hex(),
                    reference_matrix_after_hex=reference_after.hex(),
                    reference_matrix_unchanged=reference_raw == reference_after,
                    original_actor_matrix_after_hex=original_after.hex(),
                    original_actor_matrix_unchanged=original_raw == original_after))
                last = key
            iterations += 1
        elapsed = time.perf_counter() - started
        termination = ('observation_limit' if len(rows) >= 4096 else
                       'iteration_limit' if iterations >= 100000 else 'duration_limit')
        output = report_path('stage43-reference-order-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
        result = dict(read_only=True, source_sequence=str(args.sequence),
            source_sha256=hashlib.sha256(source).hexdigest(), pid=previous['pid'], module_base=hex(base),
            actor_address=hex(actor), original_world_address=hex(original_world), reference_address=hex(reference),
            marker_layout=['update_pass_u32', 'entry_gate_u32', 'animation_context_7q', 'delta_f32',
                           'vm_pass_u32', 'vm_actor_context_2q'],
            iterations=iterations, rows=rows, requested_seconds=3, elapsed_seconds=elapsed,
            termination=termination,
            limitations=['Sequential reads can miss or straddle writes; candidate markers are not causal proof.',
                         'A temporary matrix pointer can have other causes; raw values are retained.',
                         'Reference allocation or actor replacement requires a new source sequence.'])
        output.write_text(json.dumps(result, indent=2))
        print(json.dumps(dict(report=str(output), observations=len(rows),
            scope_candidates=sum(r['refresh_scope_candidate'] for r in rows),
            temporary_pointer_observations=sum(r['temporary_world_pointer'] for r in rows))))
    finally:
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    main()
