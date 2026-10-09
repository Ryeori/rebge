"""Restricted parent-first linked-world pass1409ac510.

Requires explicit object+0x33 visitation bytes and list order. This pass reads
the locals present when invoked, not locals subsequently written by animation.
It does not model the other callbacks between world and local pose passes.
"""
from copy import deepcopy
from jade_target_hierarchy import raw_affine_product


def linked_world_pass(nodes,addresses,pass_counter):
    result=deepcopy(nodes);parity=pass_counter&1;writes=[];index=0
    def eligible(address):
        if address not in result:raise ValueError('Missing world-pass node')
        return (result[address]['visitation_byte_33']>>7&1)==parity
    while index<len(addresses):
        address=addresses[index]
        if not address or address&3==1:
            index+=1;continue
        if not eligible(address):
            index+=1;continue
        current=address;seen=set()
        while True:
            if current in seen:raise ValueError('Cyclic world-pass hierarchy')
            seen.add(current)
            parent=result[current].get('parent_address')
            if parent is None:raise ValueError('Unknown linked parent presence')
            if not parent or not eligible(parent):break
            current=parent
        node=result[current]
        node['visitation_byte_33']=(node['visitation_byte_33']&127)|((1-parity)<<7)
        if node['flags']&0x400000 and node['parent_address']:
            parent=result[node['parent_address']]
            matrix,flags=raw_affine_product(node['local_matrix'],parent['world_matrix'],
                                           node['local_flags'],parent['world_flags'])
            node.update(world_matrix=matrix,world_flags=flags)
            writes.append(current)
        # The native iterator repeats its current entry after updating an ancestor.
        if current==address:index+=1
    return dict(nodes=result,writes=writes,next_pass_counter=(pass_counter+1)&0xffffffff)
