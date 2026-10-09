//! Restricted forward transform clock from140b272a0, with1409bbd60 speed scale.
//! Event keys, clip/controller restart and auxiliary-byte8 semantics are separate.
use serde::Deserialize;

#[derive(Clone, Copy, Deserialize)]
pub struct ClockState {
    pub index: usize,
    pub elapsed: f32,
    pub flags: u16,
}
#[derive(Clone, Deserialize)]
pub struct ClockFrame {
    pub tick_raw: u16,
    pub flags: u16,
}
#[derive(Clone, Deserialize)]
pub struct ClockTrack {
    pub frames: Vec<ClockFrame>,
    pub flags: u16,
    pub auxiliary_short: u16,
}
pub struct ClockResult {
    pub state: ClockState,
    pub remaining: f32,
    pub finished: bool,
}

pub fn scaled_delta(delta: f32, speed: u8) -> Result<f32, &'static str> {
    if !delta.is_finite() || delta < 0. {
        return Err("Only finite forward delta supported");
    }
    Ok((f32::from(speed) * delta) / 60.)
}

pub fn advance(
    track: &ClockTrack,
    mut state: ClockState,
    mut delta: f32,
    actor_root_terminal: bool,
) -> Result<ClockResult, &'static str> {
    if !delta.is_finite()
        || delta < 0.
        || !state.elapsed.is_finite()
        || state.elapsed < 0.
        || state.index >= track.frames.len()
    {
        return Err("Invalid forward track state");
    }
    if track.flags & 8 != 0
        || track
            .frames
            .iter()
            .any(|f| f.flags & 0x7c0 != 0x80 || f.flags & (1 | 4) != 0)
    {
        return Err("Event/entry callback track unsupported");
    }
    let last = track.frames.len() - 1;
    let duration = f32::from(track.frames[state.index].tick_raw) / 60.;
    if state.elapsed > duration {
        return Err("Elapsed exceeds current native segment");
    }
    if delta != 0. && state.index == last && state.elapsed == duration && track.flags & 2 != 0 {
        if track.auxiliary_short == 255 {
            return Err("Special restart helper unsupported");
        }
        state.index = 0;
        state.flags &= !4;
    }
    for _ in 0..4096 {
        let duration = f32::from(track.frames[state.index].tick_raw) / 60.;
        let end = state.elapsed + delta;
        let overflow = if end <= duration {
            0.
        } else {
            delta - (duration - state.elapsed)
        };
        state.elapsed = if end <= duration { end } else { duration };
        let old_flags = state.flags;
        state.flags |= 4;
        if overflow == 0. {
            return Ok(ClockResult {
                state,
                remaining: 0.,
                finished: false,
            });
        }
        state.elapsed = 0.;
        if state.index == last {
            if track.flags & 2 == 0 {
                if track.flags & 4 != 0 {
                    state.flags = (old_flags & !1) | 4;
                    state.elapsed = duration;
                    return Ok(ClockResult {
                        state,
                        remaining: overflow,
                        finished: false,
                    });
                }
            } else {
                state.index = 0;
                state.flags = old_flags & !4;
            }
            if actor_root_terminal {
                state.index = last;
                state.elapsed = duration;
                return Ok(ClockResult {
                    state,
                    remaining: overflow,
                    finished: true,
                });
            }
            if track.flags & (2 | 4) == 0 {
                return Err("Unbounded terminal continuation unsupported");
            }
        } else {
            state.index += 1;
            state.flags = old_flags & !4;
        }
        delta = overflow;
    }
    Err("Track traversal exceeded bound; zero-duration cycle unsupported")
}

#[cfg(test)]
#[path = "../../tests/unit/animation/track_clock.rs"]
mod tests;
