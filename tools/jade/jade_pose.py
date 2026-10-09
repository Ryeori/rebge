"""Bounded native pose operations recovered from Jade consumers."""

import math
import struct


def interpolate_rotation(first, second, fraction):
    """140aecfd0/140aed150: shortest arc, near-equal hold, then normalize.

    Mathematical reconstruction, not bit-exact SSE/libm emulation. Does not
    mutate the caller's second quaternion (the native routine mutates scratch).
    """
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Interpolation fraction outside segment')
    a, b = list(first), list(second)
    if len(a) != 4 or len(b) != 4 or not all(math.isfinite(x) for x in a+b):
        raise ValueError('Expected finite xyzw quaternions')
    if not sum(x*x for x in a) or not sum(x*x for x in b):
        raise ValueError('Zero quaternion')
    dot = sum(x*y for x, y in zip(a, b))
    if dot < 0:
        dot, b = -dot, [-x for x in b]
    dot = min(1.0, dot)
    # Bytes 95 bf d6 33 at 14173c1f0; no guessed epsilon or linear fallback.
    epsilon = struct.unpack('<f', bytes.fromhex('95bfd633'))[0]
    if abs(dot-1.0) <= epsilon:
        return a
    angle = math.acos(dot)
    inverse_sine = 1/math.sqrt(1-dot*dot)
    wa = math.sin((1-fraction)*angle)*inverse_sine
    wb = math.sin(fraction*angle)*inverse_sine
    result = [wa*x+wb*y for x, y in zip(a, b)]
    length = math.sqrt(sum(x*x for x in result))
    if not length:
        raise ValueError('Degenerate interpolated quaternion')
    return [x/length for x in result]


def rotation_matrix(q):
    """140aed650 flattened columns (same layout as observed GAO matrices)."""
    x, y, z, w = q
    return [1-2*(y*y+z*z), 2*(x*y+z*w), 2*(x*z-y*w), 0,
            2*(x*y-z*w), 1-2*(x*x+z*z), 2*(y*z+x*w), 0,
            2*(x*z+y*w), 2*(y*z-x*w), 1-2*(x*x+y*y), 0,
            0, 0, 0, 1]


def rotation_samples(animation, object_keys):
    tracks = []
    for track in animation['tracks']:
        slot = track['short1']
        samples = []
        for frame in track['frames']:
            transform = frame.get('transform', {})
            if 'quaternion_xyzw' not in transform:
                continue
            q = list(transform['quaternion_xyzw'])
            # 140b486d0 and 140b482f0 flip Y/Z quaternion signs for frame flag20.
            if frame['flags'] & 0x20:
                q[1], q[2] = -q[1], -q[2]
            x, y, z, w = q
            samples.append({'frame_index': frame['index'],
                            'duration_ticks_raw': frame['tick_raw'],
                            'native_duration_divided_by_60': frame['tick_raw']/60.0,
                            'jade_quaternion_xyzw': q,
                            'jade_rotation_matrix': rotation_matrix(q),
                            'bevy_quaternion_xyzw': [x, z, -y, w],
                            'bevy_rotation_matrix': rotation_matrix([x, z, -y, w])})
        if samples:
            tracks.append({'track_index': track['index'], 'native_slot': slot,
                           'candidate_gao': object_keys[slot] if slot < len(object_keys) else None,
                           'native_slot_is_actor_root': slot == 65535,
                           'samples': samples})
    return {'schema': 'jade-local-rotation-poses-v1', 'tracks': tracks,
            'limits': 'Rotation samples only. GAO mapping is a candidate list binding; '
                      'parent hierarchy, translation application, full pose assembly, '
                      'skinning and native interpolation are not implemented.'}


def translation_sample(frame):
    """First float3 is position: accessor140b4ae30 + consumer140b49fb0."""
    channels = frame.get('transform', {}).get('float3_channels', [])
    if not channels:
        return None
    points = [list(point) for point in channels]
    if frame['flags'] & 0x20:
        if len(points) != 1:
            raise ValueError('Mirrored curve control-point handling needs assembly verification')
        points[0][0] = -points[0][0]
    return points


def interpolate_translation(points, next_position, fraction):
    """140b49fb0 linear/quadratic/cubic branches; input fraction in [0,1]."""
    if not 0 <= fraction <= 1:
        raise ValueError('Interpolation fraction outside segment')
    n = len(points)
    if n not in (1, 2, 3):
        raise ValueError('Unsupported position channel count')
    t, s = fraction, 1-fraction
    weights = ((s, t) if n == 1 else
               (s*s, 2*t*s, t*t) if n == 2 else
               (s*s*s, 3*t*s*s, 3*t*t*s, t*t*t))
    controls = points + [next_position]
    return [sum(weight*point[axis] for weight, point in zip(weights, controls))
            for axis in range(3)]


def validate_link_graph(objects):
    """Validate the native bit22 linked-parent chain; external roots stay explicit."""
    by_key = {obj['key']: obj for obj in objects}
    if len(by_key) != len(objects):
        raise ValueError('Duplicate GAO key')
    depths = {}
    def visit(key, active):
        if key in active:
            raise ValueError(f'Linked GAO cycle at {key}')
        if key in depths:
            return depths[key]
        parent = by_key[key].get('linked_gao')
        depths[key] = (1 + visit(parent, active | {key}) if parent in by_key else 0)
        return depths[key]
    for key in by_key:
        visit(key, set())
    return depths


def affine_product(local, parent):
    """140ae9420: flat column-major result = parent * local; no scale flags."""
    if len(local) != 16 or len(parent) != 16:
        raise ValueError('Expected 16 matrix entries')
    out = [0.0] * 16
    for column in range(3):
        for row in range(3):
            out[column*4+row] = sum(parent[k*4+row]*local[column*4+k] for k in range(3))
    for row in range(3):
        out[12+row] = sum(parent[k*4+row]*local[12+k] for k in range(3)) + parent[12+row]
    out[15] = 1.0
    return out


def assemble_rest_pose(objects):
    """1409b4e70 ancestor order for observed matrices without native scale bit8."""
    validate_link_graph(objects)
    by_key = {obj['key']: obj for obj in objects}
    matrices = {}
    def visit(key):
        if key in matrices:
            return matrices[key]
        obj = by_key[key]
        parent = obj.get('linked_gao')
        if parent and parent not in ('00000000', 'FFFFFFFF'):
            if parent not in by_key:
                raise ValueError(f'Missing parent {parent}')
            if obj['linked_matrix_flags'] & 8:
                raise ValueError('Native scale bit8 composition not implemented')
            matrix = affine_product(obj['linked_matrix'], visit(parent))
        else:
            matrix = list(obj['gao_matrix'])
        matrices[key] = matrix
        return matrix
    for key in by_key:
        visit(key)
    return matrices
