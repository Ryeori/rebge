"""No-scale linked-to-actor translation branch140b49fb0.

Reference/actor matrices and component height must be observed writer inputs.
"""
from jade_animation_transition import f32
from jade_tracking_local import inverse_no_scale
from jade_target_hierarchy import raw_affine_product


def refresh_reference(root_matrix,root_flags,saved_actor_matrix,saved_actor_flags):
    """1409c0850 final product: saved actor * inverse evaluated root.

    Caller supplies the temporary root pose and saved actor matrix from the
    refresh operation. A final world snapshot is not automatically that input.
    Scaled root or actor matrices are explicitly unsupported.
    """
    inverse,flags=inverse_no_scale(root_matrix,root_flags)
    return raw_affine_product(inverse,saved_actor_matrix,flags,saved_actor_flags)


def actor_reference_position(position,reference,reference_flags,actor_matrix,
                             actor_matrix_flags,*,height=0,add_height=False):
    inverse,flags=inverse_no_scale(actor_matrix,actor_matrix_flags)
    relative,_=raw_affine_product(reference,inverse,reference_flags,flags)
    p=list(map(f32,position));result=[]
    for row in range(3):
        order=(0,1,2) if row==0 else (1,0,2)
        terms=[f32(p[k]*relative[k*4+row]) for k in order]
        value=f32(f32(terms[0]+terms[1])+terms[2])
        result.append(f32(value+relative[12+row]))
    if add_height:result[2]=f32(result[2]+f32(height))
    return result
