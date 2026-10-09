//! 1409c1d60 refresh dispatch after VM transform setters.
//! The executor supplies 1409c0850 writer-time evaluation, not a final pose.

#[derive(Clone, Copy)]
pub struct DispatchState {
    pub actor_present: bool,
    pub gao_flags: u32,
    pub component_present: bool,
    pub component_flags: u16,
    pub primary_present: bool,
    pub transition_present: bool,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Target {
    Primary,
    Transition,
}

/// Mirrors native gate order, including re-reading flags after primary refresh.
/// The executor owns temporary actor matrices, zero-delta root evaluation with
/// entry gate disabled, reference product and native global-context restoration.
/// It must return the state observed after its operation. This dispatcher alone
/// does not reconstruct those operations or promise rollback on executor error.
pub fn dispatch(
    mut state: DispatchState,
    requested: u8,
    mut execute: impl FnMut(Target, DispatchState) -> Result<DispatchState, &'static str>,
) -> Result<DispatchState, &'static str> {
    if !state.actor_present
        || state.gao_flags & 2 == 0
        || state.gao_flags & 0x4000000 == 0
        || !state.component_present
        || !state.primary_present
    {
        return Ok(state);
    }
    if requested & 1 != 0 {
        state = execute(Target::Primary, state)?;
    }
    if state.gao_flags & 2 != 0
        && state.component_present
        && state.component_flags & 0x200 != 0
        && requested & 2 != 0
    {
        // Native dereferences the secondary pointer without another null gate.
        // An absent explicit instance remains an error in the reconstruction.
        if !state.transition_present {
            return Err("Active transition refresh instance missing");
        }
        state = execute(Target::Transition, state)?;
    }
    Ok(state)
}
