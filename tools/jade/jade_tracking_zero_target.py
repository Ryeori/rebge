"""Compatibility entry point for the explicitly zero-target writer branch."""
from jade_tracking_step import tracking_step


def zero_target_step(nodes,actor_address,role_addresses,previous_world,
                     continuity_address,*,strength,limits,sign_axis,
                     allow_limit_crossing,scale_references,coefficients):
    return tracking_step(nodes,actor_address,role_addresses,previous_world,
        continuity_address,strength=strength,limits=limits,sign_axis=sign_axis,
        allow_limit_crossing=allow_limit_crossing,scale_references=scale_references,
        coefficients=coefficients,target=(0,0,0))
