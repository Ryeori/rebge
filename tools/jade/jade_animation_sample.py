"""Timed local channel updates; excludes actor/world conversion and event VM."""
from jade_animation_time import locate_transform_segment
from jade_pose import interpolate_rotation, interpolate_translation, translation_sample, rotation_matrix
from jade_animation_root import convert_root_channels


def _rotation(frame):
    value = frame.get('transform', {}).get('quaternion_xyzw')
    if value is None:
        return None
    value = list(value)
    if frame['flags'] & 0x20:
        value[1], value[2] = -value[1], -value[2]
    return value


def sample_local_track(track, elapsed_seconds, *, loop=False):
    """140b49ba0/140b49fb0 ordinary channel branch with explicit time policy.

    Returns channel writes, not an absolute actor/world pose. Unsupported time
    remapping and alternate endpoints fail rather than fabricate a transform.
    """
    segment = locate_transform_segment(track, elapsed_seconds, loop=loop)
    frame = track['frames'][segment['frame_index']]
    following = track['frames'][segment['next_frame_index']]
    transform = frame.get('transform', {})
    if transform.get('flags', 0) & (8 | 0x40):
        raise ValueError('Transform time remapping/alternate endpoint unsupported')
    result = {'slot': track['short1'], 'track_index': track['index'], **segment}
    q, next_q = _rotation(frame), _rotation(following)
    if q is not None:
        # General consumer140b482f0 holds current for missing next/no-interpolation.
        result['quaternion_xyzw'] = (q if frame['tick_raw'] == 0 or next_q is None or frame['flags'] & 0x800 else
                                    next_q if segment['fraction'] >= 1 else
                                    interpolate_rotation(q, next_q, segment['fraction']))
    points = translation_sample(frame)
    if points:
        next_points = translation_sample(following)
        # Translation has an explicit no-interpolation flag and missing-channel hold.
        if not next_points or frame['tick_raw'] == 0 or frame['flags'] & 0x800:
            result['position_xyz'] = points[0]
        else:
            result['position_xyz'] = interpolate_translation(points, next_points[0], segment['fraction'])
    return result


def sample_clone_local_matrices(animation, objects, elapsed_seconds, *, root_context=None):
    """Apply ordinary channel writes in track order to seeded clone matrices.

    This is a local destination snapshot, not world assembly. Actor/root writes
    and dynamic parent switching need runtime context and are rejected explicitly.
    """
    mapping = clone_parent_mapping(objects)
    matrices = {}
    for obj, mapped in zip(objects, mapping):
        field = 'linked_matrix' if mapped['destination'] == 'linked_local_matrix' else 'gao_matrix'
        matrices[obj['key']] = list(obj[field])
    applied, unsupported = [], []
    actor_matrix = list(root_context['actor_matrix']) if root_context is not None else None
    for track in animation['tracks']:
        try:
            sample = sample_local_track(track, elapsed_seconds)
            slot = sample['slot']
            if slot == 65535:
                if root_context is None:
                    raise ValueError('Actor root conversion needs runtime reference matrix')
                converted = convert_root_channels(sample, root_context['reference_matrix'],
                    reference_flags=root_context['reference_flags'],
                    translation_reference_enabled=root_context['translation_gates'][track['index']])
                if 'rotation_basis' in converted:
                    for column in range(3):
                        actor_matrix[column*4:column*4+3] = converted['rotation_basis'][column*3:column*3+3]
                if 'position_xyz' in converted:
                    actor_matrix[12:15] = converted['position_xyz']
                applied.append(track['index'])
                continue
            if not 0 <= slot < len(objects):
                raise ValueError('Invalid indexed object slot')
            frame = track['frames'][sample['frame_index']]
            if frame.get('transform', {}).get('flags', 0) & 0x20:
                raise ValueError('Dynamic parent switching/rebase needs runtime context')
            matrix = matrices[objects[slot]['key']]
            if 'quaternion_xyzw' in sample:
                rotation = rotation_matrix(sample['quaternion_xyzw'])
                for column in range(3):
                    matrix[column*4:column*4+3] = rotation[column*4:column*4+3]
            if 'position_xyz' in sample:
                matrix[12:15] = sample['position_xyz']
            applied.append(track['index'])
        except ValueError as error:
            unsupported.append({'track_index': track['index'], 'reason': str(error)})
    return {'objects': [{**mapped, 'jade_destination_matrix': matrices[mapped['key']]}
                        for mapped in mapping], 'applied_tracks': applied,
            'unsupported_tracks': unsupported, 'complete_local_snapshot': not unsupported,
            'actor_destination_matrix': actor_matrix}


def clone_parent_mapping(objects):
    """153602b50: retain parents within indexed list; clear external pointers.

    Only resource GAO keys are accepted. Native pointer sentinels1/2 are not GAO
    resource keys and require a separate runtime representation.
    """
    keys = {obj['key'] for obj in objects}
    if len(keys) != len(objects):
        raise ValueError('Duplicate clone source key')
    return [{'key': obj['key'], 'source_parent': obj.get('linked_gao'),
             'clone_parent': obj.get('linked_gao') if obj.get('linked_gao') in keys else None,
             'destination': 'linked_local_matrix' if int(obj['flags'], 16) & 0x400000
                            else 'gao_matrix'} for obj in objects]
