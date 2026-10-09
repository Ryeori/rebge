"""Static eligibility gates recovered from native local/palette pass consumers.

These predicates select candidates; they do not claim a path ran in a snapshot.
"""


def local_callback_candidate(address,actor_flags,update_flags,indexed_present):
    """1409adf00/1409ce910 local pass filter."""
    return (address!=0 and address&3!=1 and not update_flags&4
            and bool(actor_flags&2) and indexed_present)


def palette_initial_callback(component_flags,primary_present):
    """1409ce4e0 initial evaluation+callback3, preceding palette publication."""
    return component_flags&0xff==0 and primary_present
