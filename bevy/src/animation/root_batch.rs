//! Explicit same-phase diagnostic root batch; controller phase changes excluded.
use super::{
    channels::Track,
    reference_entry::{ActorReferenceStorage, EntryContext},
    root_pipeline::{self, PublicationContext, ReferenceSource},
    track_clock::{self, ClockState, ClockTrack},
};
pub struct TrackInput<'a> {
    pub source: &'a Track,
    pub clock: &'a ClockTrack,
    pub state: ClockState,
}
pub struct Batch {
    pub actor: ActorReferenceStorage,
    pub states: Vec<ClockState>,
    pub completions: u32,
}
pub struct Pass {
    pub batch: Batch,
    pub remaining: f32,
}
/// One native batch invocation. The first destination owns completion/carry;
/// every destination still receives the full scaled input before rebinding.
pub fn advance_once(
    inputs: &[TrackInput<'_>],
    actor: &ActorReferenceStorage,
    delta: f32,
    speed: u8,
    entry_gate: u32,
    dispatch_flags: u8,
) -> Result<Pass, &'static str> {
    if inputs.is_empty() {
        return Err("Missing controlling root track");
    }
    let scaled = track_clock::scaled_delta(delta, speed)?;
    let mut actor = actor.clone();
    let mut states = Vec::new();
    let mut finished = false;
    let mut remaining = 0.;
    for (i, input) in inputs.iter().enumerate() {
        let result = root_pipeline::run_track(
            input.clock,
            input.source,
            input.state,
            scaled,
            &actor,
            &EntryContext {
                manager_gate: entry_gate,
                clip_present: true,
                actor_present: true,
                reference_aliases_source: false,
            },
            &PublicationContext {
                reference: ReferenceSource::Actor,
                root_count: inputs.len() as u32,
                dispatch_flags,
            },
        )?;
        if i == 0 {
            finished = result.pass.finished;
            if finished {
                remaining = super::root_clock::unscaled_remaining(result.pass.remaining, speed)?;
            }
        }
        states.push(result.pass.state);
        actor = result.actor;
    }
    Ok(Pass {
        batch: Batch {
            actor,
            states,
            completions: u32::from(finished),
        },
        remaining,
    })
}
/// Complete all root destinations before carrying a shared terminal remainder.
/// Diagnostic publication policy is explicit; no VM setter/controller inference.
pub fn advance(
    inputs: &[TrackInput<'_>],
    actor: &ActorReferenceStorage,
    delta: f32,
    speed: u8,
    entry_gate: u32,
    dispatch_flags: u8,
) -> Result<Batch, &'static str> {
    if inputs.is_empty() {
        return Err("Missing diagnostic root tracks");
    }
    let mut delta = track_clock::scaled_delta(delta, speed)?;
    let mut actor = actor.clone();
    let mut states: Vec<_> = inputs.iter().map(|t| t.state).collect();
    let mut completions = 0;
    for _ in 0..64 {
        let mut finished = Vec::new();
        let mut remainders = Vec::new();
        for (i, input) in inputs.iter().enumerate() {
            let result = root_pipeline::run_track(
                input.clock,
                input.source,
                states[i],
                delta,
                &actor,
                &EntryContext {
                    manager_gate: entry_gate,
                    clip_present: true,
                    actor_present: true,
                    reference_aliases_source: false,
                },
                &PublicationContext {
                    reference: ReferenceSource::Actor,
                    root_count: inputs.len() as u32,
                    dispatch_flags,
                },
            )?;
            states[i] = result.pass.state;
            finished.push(result.pass.finished);
            remainders.push(result.pass.remaining);
            actor = result.actor;
        }
        if finished.iter().all(|f| !*f) {
            return Ok(Batch {
                actor,
                states,
                completions,
            });
        }
        if !finished.iter().all(|f| *f) {
            return Err("Root batch needs an explicit mixed-duration controller policy");
        }
        if remainders.iter().any(|r| (*r - remainders[0]).abs() > 1e-6) {
            return Err("Root terminal carry differs across destinations");
        }
        completions += 1;
        delta = remainders[0];
        if delta == 0. {
            return Ok(Batch {
                actor,
                states,
                completions,
            });
        }
    }
    Err("Root batch exceeded diagnostic repeat bound")
}
