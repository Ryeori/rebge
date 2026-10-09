"""Audit sampled input lifetime across ordinary and corrected publications.

An unchanged window is necessary evidence, not proof of callback entry.
Changed windows remain diagnostic measurements and cannot validate a writer.
"""


def window_input_rejections(ordinary, corrected, repeated):
    reasons=[]
    for name,row in (('ordinary',ordinary),('corrected',corrected),('repeated',repeated)):
        for field in ('primary_clip_unchanged','tracking_inputs_unchanged'):
            if row.get(field) is not True:reasons.append(f'{name}:{field}')
        if 'actor_world_unchanged' in row and row['actor_world_unchanged'] is not True:
            reasons.append(f'{name}:actor_world_unchanged')
    for field in ('delta_time','brain_604_61f_hex','target_reference',
                  'primary_states_hex','component_flags_u16','actor_flags',
                  'actor_reference_matrix_hex','component_height_b4',
                  'current_phase_flags','current_phase_control','sign_axis','strength_multiplier'):
        if field in ordinary and any(row.get(field)!=ordinary[field] for row in (corrected,repeated)):
            reasons.append(field+':changed')
    if any(row['matrices']['actor_world']!=ordinary['matrices']['actor_world']
           for row in (corrected,repeated)):
        reasons.append('actor_world:changed')
    return reasons
