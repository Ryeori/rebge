"""Native clone attach and world assembly using explicit attachment matrices."""
from jade_pose import affine_product
from copy import deepcopy


def initialize_source_clones(objects):
    """Loader bit16 copies source GAO matrix to+44; attach copies+44 to local.

    Source-state reconstruction only; prior live updates/clone position overrides
    are excluded. Missing extra-block source cases fail explicitly.
    """
    clones = deepcopy(objects)
    keys = {obj['key'] for obj in clones}
    for obj in clones:
        flags = int(obj['flags'], 16)
        parent = obj.get('linked_gao')
        if parent not in keys:
            if not flags & 0x10000:
                raise ValueError('Extra matrix initialization requires explicit runtime position')
            obj['linked_matrix'] = list(obj['gao_matrix'])
            obj['linked_matrix_flags'] = 6
            obj['linked_gao'] = None
        obj['flags'] = f'{flags | 0x400000:08X}'
    return clones


def assemble_sampled_clone_world(snapshot):
    """After attachment initialization AND channel application; roots use actor."""
    actor = snapshot['actor_destination_matrix']
    if actor is None:
        raise ValueError('Evaluated actor matrix required')
    rows = {obj['key']: obj for obj in snapshot['objects']}
    if len(rows) != len(snapshot['objects']):
        raise ValueError('Duplicate clone key')
    world, active = {}, set()
    def visit(key):
        if key in active:
            raise ValueError('Clone parent cycle')
        if key in world:
            return world[key]
        active.add(key)
        row = rows[key]
        parent = row['clone_parent']
        if parent is not None and parent not in rows:
            raise ValueError('Missing clone parent')
        world[key] = affine_product(row['jade_destination_matrix'], actor if parent is None else visit(parent))
        active.remove(key)
        return world[key]
    for key in rows:
        visit(key)
    return world


def assemble_attached_clone_base_world(snapshot, attachment_matrices):
    """153219c00 attach roots;1409b4e70 parent*local composition, no scale.

    attachment_matrices supplies evaluated GAO matrixblock+44 values for entries
    whose remapped parent is null. Actor destination must already be evaluated.
    A caller may supply diagnostic matrices, but must label that context.
    """
    actor = snapshot['actor_destination_matrix']
    if actor is None:
        raise ValueError('Evaluated actor matrix required')
    rows = snapshot['objects']
    by_key = {row['key']: row for row in rows}
    if len(by_key) != len(rows):
        raise ValueError('Duplicate clone key')
    world, active = {}, set()
    def visit(key):
        if key in active:
            raise ValueError('Clone parent cycle')
        if key in world:
            return world[key]
        active.add(key)
        row = by_key[key]
        parent = row['clone_parent']
        if parent is None:
            if key not in attachment_matrices:
                raise ValueError(f'Missing attachment matrix for {key}')
            local = attachment_matrices[key]
            parent_matrix = actor
        else:
            if parent not in by_key:
                raise ValueError(f'Missing clone parent {parent}')
            local = row['jade_destination_matrix']
            parent_matrix = visit(parent)
        # Animation channels must be applied AFTER attachment initialization.
        # Thus this function is a base attached-pose builder, not playback.
        world[key] = affine_product(local, parent_matrix)
        active.remove(key)
        return world[key]
    for key in by_key:
        visit(key)
    return world
