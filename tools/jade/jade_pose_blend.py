"""Numerical quaternion stage of140aed7b0/140aed150.

Inputs are already extracted quaternions, not arbitrary matrices. Host sin/acos
and normalization are numerical substitutes, not native transcendental parity.
"""
import math
import struct
from jade_animation_transition import f32
from jade_matrix_quaternion import normalize_quaternion

NEAR_IDENTICAL = struct.unpack('<f', bytes.fromhex('feff7f3f'))[0]


def blend_rotation(first, second, weight):
    if len(first) != 4 or len(second) != 4:
        raise ValueError('Expected xyzw quaternions')
    a, b = [list(map(f32, q)) for q in (first, second)]
    if not all(math.isfinite(v) for v in a+b+[weight]):
        raise ValueError('Finite inputs required')
    dot = f32(f32(f32(a[0]*b[0])+f32(a[1]*b[1]))+f32(a[2]*b[2]))
    dot = f32(dot+f32(a[3]*b[3]))
    if dot < 0:
        dot = -dot
        b = [-v for v in b]
    # Native helper copies the first operand when angle is zero; no nlerp.
    if abs(dot) >= NEAR_IDENTICAL:
        return a
    angle = f32(math.acos(dot))
    reciprocal = f32(1/f32(math.sqrt(f32(1-f32(dot*dot)))))
    t = f32(weight)  # rotation consumer does not clamp this parameter
    left = f32(f32(math.sin(f32(f32(1-t)*angle)))*reciprocal)
    right = f32(f32(math.sin(f32(t*angle)))*reciprocal)
    result = [f32(f32(x*left)+f32(y*right)) for x,y in zip(a,b)]
    return normalize_quaternion(result)
