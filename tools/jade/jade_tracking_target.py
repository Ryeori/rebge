"""Read-only target primitives from 1400bf6a0 and 140b33020.

Linked/local actors (flag 1) require hierarchy evaluation and are rejected.
These helpers do not choose the target or alter VM storage.
"""
import struct


def variable_storage(read, encoded, context, *, max_descriptors=65536):
    """Return VM value storage address, not the value stored there.

    Descriptor table has no verified count in this structure: caller must
    supply a validated max_descriptors when working with narrower tables.
    """
    if not isinstance(encoded, int) or not 0 <= encoded <= 0xffffffff:
        raise ValueError('Expected unsigned encoded variable')
    index, element = encoded >> 16, encoded & 0xffff
    if not 0 <= index < max_descriptors <= 65536 or context < 0x10000:
        raise ValueError('Descriptor index/context outside bounds')
    table, _, storage = struct.unpack('<QQQ', read(context, 24))
    if table < 0x10000 or storage < 0x10000:
        raise ValueError('Absent descriptor table or value storage')
    descriptor = read(table + index * 12, 12)
    offset = struct.unpack_from('<I', descriptor)[0]
    kind = struct.unpack_from('<h', descriptor, 8)[0]
    stride = 8 if kind in (0x27, 0x28, 0x2b, 0x2f) else 64 if kind == 0x29 else 0
    return storage + offset + element * stride


def resolve_actor_reference(value, special_references):
    """Caller expands references 1/2 through PTR_DAT_14193f710."""
    if not isinstance(value, int) or not 0 <= value <= 0xffffffffffffffff:
        raise ValueError('Expected unsigned native reference')
    if len(special_references) != 2:
        raise ValueError('Expected native two-entry reference table')
    return special_references[value - 1] if value in (1, 2) else value


def direct_target_position(read, actor):
    """Native null and world-matrix branches only; no guessed linked pose."""
    if actor == 0:
        return (0.0, 0.0, 0.0)
    if actor < 0x10000:
        raise ValueError('Resolve special actor references first')
    flags = struct.unpack('<I', read(actor + 4, 4))[0]
    if flags & 1:
        raise NotImplementedError('Linked actor target requires hierarchy evaluation')
    matrix = struct.unpack('<Q', read(actor + 0x10, 8))[0]
    if matrix < 0x10000:
        raise ValueError('Absent world matrix')
    return struct.unpack('<3f', read(matrix + 0x30, 12))
