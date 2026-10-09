"""Root-channel conversion with explicit runtime reference context."""
from jade_pose import affine_product, rotation_matrix
import math


def translation_reference_gate(runtime_tracks, current_index, current_actor, default_actor):
    """140b48240 inclusive scan of explicit runtime actor/current-frame entries."""
    if not 0 <= current_index < len(runtime_tracks):
        raise ValueError('Invalid current runtime track index')
    for track in runtime_tracks[:current_index+1]:
        actor = track['actor'] if track['actor'] is not None else default_actor
        flags = track.get('current_frame_flags')
        if actor == current_actor and flags is not None and flags & 0x7C0 == 0x80 and flags & 4:
            return True
    return False


def rigid_inverse(matrix):
    """1409c0850 transposed basis and transformed negative position; no scale."""
    if len(matrix) != 16 or not all(math.isfinite(x) for x in matrix):
        raise ValueError('Expected finite matrix')
    for i in range(3):
        for j in range(3):
            dot = sum(matrix[i*4+k]*matrix[j*4+k] for k in range(3))
            if abs(dot-(1 if i == j else 0)) > 1e-5:
                raise ValueError('Rigid inverse requires orthonormal basis')
    inverse = rotation_matrix([0, 0, 0, 1])
    for c in range(3):
        for r in range(3):
            inverse[c*4+r] = matrix[r*4+c]
    for r in range(3):
        inverse[12+r] = -sum(inverse[c*4+r]*matrix[12+c] for c in range(3))
    return inverse


def refresh_root_reference(current_actor_matrix, evaluated_root_matrix, *, root_flags):
    """1409c0850 ->140ae9c00: current_actor * inverse(evaluated_root).

    evaluated_root must be the native zero-delta evaluation at its current track
    state, including its explicit initial reference. This function does not guess
    that state, reset time to zero, or emulate action blending.
    """
    if root_flags & 8:
        raise ValueError('Native scale-bit8 reference refresh unsupported')
    return affine_product(rigid_inverse(evaluated_root_matrix), current_actor_matrix)


def reference_matrix_offset(gao_flags):
    """140b28360: pointer relative to GAO matrix block, absent without bit26."""
    if not gao_flags & 0x4000000:
        return None
    return 0x88 if gao_flags & 0x10000 else 0x44


def convert_root_channels(sample, reference_matrix, *, reference_flags,
                          translation_reference_enabled):
    """140ae9870 rotation +140ae9fb0 position; no native scale bit8 branch.

    translation_reference_enabled must come from runtime140b48240 scan. Rotation
    composition is independent of that condition. Output contains channel writes
    only; it does not invent actor position or root-parent relationships.
    """
    if sample['slot'] != 65535:
        raise ValueError('Expected actor root slot')
    if reference_matrix is None or len(reference_matrix) != 16:
        raise ValueError('Explicit 16-entry runtime reference matrix required')
    if reference_flags & 8:
        raise ValueError('Native scale-bit8 root conversion unsupported')
    result = {'slot': 65535, 'track_index': sample['track_index']}
    if 'quaternion_xyzw' in sample:
        local = rotation_matrix(sample['quaternion_xyzw'])
        if reference_flags & 0x3C:
            matrix = affine_product(local, reference_matrix)
        else:
            matrix = local
        result['rotation_basis'] = [matrix[c*4+r] for c in range(3) for r in range(3)]
    if 'position_xyz' in sample:
        p = sample['position_xyz']
        result['position_xyz'] = ([sum(reference_matrix[c*4+r]*p[c] for c in range(3))
                                   + reference_matrix[12+r] for r in range(3)]
                                  if translation_reference_enabled else list(p))
    return result
