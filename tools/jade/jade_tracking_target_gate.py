"""Resolved-target filtering in140e02760; no memory writes."""


def tracking_target_gate(resolved_target, blocked_targets, phase_flags):
    """Native blocked table compares entries directly to the resolved target.

    Blocking clears VM target storage. Phase rejection only chooses the zero
    target branch and does not itself clear storage.
    """
    if not isinstance(resolved_target,int) or not 0 <= resolved_target <= 0xffffffffffffffff:
        raise ValueError('Expected resolved native reference')
    if len(blocked_targets) > 512 or any(not isinstance(v,int) or
           not 0 <= v <= 0xffffffffffffffff for v in blocked_targets):
        raise ValueError('Expected bounded native blocked references')
    if not isinstance(phase_flags,int) or not 0 <= phase_flags <= 255:
        raise ValueError('Expected captured phase flags')
    blocked = resolved_target in blocked_targets
    target = 0 if blocked else resolved_target
    return {'target_enabled': target != 0 and bool(phase_flags & 4),
            'clear_target_storage': blocked, 'filtered_reference': target,
            'blocked': blocked, 'phase_allows_target': bool(phase_flags & 4)}
