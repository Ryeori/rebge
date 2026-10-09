"""Restricted resolved-target writer1409b3b20 with explicit prior world state.

No target resolution, phase gate, scaled matrices or near-horizontal role1
fallback. Native transcendental parity depends on caller's coefficients;
yaw/pitch helpers still use host acos, so this is a numerical reconstruction.
"""
from copy import deepcopy

from jade_animation_transition import f32
from jade_basis_normalize import normalize_vector
from jade_directional_basis import directional_basis
from jade_tracking_angles import yaw_difference,pitch_difference
from jade_tracking_correction import tracking_corrections
from jade_tracking_local import compose_tracking_world,recover_tracking_local
from jade_tracking_rotation import rotate_world_xy,rotate_yz_basis
from jade_tracking_desired import role0_desired,secondary_desired


def tracking_step(nodes,actor_address,role_addresses,previous_world,
                     continuity_address,*,strength,limits,sign_axis,
                     allow_limit_crossing,scale_references,coefficients,
                     target=(0,0,0),phase_blocked=False,
                     parameter7=False,parameter8=False):
    """Update copied local nodes; prior matrices must precede this correction.

    previous_world maps native addresses to (matrix,flags). Passing a final
    corrected snapshot here does not establish an oracle for native output.
    coefficient callback takes radians and returns (cosine,sine).
    """
    if set(role_addresses) not in ({0,1},{0,1,12}):
        raise ValueError('Expected resolved native roles0/1 and optional12')
    result=deepcopy(nodes)
    reference=[-v for v in nodes[actor_address]['world_matrix'][4:7]]
    forward=lambda matrix: [-v for v in matrix[4:7]]
    rebuilt={role:compose_tracking_world(nodes,address)[0]
             for role,address in role_addresses.items()}
    current={role:list(previous_world[address][0])
             for role,address in role_addresses.items()}
    current_flags={role:previous_world[address][1]
                   for role,address in role_addresses.items()}
    if any(flags&8 for flags in current_flags.values()):
        raise NotImplementedError('Scaled previous world basis')
    role1_z=normalize_vector(current[1][8:11])
    if abs(role1_z[2]) < f32(0.05):
        raise NotImplementedError('Native near-horizontal role1 fallback')
    rebuilt_continuity=compose_tracking_world(nodes,continuity_address)[0]
    previous_yaw=yaw_difference(forward(previous_world[continuity_address][0]),
                                forward(rebuilt_continuity),sign_axis)
    yaw=lambda matrix:yaw_difference(reference,forward(matrix),sign_axis)
    pitch=lambda matrix:pitch_difference(reference,forward(matrix))
    desired=role0_desired(reference,rebuilt[0],target,phase_blocked=phase_blocked,
        reject_outside_yaw=allow_limit_crossing,limits=limits,sign_axis=sign_axis)
    secondary=secondary_desired(desired,yaw(rebuilt[1]),
        yaw(rebuilt[12]) if 12 in rebuilt else None,
        parameter7=parameter7,parameter8=parameter8,current_role1_yaw=yaw(current[1]))
    args=dict(desired_yaw=desired['yaw'],current_yaw=yaw(current[0]),
              desired_pitch=desired['pitch'],current_pitch=pitch(current[0]),
              role1_desired=secondary['role1_yaw'],role1_current=yaw(current[1]),
              strength=strength,previous_yaw=previous_yaw,limits=limits,
              allow_limit_crossing=allow_limit_crossing)
    if 12 in role_addresses:
        args.update(role12_desired=secondary['role12_yaw'],role12_current=yaw(current[12]))
    deltas=tracking_corrections(**args)
    applied={}
    for role in role_addresses:
        matrix,flags=current[role],current_flags[role]
        yaw_delta=deltas[f'role{role}_yaw']
        if abs(yaw_delta)>=f32(1e-5):
            c,s=coefficients(yaw_delta)
            matrix,flags=rotate_world_xy(matrix,flags,c,s)
        # Role0 pitch is weighted/clamped. Secondary pitch restores the
        # rebuilt-current difference unconditionally, per XMM1 call listing.
        pitch_delta=(deltas['role0_pitch'] if role==0 else
                     f32(pitch(rebuilt[role])-pitch(current[role])))
        if role!=0 or abs(pitch_delta)>=f32(1e-5):
            c,s=coefficients(pitch_delta)
            matrix,flags=rotate_yz_basis(matrix,flags,c,s)
        matrix,flags=directional_basis(matrix,flags,forward(matrix),rebuilt[role][8:11])
        applied[role]=(matrix,flags)
    # Native restores secondary12 first, then1, then0. Rebuild parents after
    # each local write: roles may be ancestors of later corrected roles.
    for role in (12,1,0):
        if role not in role_addresses:
            continue
        address=role_addresses[role]
        node=result[address]
        if not node['flags']&0x400000 or not node.get('parent_address'):
            raise NotImplementedError('Expected linked role with a known parent')
        if node['local_flags']&8:
            raise NotImplementedError('Scaled original local basis')
        parent,parent_flags=compose_tracking_world(result,node['parent_address'])
        matrix,flags=recover_tracking_local(*applied[role],parent,parent_flags,
            nodes[address]['local_matrix'][12:15],saved_scale=[1.,1.,1.],
            reference_scales=scale_references)
        node.update(local_matrix=matrix,local_flags=flags)
    return {'nodes':result,'scalar_corrections':deltas,'previous_yaw':previous_yaw,
            'desired':desired,'secondary_desired':secondary,
            'limits':['Prior world state is supplied, not inferred from final pose.',
                      'Finite no-scale resolved-target branch; native acos parity unproven.']}
