"""Verified argument packing at Sally eye-follow callsites 140e02b2f/bd7.

Does not resolve target handles, evaluate phase gates or run the tracking writer.
Flag parameters retain native integer masks; their meanings remain unresolved.
"""
import math

from jade_animation_transition import f32


def tracking_arguments(base_word, tracking_word, strength, delta_time,
                       strength_multiplier, *, target_enabled):
    """Pack arguments 3..10, given the already resolved caller branch.

    Native caller ADDs words, rather than ORing them. Bit 16 is cleared in
    the zero-target branch; enabled-target special handling must be resolved
    before this function. Finite inputs exclude SSE NaN operand semantics.
    """
    if not all(isinstance(v, int) and 0 <= v <= 0xffffffff
               for v in (base_word, tracking_word)):
        raise ValueError('Expected unsigned 32-bit caller words')
    if not all(math.isfinite(v) for v in
               (strength, delta_time, strength_multiplier)):
        raise ValueError('Finite strength inputs required')
    value = f32(strength)
    if value < 1.0:
        factor = f32(f32(delta_time) * f32(strength_multiplier))
        value = f32(value * factor)
    word = tracking_word if target_enabled else tracking_word & ~0x10000
    combined = (word + base_word) & 0xffffffff
    return {
        'strength': min(max(value, 0.0), 1.0),
        'mode': combined & 0x03ffffff,
        'parameter_5': combined & 0x80000000,
        'parameter_6': combined & 0x40000000,
        'parameter_7': combined & 0x20000000,
        'parameter_8': combined & 0x10000000,
        'parameter_9': combined & 0x08000000,
        'parameter_10': combined & 0x04000000,
    }
