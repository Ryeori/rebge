"""Restricted140b33020 hierarchy and140ae9c00 no-scale matrix product.

The affine consumer reads raw basis/translation even when flags2/4 are clear.
No-scale product is kept separate from skin flag-selected preprocessing.
"""
import math

from jade_animation_transition import f32


IDENTITY = [1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]


def raw_affine_product(local, parent, local_flags=0, parent_flags=0):
    """parent*local, rounding each MULSS/ADDSS, excluding scale flag8."""
    if local_flags & 8 or parent_flags & 8:
        raise NotImplementedError('Native scale decomposition not implemented')
    if any(len(m) != 16 or not all(math.isfinite(v) for v in m)
           for m in (local, parent)):
        raise ValueError('Expected finite native matrices')
    local, parent = list(map(f32, local)), list(map(f32, parent))
    result = IDENTITY.copy()
    for column in (0, 4, 8, 12):
        for row in range(3):
            terms = [f32(local[column+k]*parent[k*4+row]) for k in range(3)]
            value = f32(f32(terms[0]+terms[1])+terms[2])
            result[column+row] = f32(value+parent[12+row]) if column == 12 else value
    flags = (local_flags | parent_flags) & 4
    if any(v != 0 for v in result[12:15]):
        flags |= 2
    return result, flags


def linked_target_position(nodes, actor_address, *, max_depth=64):
    """Evaluate captured nodes, following native linked parent/local ordering.

    nodes use integer addresses, flags, world_matrix/world_flags and optional
    parent_address/local_matrix/local_flags. Missing capture nodes are errors;
    an explicitly absent parent follows native fallback to original world.
    """
    if actor_address == 0:
        return {'position': [0.,0.,0.], 'path': [], 'branch': 'null'}
    if not 0 < max_depth <= 512:
        raise ValueError('Invalid traversal bound')
    original = actor_address
    current, path, seen = original, [], set()
    while True:
        if current in seen or len(seen) >= max_depth:
            raise ValueError('Cyclic or overlong target hierarchy')
        seen.add(current)
        if current not in nodes:
            raise ValueError('Missing captured hierarchy node')
        node = nodes[current]
        if not node['flags'] & 1:
            root, branch = current, 'direct' if not path else 'linked'
            break
        parent = node.get('parent_address')
        if parent is None:
            raise ValueError('Unknown captured parent')
        if parent == 0:
            #140b330e3 chooses original actor, not last visited ancestor.
            root, path, branch = original, [], 'missing_parent_fallback'
            break
        path.append(current)
        current = parent
    if not path:
        return {'position': list(nodes[root]['world_matrix'][12:15]),
                'path': [hex(root)], 'branch': branch}
    accumulated, flags = IDENTITY.copy(), 0
    for address in path:
        node = nodes[address]
        if not node['flags'] & 0x400000:
            raise NotImplementedError('Native absent local-matrix pointer branch')
        accumulated, flags = raw_affine_product(
            accumulated, node['local_matrix'], flags, node['local_flags'])
    matrix, _ = raw_affine_product(accumulated, nodes[root]['world_matrix'],
                                   flags, nodes[root]['world_flags'])
    return {'position': matrix[12:15], 'path': [hex(a) for a in (*path, root)],
            'branch': branch}


def snapshot_target_nodes(snapshot):
    actor = snapshot['actor']
    nodes = {int(actor['address'],16): dict(flags=int(actor['flags'],16),
              world_matrix=list(actor['world_matrix'][:16]),
              world_flags=actor['world_matrix'][16])}
    for obj in snapshot['objects']:
        if 'matrix' not in obj:
            continue
        node = dict(flags=int(obj['flags'],16), world_matrix=obj['matrix'],
                    world_flags=obj['matrix_flags'])
        if 'linked_parent_address' in obj:
            node.update(parent_address=int(obj['linked_parent_address'],16),
                        local_matrix=obj['linked_local_matrix'],
                        local_flags=obj['linked_local_matrix_flags'])
        nodes[int(obj['address'],16)] = node
    return nodes
