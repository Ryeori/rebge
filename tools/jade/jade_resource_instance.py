"""Verified resource instance selection/clamp branches; no backend playback."""
import struct


def select_actor_resource(actor, local_index, *, enabled, resource_count):
    """140afa260 ordinary actor-bound index indirection, excluding debug mode."""
    if not enabled:
        return -1
    if actor is not None:
        if not actor['flags'] & 0x8000000:
            return -1
        mapping = actor.get('resource_indices')
        if mapping is None or not 0 <= local_index < len(mapping):
            return -1
        local_index = mapping[local_index]
    return local_index if 0 <= local_index < resource_count else -1


def clamp_instance_parameter(value):
    """154f63710: below native epsilon ->0, otherwise min(value,1)."""
    epsilon = struct.unpack('<f', bytes.fromhex('95bfd633'))[0]
    return min(value, 1.0) if value >= epsilon else 0.0
