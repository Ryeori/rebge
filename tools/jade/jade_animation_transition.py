"""Restricted forward transition clock from native 1409bcd20.

Returns the downstream ratio, not an inferred incoming/outgoing blend weight.
No pose blending, clip execution or root-motion side effects are implemented.
"""
import math
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def blend_root_position(before_transition, after_transition, ratio):
    """15358c6f0 ordinary position branch, excluding movement callbacks.

    The saved primary position gains weight as ratio increases. This does
    not establish how each bone rotation is blended by other functions.
    """
    if len(before_transition) != 3 or len(after_transition) != 3:
        raise ValueError('Expected two XYZ positions')
    if not all(math.isfinite(v) for v in (*before_transition, *after_transition, ratio)):
        raise ValueError('Finite positions and ratio required')
    weight = min(max(f32(ratio), 0.0), 1.0)
    complement = f32(1.0 - weight)
    return [f32(f32(complement * f32(new)) + f32(f32(old) * weight))
            for old, new in zip(before_transition, after_transition)]


def advance_transition(*, active, duration_byte, elapsed_u16, delta_seconds,
                       saved_delta_seconds=None):
    if not 0 <= duration_byte <= 255 or not 0 <= elapsed_u16 <= 65535:
        raise ValueError('Native byte/ushort bounds required')
    delta = delta_seconds if saved_delta_seconds is None else saved_delta_seconds
    if not math.isfinite(delta) or delta < 0:
        raise ValueError('Only finite forward transitions supported')
    if not active:
        return {'active': False, 'elapsed_u16': elapsed_u16,
                'downstream_ratio': None, 'evaluate_transition': False}
    duration = f32(f32(duration_byte + 1) / f32(60))
    elapsed = f32(f32(f32(elapsed_u16) / f32(15360)) + f32(delta))
    if duration <= elapsed:
        # Native clears the active bit without rewriting the counter or ratio.
        return {'active': False, 'elapsed_u16': elapsed_u16,
                'downstream_ratio': None, 'evaluate_transition': False}
    counter = int(f32(elapsed * f32(15360))) & 0xffff
    return {'active': True, 'elapsed_u16': counter,
            'downstream_ratio': f32(elapsed / duration),
            'evaluate_transition': True}
