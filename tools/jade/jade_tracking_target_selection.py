"""Finite-input target branches in140e02760 with resolved references.

Caller supplies phase/blocked-target decisions and role0 position; this
function models offset updates but never mutates game memory.
"""
import math

from jade_animation_transition import f32


def select_tracking_target(tracking_word, offset, actor_position, *,
                           target_enabled, target_is_self, role0_position=None):
    if not isinstance(tracking_word, int) or not 0 <= tracking_word <= 0xffffffff:
        raise ValueError('Expected native tracking word')
    vectors = (offset, actor_position) + (() if role0_position is None else (role0_position,))
    if any(len(v) != 3 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Expected finite XYZ inputs')
    word, offset = tracking_word, list(map(f32, offset))
    if not target_enabled:
        return {'target': [0.0]*3, 'tracking_word': word & ~0x10000,
                'offset_after': offset, 'branch': 'zero_target'}
    position = list(map(f32, actor_position))
    branch = 'actor_position'
    if word & 0x10000:
        word &= ~0x10000
        if role0_position is not None:
            # Native14173cf38 floatbits461c4000 =10000; z uses <= branch.
            if offset[2] <= 10000.0:
                position = list(map(f32, role0_position))
                position[2] = f32(position[2]+0.25)  #14173c4f8
                if not target_is_self:
                    offset = [0.0]*3
                branch = 'role0_position'
            else:
                offset[2] = f32(offset[2]-10000.0)
                branch = 'offset_z_sentinel'
    return {'target': [f32(x+y) for x, y in zip(position, offset)],
            'tracking_word': word, 'offset_after': offset, 'branch': branch}
