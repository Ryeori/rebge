"""Role0 desired-angle branch of1409b3b20 from resolved writer inputs.

Caller supplies pre-correction rebuilt world, resolved target and phase decision.
This does not resolve VM targets or infer prior pose from final output.
"""
import math
import struct
from jade_animation_transition import f32
from jade_basis_normalize import normalize_vector
from jade_tracking_angles import yaw_difference,pitch_difference

TARGET_YAW_MARGIN=struct.unpack('<f',bytes.fromhex('c3b8323e'))[0]


def role0_desired(reference,rebuilt_world,target,*,phase_blocked,
                  reject_outside_yaw,limits,sign_axis):
    if len(target)!=3 or not all(math.isfinite(v) for v in target):
        raise ValueError('Finite resolved target XYZ required')
    fallback=normalize_vector([-v for v in rebuilt_world[4:7]])
    def angles(direction):
        return yaw_difference(reference,direction,sign_axis),pitch_difference(reference,direction)
    if phase_blocked or not any(target):
        yaw,pitch=angles(fallback)
        return dict(yaw=yaw,pitch=pitch,branch='rebuilt_forward',direction=fallback)
    direction=normalize_vector([f32(a-b) for a,b in zip(target,rebuilt_world[12:15])])
    yaw,pitch=angles(direction)
    upper=f32(limits['fVar29']+TARGET_YAW_MARGIN)
    lower=f32(limits['fVar35']-TARGET_YAW_MARGIN)
    if reject_outside_yaw and (upper<yaw or yaw<lower):
        yaw,pitch=angles(fallback)
        return dict(yaw=yaw,pitch=pitch,branch='target_outside_yaw_fallback',direction=fallback)
    return dict(yaw=yaw,pitch=f32(pitch+limits['fVar26']),branch='resolved_target',direction=direction)


def secondary_desired(role0_result,rebuilt_role1_yaw,rebuilt_role12_yaw=None,
                      *,parameter7=False,parameter8=False,current_role1_yaw=None):
    """Native yaw distribution after desired target/fallback decision."""
    target_branch=role0_result['branch']=='resolved_target'
    if not target_branch:
        role1=rebuilt_role1_yaw
    elif parameter7:
        role1=role0_result['yaw']
    elif parameter8:
        # 1409b4452 saves current yaw in XMM8; 1409b44ac..44c2
        # retains it when parameter8 is set. Rebuilt yaw is the fallback.
        if current_role1_yaw is None:
            raise ValueError('Parameter8 requires explicit prior role1 yaw')
        role1=current_role1_yaw
    else:
        role1=f32(role0_result['yaw']/3)
    role12=(None if rebuilt_role12_yaw is None else
            f32(role0_result['yaw']/5) if target_branch else rebuilt_role12_yaw)
    return {'role1_yaw':f32(role1),'role12_yaw':role12}
