"""140aed9a0/1400369e0 ordinary finite basis normalization.

Only basis XYZ entries are written. Native degenerate zero vectors remain
zero; flags/scale metadata require the caller's separate handling.
"""
import math

from jade_animation_transition import f32


def normalize_vector(vector):
    if len(vector) != 3 or not all(math.isfinite(v) for v in vector):
        raise ValueError('Expected finite XYZ')
    x, y, z = (f32(v) for v in vector)
    squared = f32(f32(f32(x*x) + f32(y*y)) + f32(z*z))
    if not math.isfinite(squared):
        raise ValueError('Vector length exceeds supported finite arithmetic')
    if squared <= 0:
        return [x, y, z]
    length = f32(math.sqrt(squared))
    reciprocal = f32(1.0 / length)
    return [f32(v * reciprocal) for v in (x, y, z)]


def cross(first, second):
    return [f32(f32(first[1]*second[2]) - f32(first[2]*second[1])),
            f32(f32(first[2]*second[0]) - f32(first[0]*second[2])),
            f32(f32(first[0]*second[1]) - f32(first[1]*second[0]))]


def normalize_basis(matrix):
    if len(matrix) != 16 or not all(math.isfinite(v) for v in matrix):
        raise ValueError('Expected finite native 16-component matrix')
    result = list(matrix)
    x = normalize_vector(matrix[:3])
    z = [f32(v) for v in matrix[8:11]]
    y = normalize_vector(cross(z, x))
    z = normalize_vector(cross(x, y))
    result[:3], result[4:7], result[8:11] = x, y, z
    return result
