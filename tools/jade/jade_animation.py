"""Ordinary PC track reader grounded in 140b442c0/140b43db0/140b49120.

Exports local samples only: time units, rig parents and interpolation remain unknown.
Unsupported transform encodings fail explicitly instead of shifting the cursor.
"""
import math
import struct


def packed_quaternion_float32(packed):
    """140b49120 explicit XYZ decode; float32 operations before double sqrt."""
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    x, y, z = [f32(value/32767.0) for value in packed]
    norm = f32(f32(f32(y*y) + f32(x*x)) + f32(z*z))
    w = f32(math.sqrt(f32(1.0-norm))) if norm < 1.0 else 0.0
    return [x, y, z, w]


class UnsupportedAnimation(ValueError):
    pass


class Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError(f'Truncated animation at {self.pos}, need {size}')
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def unpack(self, fmt):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))


def transform(c, compression, first, previous):
    start = c.pos
    effective = (0x100 if compression & 0x2000 else 0) if first else compression
    if effective & 0x2000:
        if previous is None:
            raise ValueError('Missing shared transform header')
        size = previous['declared_size']
    else:
        size, = c.unpack('<H')
    if effective & 0x1000:
        if previous is None:
            raise ValueError('Missing shared transform flags')
        flags = previous['flags']
    else:
        flags, = c.unpack('<H')
    result = {'declared_size': size, 'flags': flags}
    rotation = flags & 0x780
    vector = flags & 0xF800
    if rotation:
        if flags & 0x80:
            packed = c.unpack('<3h')
            q = packed_quaternion_float32(packed)
            result.update(quaternion_xyzw=q, packed_rotation=list(packed))
        else:
            # Four source bytes; native code adds signed deltas to previous quaternion.
            # Previous sign canonicalisation requires assembly verification.
            result['rotation_delta_hex'] = c.take(4).hex()
            result['pose_unresolved'] = 'Previous quaternion sign/quantisation not verified'
    elif vector:
        if vector in (0x800, 0x1000):
            xyz = c.unpack('<3h')
        elif vector == 0x2000:
            xyz = c.unpack('<hbb')
        elif vector == 0x4000:
            y, x, z = c.unpack('<hbb')
            xyz = (x, y, z)
        elif vector == 0x8000:
            z, x, y = c.unpack('<hbb')
            xyz = (x, y, z)
        else:
            raise UnsupportedAnimation(f'Vector mask {vector:04X}')
        result['vector_xyz'] = [v / 1024.0 for v in xyz]
    else:
        mode = flags & 3
        if mode:
            result['float3_channels'] = [list(c.unpack('<3f')) for _ in range(mode)]
        elif flags & 0x14 == 0x10:
            result['quaternion_xyzw'] = list(c.unpack('<4f'))
        elif flags & 0x14:
            raise UnsupportedAnimation('Matrix transform reader 140aeb350 pending')
        if flags & 8:
            raise UnsupportedAnimation('Variable float tail pending')
    result['source_hex'] = c.data[start:c.pos].hex()
    return result


def decode_animation(data):
    c = Cursor(data)
    count, flags = c.unpack('<HH')
    tracks = []
    for index in range(count):
        start = c.pos
        source_flags, short1, aux_count = c.unpack('<HHI')
        compression = source_flags & 0x3F00
        track = {'index': index, 'source_flags': source_flags,
                 'short1': short1, 'aux_count': aux_count}
        if not source_flags & 0x8000:
            key, = c.unpack('<I')
            track['gao_key'] = f'{key:08X}'
            c.take(16)  # Native ordinary branch advances by 28 total bytes.
        elif not compression:
            link, = c.unpack('<I')
            track['link_u32'] = link
        track['prefix_hex'] = data[start:c.pos].hex()
        n, = c.unpack('<I')
        if n > 65535:
            raise UnsupportedAnimation('Native count truncation not emulated')
        track['count_hex'] = struct.pack('<I', n).hex()
        frames, previous, first_flags = [], None, None
        for frame_index in range(n):
            frame_start = c.pos
            tick, = c.unpack('<B' if compression & 0x200 else '<H')
            if not compression & 0x800 or frame_index == 0:
                frame_flags, = c.unpack('<H')
                if frame_index == 0:
                    first_flags = frame_flags
            else:
                frame_flags = first_flags & 0xFFFB
            runtime_flags = frame_flags & 0xFFFD
            frame = {'index': frame_index, 'tick_raw': tick, 'flags': frame_flags}
            kind = runtime_flags & 0x7C0
            if kind == 0x40:
                num, = c.unpack('<I')
                frame['aux_records_hex'] = c.take(num * 8).hex()
            elif kind == 0x80:
                if runtime_flags & 0x20:
                    frame['reference_u32'], = c.unpack('<I')
                else:
                    previous = transform(c, compression, frame_index == 0, previous)
                    frame['transform'] = previous
            frame['source_hex'] = data[frame_start:c.pos].hex()
            frames.append(frame)
        track['frames'] = frames
        tracks.append(track)
    return {'schema': 'jade-animation-local-samples-v1', 'flags': flags,
            'tracks': tracks, 'opaque_tail_hex': data[c.pos:].hex(),
            'consumed_bytes': c.pos,
            'limits': 'Local samples; delta quaternion poses unresolved; no rig hierarchy, '
                      'time units, channel semantics or interpolation established.'}


def encode_animation(animation):
    """Rebuild source segments, preserving all unknown data and float bit patterns."""
    out = bytearray(struct.pack('<HH', len(animation['tracks']), animation['flags']))
    for track in animation['tracks']:
        out.extend(bytes.fromhex(track['prefix_hex']))
        out.extend(bytes.fromhex(track['count_hex']))
        for frame in track['frames']:
            out.extend(bytes.fromhex(frame['source_hex']))
    out.extend(bytes.fromhex(animation['opaque_tail_hex']))
    return bytes(out)
