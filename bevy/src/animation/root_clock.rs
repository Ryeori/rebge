//! Numerical140b27970 root dispatch. Ordered effects are returned, not executed.
//! Caller owns reference entry, channel publication, dispatch gates and phases.
use super::track_clock::{ClockState, ClockTrack, scaled_delta};

#[derive(Debug)]
pub enum RootEffect {
    ReferenceEntry {
        index: usize,
    },
    Publish {
        index: usize,
        elapsed: f32,
        terminal: bool,
    },
}

pub struct RootPass {
    pub state: ClockState,
    pub remaining: f32,
    pub finished: bool,
    pub effects: Vec<RootEffect>,
}

pub fn advance(
    track: &ClockTrack,
    mut state: ClockState,
    mut delta: f32,
) -> Result<RootPass, &'static str> {
    if !delta.is_finite()
        || delta < 0.
        || !state.elapsed.is_finite()
        || state.elapsed < 0.
        || state.index >= track.frames.len()
    {
        return Err("Invalid root clock input");
    }
    if track
        .frames
        .iter()
        .any(|f| f.flags & 0x7c0 != 0x80 || f.flags & 1 != 0)
    {
        return Err("Nontransform root key unsupported");
    }
    let last = track.frames.len() - 1;
    if state.elapsed > f32::from(track.frames[state.index].tick_raw) / 60. {
        return Err("Root elapsed exceeds current segment");
    }
    if track.auxiliary_short == 255 && state.index == last {
        return Err("Clip-wide active-state reset requires external state");
    }
    let mut effects = Vec::new();
    if state.index == last {
        state.index = 0;
        state.elapsed = 0.;
        state.flags &= !4;
    }
    let epsilon = f32::from_bits(0x3727c5ac);
    for _ in 0..4096 {
        let frame = &track.frames[state.index];
        let duration = f32::from(frame.tick_raw) / 60.;
        if frame.flags & 4 != 0 && state.flags & 4 == 0 {
            effects.push(RootEffect::ReferenceEntry { index: state.index });
        }
        let end = state.elapsed + delta;
        if end <= duration - epsilon {
            state.elapsed = end;
            effects.push(RootEffect::Publish {
                index: state.index,
                elapsed: end,
                terminal: false,
            });
            state.flags |= 4;
            return Ok(RootPass {
                state,
                remaining: 0.,
                finished: false,
                effects,
            });
        }
        delta -= duration - state.elapsed;
        if delta <= 0. {
            delta = 0.;
        }
        if state.index == last {
            effects.push(RootEffect::Publish {
                index: last,
                elapsed: state.elapsed,
                terminal: true,
            });
            state.elapsed = 0.;
            state.flags &= !4;
            return Ok(RootPass {
                state,
                remaining: delta,
                finished: true,
                effects,
            });
        }
        state.index += 1;
        state.elapsed = 0.;
        state.flags &= !4;
    }
    Err("Root traversal exceeds bound")
}

///1409bd3b0 carry conversion. A caller must decide phase/repeat continuation.
pub fn unscaled_remaining(remaining: f32, speed: u8) -> Result<f32, &'static str> {
    if !remaining.is_finite() || remaining < 0. || speed == 0 {
        return Err("Finite remainder and nonzero speed required");
    }
    let result = (remaining * 60.) / f32::from(speed);
    if !result.is_finite() {
        return Err("Root remainder conversion overflow");
    }
    Ok(result)
}

pub struct PrimaryRootPass {
    pub state: ClockState,
    pub repeat: u8,
    pub phase_finished: bool,
    pub unscaled_remaining: f32,
    pub effects: Vec<RootEffect>,
}

/// Numerical1409bd3b0 continuation of one explicit phase. At the repeat limit,
/// return before phase selection/resource rebinding; no inferred fallback phase.
/// Side-effect intents retain native pass order but are not executed here.
pub fn advance_primary_same_phase(
    track: &ClockTrack,
    mut state: ClockState,
    mut delta: f32,
    speed: u8,
    mut repeat: u8,
    repeat_limit: u8,
) -> Result<PrimaryRootPass, &'static str> {
    if speed == 0 {
        return Err("Zero-speed controller continuation unsupported");
    }
    let mut effects = Vec::new();
    for _ in 0..4096 {
        let mut pass = advance(track, state, scaled_delta(delta, speed)?)?;
        effects.append(&mut pass.effects);
        state = pass.state;
        if !pass.finished {
            return Ok(PrimaryRootPass {
                state,
                repeat,
                phase_finished: false,
                unscaled_remaining: 0.,
                effects,
            });
        }
        delta = unscaled_remaining(pass.remaining, speed)?;
        repeat = repeat.wrapping_add(1);
        if repeat_limit <= repeat {
            return Ok(PrimaryRootPass {
                state,
                repeat: 0,
                phase_finished: true,
                unscaled_remaining: delta,
                effects,
            });
        }
        if delta == 0. {
            return Ok(PrimaryRootPass {
                state,
                repeat,
                phase_finished: false,
                unscaled_remaining: 0.,
                effects,
            });
        }
    }
    Err("Primary phase continuation exceeded bound")
}

#[cfg(test)]
#[path = "../../tests/unit/animation/root_clock.rs"]
mod tests;
