"""Tracking gate 1409b3c55..1409b3e11, excluding pointer/phase resolution."""
import math

from jade_animation_transition import f32


def tracking_phase_gate(counter, strength, delta_time, *, current_flags=None,
                        component_high_byte=1, transition_flags=None,
                        phase_control=0):
    """None flags means missing/out-of-range phase, not flags zero.

    Prerequisite actor/component/role checks happen before this native block.
    Returns whether execution may continue into angle calculation. No pose
    writes or transition phase lookups are performed here.
    """
    if not isinstance(counter, int) or not 0 <= counter <= 255:
        raise ValueError('Expected byte counter')
    if not 0 <= phase_control <= 65535:
        raise ValueError('Expected phase control word')
    if not all(math.isfinite(v) for v in (strength, delta_time)) or delta_time < 0:
        raise ValueError('Expected finite strength and nonnegative delta')
    blocked = False
    if current_flags is not None:
        blocked = not bool(current_flags & 4)
        if component_high_byte != 1:
            blocked = (transition_flags is not None and
                       (blocked or not bool(transition_flags & 4)))
    if not blocked:
        return {'counter': 0, 'strength': f32(strength), 'continue': True}
    if phase_control & 0x8000:
        if counter >= 16:
            return {'counter': 16, 'strength': f32(strength), 'continue': False}
        increment = math.trunc(f32(f32(f32(delta_time) / f32(0.01666666567325592)) + 0.5))
        if increment > 0x7fffffff:
            raise ValueError('Delta outside supported CVTTSS2SI range')
        counter = (counter + increment) & 255
        return {'counter': counter, 'strength': f32(counter * 0.0625),
                'continue': counter < 16}
    if phase_control & 0x1000:
        return {'counter': counter, 'strength': f32(strength), 'continue': False}
    if counter >= 6:
        return {'counter': 6, 'strength': f32(strength), 'continue': False}
    counter += 1
    return {'counter': counter, 'strength': f32(0.4), 'continue': counter < 6}
