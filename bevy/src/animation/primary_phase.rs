//! 1409bd3b0 phase policy after completion of the first controlling track.
//! Rebinding, callbacks, VM action requests and channel publication are caller effects.
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct Phase {
    pub repeat_limit: u8,
    pub speed_source_byte: u8,
    pub flags: u8,
}
#[derive(Clone, Deserialize)]
pub struct Descriptor {
    pub loop_phase: u8,
    pub phases: Vec<Phase>,
}
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Effect {
    Repeat,
    Bind {
        phase: u8,
        speed: Option<u8>,
        clip_flags: u8,
        actor_control: u8,
    },
    QueuedAction,
    Disable,
}
#[derive(Clone, Copy, Debug)]
pub struct Completion {
    pub phase: u8,
    pub repeat: u8,
    pub effect: Effect,
}
pub struct ClockResult {
    pub phase: u8,
    pub repeat: u8,
    pub speed: u8,
    pub state: super::track_clock::ClockState,
    pub remaining: f32,
    pub effects: Vec<(u8, super::root_clock::RootPass, Option<Effect>)>,
}
/// Traverse the explicit first controlling track across descriptor phases.
/// Effects must be replayed in order with all other channels before pose finalization.
pub fn advance_clock(
    descriptor: &Descriptor,
    tracks: &[super::track_clock::ClockTrack],
    mut phase: u8,
    mut repeat: u8,
    mut speed: u8,
    mut state: super::track_clock::ClockState,
    mut delta: f32,
    queued: bool,
) -> Result<ClockResult, &'static str> {
    if tracks.len() != descriptor.phases.len() || speed == 0 {
        return Err("Invalid phase clock bank");
    }
    let mut effects = Vec::new();
    for _ in 0..256 {
        let pass = super::root_clock::advance(
            tracks.get(phase as usize).ok_or("Missing phase clock")?,
            state,
            super::track_clock::scaled_delta(delta, speed)?,
        )?;
        state = pass.state;
        if !pass.finished {
            effects.push((phase, pass, None));
            return Ok(ClockResult {
                phase,
                repeat,
                speed,
                state,
                remaining: 0.,
                effects,
            });
        }
        delta = super::root_clock::unscaled_remaining(pass.remaining, speed)?;
        let decision = complete(descriptor, phase, repeat, queued)?;
        effects.push((phase, pass, Some(decision.effect)));
        phase = decision.phase;
        repeat = decision.repeat;
        match decision.effect {
            Effect::Bind {
                speed: new_speed, ..
            } => {
                if let Some(new_speed) = new_speed {
                    speed = new_speed;
                }
                if speed == 0 {
                    return Err("Zero-speed phase continuation unsupported");
                }
                state = super::track_clock::ClockState {
                    index: 0,
                    elapsed: 0.,
                    flags: 1,
                };
            }
            Effect::Disable | Effect::QueuedAction => {
                return Ok(ClockResult {
                    phase,
                    repeat,
                    speed,
                    state,
                    remaining: delta,
                    effects,
                })
            }
            Effect::Repeat => {}
        }
        if delta == 0. {
            return Ok(ClockResult {
                phase,
                repeat,
                speed,
                state,
                remaining: 0.,
                effects,
            });
        }
    }
    Err("Primary phase traversal exceeds bound")
}
pub fn complete(
    descriptor: &Descriptor,
    phase: u8,
    repeat: u8,
    queued: bool,
) -> Result<Completion, &'static str> {
    if descriptor.phases.is_empty() || descriptor.phases.len() > 255 {
        return Err("Invalid primary phase descriptor");
    }
    let current = descriptor
        .phases
        .get(phase as usize)
        .ok_or("Missing current primary phase")?;
    let repeat = repeat.wrapping_add(1);
    if repeat < current.repeat_limit {
        return Ok(Completion {
            phase,
            repeat,
            effect: Effect::Repeat,
        });
    }
    let mut next = phase as usize + 1;
    if next >= descriptor.phases.len() {
        if queued {
            return Ok(Completion {
                phase,
                repeat: 0,
                effect: Effect::QueuedAction,
            });
        }
        if descriptor.loop_phase == 255 {
            return Ok(Completion {
                phase,
                repeat: 0,
                effect: Effect::Disable,
            });
        }
        next = (descriptor.loop_phase as usize).min(descriptor.phases.len() - 1);
    }
    let row = &descriptor.phases[next];
    Ok(Completion {
        phase: next as u8,
        repeat: 0,
        effect: Effect::Bind {
            phase: next as u8,
            speed: (next != phase as usize)
                .then_some(((row.speed_source_byte as u32 * 60) >> 6) as u8),
            clip_flags: row.flags & 15,
            actor_control: (row.flags >> 4) & 7,
        },
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/primary_phase.rs"]
mod tests;
