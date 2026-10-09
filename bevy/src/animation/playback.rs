//! Stateful selected ordinary tracks. Clip selection, root clocks and controller
//! restarts remain explicit; the caller carries returned clocks to the next tick.
use super::{
    binding::AnimationBinding,
    channels::Clip,
    local_pose::{self, SampledLocalPose, TrackState},
    skeleton::Skeleton,
    track_clock::{self, ClockState, ClockTrack},
};

pub struct SelectedTrack<'a> {
    pub index: usize,
    pub clock: &'a ClockTrack,
    pub state: ClockState,
}
pub struct Advance {
    pub states: Vec<Option<ClockState>>,
    pub remaining: Vec<(usize, f32)>,
}

pub fn advance(
    track_count: usize,
    selected: &[SelectedTrack<'_>],
    delta: f32,
    speed: u8,
    actor_terminal: bool,
) -> Result<Advance, &'static str> {
    let delta = track_clock::scaled_delta(delta, speed)?;
    let mut states = vec![None; track_count];
    let mut remaining = Vec::new();
    for track in selected {
        if track.index >= track_count || states[track.index].is_some() {
            return Err("Duplicate or invalid playback track");
        }
        let result = track_clock::advance(track.clock, track.state, delta, actor_terminal)?;
        states[track.index] = Some(result.state);
        if result.remaining != 0. {
            remaining.push((track.index, result.remaining));
        }
    }
    Ok(Advance { states, remaining })
}

pub struct Playback {
    pub clocks: Advance,
    pub locals: SampledLocalPose,
}

pub struct Tick {
    pub clocks: Advance,
    pub frame: super::frame::Frame,
}

/// Advance selected source channels and evaluate their frame atomically.
/// The caller persists both returned clocks and finalized runtime/modifiers.
/// Root/controller selection and transition blending are external inputs.
pub fn tick(
    prior: &super::runtime_pose::RuntimePose,
    binding: &AnimationBinding,
    clip: &Clip,
    selected: &[SelectedTrack<'_>],
    speed: u8,
    actor_terminal: bool,
    inputs: super::frame::Inputs<'_>,
) -> Result<Tick, &'static str> {
    if inputs.local_pose.is_some() {
        return Err("Playback owns the sampled local pose");
    }
    let playback = sample(
        inputs.rig,
        binding,
        clip,
        selected,
        inputs.delta,
        speed,
        actor_terminal,
    )?;
    let frame = super::frame::evaluate(
        prior,
        super::frame::Inputs {
            rig: inputs.rig,
            actor_address: inputs.actor_address,
            actor: inputs.actor,
            local_pose: Some(&playback.locals),
            ordinary_bones: inputs.ordinary_bones,
            root: inputs.root,
            modifiers: inputs.modifiers,
            modifier_requests: inputs.modifier_requests,
            delta: inputs.delta,
            normalize_modifier_publication: inputs.normalize_modifier_publication,
            palette_bones: inputs.palette_bones,
        },
    )?;
    Ok(Tick {
        clocks: playback.clocks,
        frame,
    })
}
pub fn sample(
    rig: &Skeleton,
    binding: &AnimationBinding,
    clip: &Clip,
    selected: &[SelectedTrack<'_>],
    delta: f32,
    speed: u8,
    actor_terminal: bool,
) -> Result<Playback, &'static str> {
    for input in selected {
        let source = clip
            .tracks
            .get(input.index)
            .ok_or("Missing playback source track")?;
        if source.short1 == 65535 {
            return Err("Ordinary playback cannot own actor root/event destinations");
        }
        if source.frames.len() != input.clock.frames.len()
            || source
                .frames
                .iter()
                .zip(&input.clock.frames)
                .any(|(a, b)| a.tick_raw != b.tick_raw || a.flags != b.flags)
        {
            return Err("Playback clock/source definition mismatch");
        }
    }
    let clocks = advance(clip.tracks.len(), selected, delta, speed, actor_terminal)?;
    let states: Vec<_> = clocks
        .states
        .iter()
        .map(|s| {
            s.map(|s| TrackState {
                index: s.index,
                elapsed: s.elapsed,
            })
        })
        .collect();
    let locals = local_pose::sample_local_pose(rig, binding, clip, &states)?;
    Ok(Playback { clocks, locals })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/playback.rs"]
mod tests;
