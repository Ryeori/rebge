"""Fail-closed trace qualification; no inferred consecutive native frames."""
PRIMARY_CHECKS=('primary_states_unchanged','primary_link_unchanged',
    'primary_resource_unchanged','primary_instance_unchanged',
    'component_prefix_unchanged','update_pass_unchanged',
    'brain_unchanged','target_reference_unchanged','primary_header_unchanged')


def rejection_reasons(sample):
    reasons=[key+(':missing' if key not in sample else ':changed')
             for key in PRIMARY_CHECKS if sample.get(key) is not True]
    if 'pose_matrices_unchanged' in sample and sample['pose_matrices_unchanged'] is not True:
        reasons.append('pose_matrices_unchanged:changed')
    for check in ('primary_phase_descriptor_unchanged','actor_dispatch_prefix_unchanged',
                  'reference_entry_manager_unchanged'):
        if check in sample and sample[check] is not True:
            reasons.append(check+':changed')
    active=sample['component_flags_u16']>>8&15
    if active not in (1,3):reasons.append('unsupported_active_slots')
    if active==3:
        checks=sample.get('transition_consistency',{})
        for key in ('states_unchanged','link_unchanged','resource_unchanged',
                    'instance_header_unchanged','instance_pointer_unchanged'):
            if checks.get(key) is not True:reasons.append('transition_'+key)
    return reasons


def pair_candidate(first,second):
    reasons=rejection_reasons(first)+rejection_reasons(second)
    if first['actor']['address']!=second['actor']['address']:reasons.append('actor_changed')
    if (second.get('update_pass_before',0)-first.get('update_pass_after',0))&0xffffffff!=1:
        reasons.append('not_adjacent_update_passes')
    if first.get('target_resolved_address')!=second.get('target_resolved_address'):
        reasons.append('target_changed')
    return dict(candidate=not reasons,reasons=sorted(set(reasons)),native_prior_input_proven=False)
