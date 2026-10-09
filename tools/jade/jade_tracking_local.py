"""Restricted tracking matrix recovery1409b4e70/1409b59d0/140aea110.

No-scale branch only. Parent basis is transposed exactly as native code does;
this is not a general inverse for arbitrary sheared/non-orthogonal matrices.
"""
import math
import struct

from jade_animation_transition import f32
from jade_basis_normalize import normalize_basis
from jade_target_hierarchy import IDENTITY, raw_affine_product


def inverse_no_scale(matrix, flags):
    if flags & 8:
        raise NotImplementedError('Native scaled parent inverse not implemented')
    if len(matrix)!=16 or not all(math.isfinite(v) for v in matrix):
        raise ValueError('Expected finite native matrix')
    result=IDENTITY.copy()
    for column in range(3):
        for row in range(3):
            result[column*4+row]=f32(matrix[row*4+column])
    negative=[-f32(v) for v in matrix[12:15]]
    for row in range(3):
        terms=[f32(result[k*4+row]*negative[k]) for k in range(3)]
        result[12+row]=f32(f32(terms[0]+terms[1])+terms[2])
    return result,flags


def compose_tracking_world(nodes,address,*,max_depth=64):
    """1409b4e70 follows object bit400000, rather than target bit1."""
    if not 0<max_depth<=512:
        raise ValueError('Invalid hierarchy bound')
    path,seen=[],set()
    current=address
    while True:
        if current in seen or len(seen)>=max_depth or current not in nodes:
            raise ValueError('Cyclic, overlong or incomplete world hierarchy')
        seen.add(current)
        node=nodes[current]
        if not node['flags']&0x400000:
            break
        parent=node.get('parent_address')
        if parent is None:
            raise ValueError('Unknown captured parent')
        if parent==0:
            break
        path.append(current)
        current=parent
    if not path:
        return list(nodes[current]['world_matrix']),nodes[current]['world_flags']
    matrix,flags=IDENTITY.copy(),0
    for child in path:
        matrix,flags=raw_affine_product(matrix,nodes[child]['local_matrix'],
                                       flags,nodes[child]['local_flags'])
    return raw_affine_product(matrix,nodes[current]['world_matrix'],
                              flags,nodes[current]['world_flags'])


def restore_scale(matrix, flags, saved_scale, reference_scales):
    """140aea6e0, with actual native reference vectors supplied by caller.

    Initializer uses (1,1,1)/(0,0,0); another writer exists, so no hidden
    defaults are used. This restores metadata; it does not scale the basis.
    """
    vectors=(saved_scale,*reference_scales)
    if len(matrix)!=16 or len(reference_scales)!=2 or any(
            len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Expected matrix, saved XYZ scale and two references')
    epsilon=struct.unpack('<f',bytes.fromhex('17b7d138'))[0]
    saved=list(map(f32,saved_scale))
    equivalent=any(all(abs(f32(f32(r)-s))<=epsilon for r,s in zip(ref,saved))
                   for ref in reference_scales)
    result=list(matrix)
    if equivalent:
        result[3]=result[7]=result[11]=0.0
        flags &= ~8
    else:
        result[3],result[7],result[11]=saved
        flags |= 8
    return result,flags


def recover_tracking_local(world,world_flags,parent_world,parent_flags,
                           saved_position,*,saved_scale,reference_scales):
    """No-scale1409b59d0 normalization + caller position/scale restoration."""
    if len(saved_position)!=3 or not all(math.isfinite(v) for v in saved_position):
        raise ValueError('Expected saved native local XYZ')
    inverse,flags=inverse_no_scale(parent_world,parent_flags)
    local,flags=raw_affine_product(world,inverse,world_flags,flags)
    local=normalize_basis(local)
    local,flags=restore_scale(local,flags,saved_scale,reference_scales)
    local[12:15]=list(saved_position)
    return local,flags
