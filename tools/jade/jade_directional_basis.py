"""Restricted 140aec520 directional basis; near-parallel fallback excluded."""
import math
import struct

from jade_animation_transition import f32
from jade_basis_normalize import cross, normalize_vector


def directional_basis(matrix, flags, direction, up=None):
    """Preserve translation/metadata; native reset-byte branch unsupported.

    Native ADD 80000000 toggles float sign bits, not numeric integer values.
    Supplied-up branch uses the original (not normalized) direction in cross.
    """
    if len(matrix) != 16 or not all(math.isfinite(v) for v in matrix):
        raise ValueError('Expected finite native matrix')
    d = list(direction)
    unit = normalize_vector(d)
    if not any(unit):
        raise ValueError('Zero direction has undefined native division')
    y = [-v for v in unit]
    if up is None:
        x = cross(matrix[8:11], y)
    else:
        u = normalize_vector(up)
        if not any(u):
            raise ValueError('Zero up has undefined native division')
        # Preserve pre-sign-flip native subtraction order.
        raw = cross(d, u)
        threshold = struct.unpack('<f', bytes.fromhex('60708930'))[0]
        if all(abs(v) < threshold for v in raw):
            raise NotImplementedError('Native near-parallel up perturbation not implemented')
        x = [-v for v in raw]
    x = normalize_vector(x)
    z = cross(x, y)
    result = list(matrix)
    result[:3], result[4:7], result[8:11] = x, y, z
    return result, flags | 4
