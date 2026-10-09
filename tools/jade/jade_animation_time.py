"""Restricted native140b272a0 forward transform-track timing, without events."""
import math


def locate_transform_segment(track, elapsed_seconds, *, loop=False):
    if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
        raise ValueError('Only finite forward time supported')
    frames = track['frames']
    if not frames:
        raise ValueError('Empty track')
    if any((frame['flags'] & 0x7C0) != 0x80 for frame in frames):
        raise ValueError('Event/jump track timing not implemented')
    durations = [frame['tick_raw']/60.0 for frame in frames]
    total = sum(durations)
    remaining = elapsed_seconds
    # Native uses <= at each boundary: exact boundary stays on outgoing key.
    if loop and remaining > total:
        if total == 0:
            raise ValueError('Zero-duration loop cannot advance')
        cycles = math.ceil(remaining/total)-1
        remaining -= cycles*total
    for index, duration in enumerate(durations):
        if remaining <= duration:
            return {'frame_index': index, 'next_frame_index': (index+1) % len(frames),
                    'segment_seconds': remaining,
                    'fraction': remaining/duration if duration else 0.0,
                    'clamped_terminal': False}
        remaining -= duration
    # Explicit hold policy, matching native terminal hold/root branch only.
    return {'frame_index': len(frames)-1, 'next_frame_index': 0,
            'segment_seconds': durations[-1], 'fraction': 1.0 if durations[-1] else 0.0,
            'clamped_terminal': True}
