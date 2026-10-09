"""Parameter initialization in 1409b3b20; no inferred final clamp order.

Names retain decompiler locals until their complete consumer flow is proven.
Optional secondary limits are None when parameter10 is disabled: native
uninitialized scratch values are never invented.
"""
import math

from jade_animation_transition import f32


def tracking_limits(mode, *, secondary=False, overrides=None, unrestricted=False):
    if not isinstance(mode, int) or not 0 <= mode <= 0x03ffffff:
        raise ValueError('Expected decoded native mode')
    a45 = f32(0.7853981852531433)
    a60 = f32(1.0471975803375244)
    a90 = f32(1.5707963705062866)
    a120 = f32(2.094395160675049)
    values = {'fStack_278': a45, 'fStack_254': f32(0.4363323152065277),
              'fVar36': -a45, 'fVar26': 0.0,
              'fVar35': -a90, 'fVar29': a90, 'fVar37': -a45,
              'fStack_26c': -a45 if secondary else None,
              'fStack_270': a45 if secondary else None}
    if mode == 0:
        values.update(fStack_278=a60, fVar35=-a120, fVar29=a120, fVar37=-a60)
        if secondary:
            values.update(fStack_26c=-a60, fStack_270=a60)
    elif mode == 1:
        values['fVar26'] = f32(0.5235987901687622)
    elif mode == 2:
        values.update(fVar26=f32(0.6108652949333191),
                      fStack_254=f32(0.12217305600643158))
    elif mode == 3:
        values['fVar26'] = f32(0.37088245153427124)
    addresses = {'1421015ac': 'fVar29', '1421015b4': 'fVar35',
                 '1421015a0': 'fStack_254', '14210159c': 'fVar36',
                 '1421015a4': 'fStack_278', '1421015b0': 'fVar37',
                 '1421015a8': 'fVar26'}
    for address, value in (overrides or {}).items():
        if address not in addresses or not math.isfinite(value):
            raise ValueError('Expected known finite override')
        value = f32(value)
        if value != 1000.0:
            values[addresses[address]] = value
    values['fStack_254'] = f32(values['fStack_254'] + values['fVar26'])
    values['fVar36'] = f32(values['fVar36'] + values['fVar26'])
    if unrestricted:
        pi = f32(3.1415927410125732)
        for name in ('fStack_278', 'fStack_254', 'fVar29'):
            values[name] = pi
        for name in ('fVar36', 'fVar35', 'fVar37'):
            values[name] = -pi
    return values
