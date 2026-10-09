"""Basis update in 140aec970, with trigonometric coefficients supplied.

Separating coefficients avoids claiming parity with the game's math library.
Matrix storage is native column-major; only Y/Z basis XYZ entries change.
"""
import math

from jade_animation_transition import f32


def rotate_yz_basis(matrix, flags, cosine, sine):
    if len(matrix) != 16 or not all(math.isfinite(v) for v in
                                   (*matrix, cosine, sine)):
        raise ValueError('Expected finite 16-component matrix and coefficients')
    result = list(matrix)
    c, s = f32(cosine), f32(sine)
    for row in range(3):
        y, z = f32(matrix[4 + row]), f32(matrix[8 + row])
        result[4 + row] = f32(f32(z * s) + f32(y * c))
        result[8 + row] = f32(f32(z * c) - f32(y * s))
    return result, flags | 4


def rotate_world_xy(matrix, flags, cosine, sine):
    """154bffba0: rotate each basis column in world XY, preserving its Z.

    Listing verifies separate MULSS then ADDSS/SUBSS; no fused operations.
    Coefficients remain explicit until native trigonometry is recovered.
    """
    if len(matrix) != 16 or not all(math.isfinite(v) for v in
                                   (*matrix, cosine, sine)):
        raise ValueError('Expected finite 16-component matrix and coefficients')
    result = list(matrix)
    c, s = f32(cosine), f32(sine)
    for column in (0, 4, 8):
        x, y = f32(matrix[column]), f32(matrix[column + 1])
        result[column] = f32(f32(x * c) - f32(y * s))
        result[column + 1] = f32(f32(x * s) + f32(y * c))
    return result, flags | 4
