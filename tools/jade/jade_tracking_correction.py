"""Verified scalar blend/clamp blocks 1409b4700..1409b47e1.

Includes finite-input crossing/continuity branches 1409b45c8..1409b47e1.
Role selection, target distribution, and matrix application are external.
"""
import math
import struct

from jade_animation_transition import f32

LIMIT_EPSILON = struct.unpack('<f', bytes.fromhex('6f12833a'))[0]


def continuity_allowed(desired, current, strength, previous):
    """Native bVar19, verified at 1409b45c8..1409b45fe."""
    if not all(math.isfinite(v) for v in (desired, current, strength, previous)):
        raise ValueError('Expected finite native angle inputs')
    desired, current, strength, previous = map(f32,
                                             (desired, current, strength, previous))
    return strength != 1.0 and (
        previous == 0.0 or ((desired <= current or previous >= 0.0)
                           and (current <= desired or previous <= 0.0)))


def tracking_corrections(*, desired_yaw, current_yaw, desired_pitch,
                         current_pitch, role1_desired, role1_current,
                         strength, previous_yaw, limits, allow_limit_crossing,
                         role12_desired=None, role12_current=None):
    """Scalar output of native tracking with already resolved role angles.

    Optional role12 requires initialized secondary limits. This function does
    not infer a target, callback context, role angles, or bone matrices.
    """
    required = ('fVar35', 'fVar29', 'fVar36', 'fStack_254',
                'fVar37', 'fStack_278')
    values = (desired_yaw, current_yaw, desired_pitch, current_pitch,
              role1_desired, role1_current, strength, previous_yaw)
    if not all(math.isfinite(v) for v in (*values, *(limits[k] for k in required))):
        raise ValueError('Expected finite native angle inputs and limits')
    dy, cy, dp, cp, d1, c1, weight, previous = map(f32, values)
    lower, upper = f32(limits['fVar35']), f32(limits['fVar29'])
    secondary = role12_desired is not None or role12_current is not None
    if secondary and (role12_desired is None or role12_current is None
                      or limits.get('fStack_26c') is None
                      or limits.get('fStack_270') is None):
        raise ValueError('Role12 requires both angles and initialized limits')
    if secondary and not all(math.isfinite(v) for v in
                             (role12_desired, role12_current,
                              limits['fStack_26c'], limits['fStack_270'])):
        raise ValueError('Expected finite role12 inputs')
    continuity = continuity_allowed(dy, cy, weight, previous)
    blocked = not allow_limit_crossing and (
        (abs(f32(cy-upper)) < LIMIT_EPSILON and dy < lower)
        or (abs(f32(cy-lower)) < LIMIT_EPSILON and dy > upper))
    if blocked:
        return dict(role0_yaw=0.0, role0_pitch=0.0, role1_yaw=0.0,
                    role12_yaw=0.0 if secondary else None,
                    continuity=continuity, branch='opposite_limit')
    crossed = ((dy > 0.0 and cy < dy < f32(cy+previous))
               or (dy < 0.0 and f32(cy+previous) < dy < cy))
    accumulation = previous if continuity else 0.0
    yaw = f32(dy-cy) if crossed else blended_angle_correction(
        dy, cy, weight, lower, upper, accumulation)
    pitch = blended_angle_correction(dp, cp, weight,
                                     limits['fVar36'], limits['fStack_254'])
    yaw1 = blended_angle_correction(d1, c1, weight,
                                    limits['fVar37'], limits['fStack_278'],
                                    accumulation)
    yaw12 = None if not secondary else blended_angle_correction(
        role12_desired, role12_current, weight,
        limits['fStack_26c'], limits['fStack_270'], accumulation)
    return dict(role0_yaw=yaw, role0_pitch=pitch, role1_yaw=yaw1,
                role12_yaw=yaw12, continuity=continuity,
                branch='previous_crossing' if crossed else 'blend')


def blended_angle_correction(desired, current, strength, lower, upper,
                             accumulated=0.0):
    """Return delta, clamping current+delta with native upper-first branches.

    accumulated is the previously evaluated correction when the native
    continuity predicate allows it; otherwise caller must supply zero.
    No wrap or implicit shortest-arc conversion occurs in this block.
    """
    inputs = (desired, current, strength, lower, upper, accumulated)
    if not all(math.isfinite(v) for v in inputs):
        raise ValueError('Expected finite native angle inputs')
    desired, current, strength, lower, upper, accumulated = map(f32, inputs)
    delta = f32(f32(f32(f32(desired-current) - 0.0) * strength) + 0.0)
    delta = f32(delta + accumulated)
    result = f32(delta + current)
    if result > upper:
        return f32(upper-current)
    if result < lower:
        return f32(lower-current)
    return delta
