//! One direct-actor root track: clock -> ordered entry/publication effects.
//! No controller phase selection, VM setters, transition blend or ECS scheduling.
use super::{
    actor_reference::compose_reference_basis,
    channels::{Track, sample_rotation, sample_translation},
    pose_blend::quaternion_matrix,
    reference_entry::{
        ActorReferenceStorage, EntryContext, EntryResult, MatrixStorage, execute_effects,
    },
    root_clock::{RootPass, advance},
    track_clock::{ClockState, ClockTrack},
};

#[derive(Clone, Copy)]
pub enum ReferenceSource {
    /// Read after each preceding entry copy, never cache the initial reference.
    Actor,
    /// Explicit transition/zero-delta evaluation reference at writer time.
    Explicit(MatrixStorage),
}

pub struct PublicationContext {
    pub reference: ReferenceSource,
    pub root_count: u32,
    pub dispatch_flags: u8,
}

pub struct Execution {
    pub pass: RootPass,
    pub entries: Vec<EntryResult>,
    pub actor: ActorReferenceStorage,
}

pub struct RefreshTrack<'a> {
    pub clock: &'a ClockTrack,
    pub source: &'a Track,
    pub state: ClockState,
}

pub struct RefreshEvaluation {
    pub reference: MatrixStorage,
    pub evaluated_root: MatrixStorage,
    /// Evaluation may enter/reset keys even with zero delta. The caller owns
    /// the instance states and decides their native lifetime explicitly.
    pub states: Vec<ClockState>,
}

/// Restricted direct primary 1409c0850 numerical path. Actor world remains
/// unchanged; return reference and evaluated states for explicit instance use.
/// Supply the observed identity evaluation reference and publication gates.
/// Event keys, other actor destinations and whole-clip callbacks are excluded.
pub fn evaluate_refresh(
    actor: &ActorReferenceStorage,
    tracks: &[RefreshTrack<'_>],
    evaluation_reference: MatrixStorage,
    root_count: u32,
    dispatch_flags: u8,
) -> Result<RefreshEvaluation, &'static str> {
    if actor.gao_flags & 0x400000 != 0
        || actor.gao_flags & 0x4000000 == 0
        || actor.reference.is_none()
        || tracks.is_empty()
    {
        return Err("Explicit direct actor reference and root tracks required");
    }
    if actor.world.flags & 8 != 0 {
        return Err("Scaled refresh inverse requires native reciprocal-scale path");
    }
    let mut temporary = actor.clone();
    temporary.world.flags &= !8;
    for i in [3, 7, 11] {
        temporary.world.values[i] = 0.;
    }
    let mut states = Vec::with_capacity(tracks.len());
    for track in tracks {
        let execution = run_track(
            track.clock,
            track.source,
            track.state,
            0.,
            &temporary,
            &EntryContext {
                manager_gate: 0,
                clip_present: true,
                actor_present: true,
                reference_aliases_source: false,
            },
            &PublicationContext {
                reference: ReferenceSource::Explicit(evaluation_reference),
                root_count,
                dispatch_flags,
            },
        )?;
        states.push(execution.pass.state);
        temporary = execution.actor;
    }
    let (values, flags) = super::actor_reference::refresh_reference(
        temporary.world.values,
        temporary.world.flags,
        actor.world.values,
        actor.world.flags,
    )?;
    Ok(RefreshEvaluation {
        reference: MatrixStorage { values, flags },
        evaluated_root: temporary.world,
        states,
    })
}

/// Restricted 140b49ba0/140b49810 direct GAO path. Preserve unwritten bytes.
pub fn publish_direct(
    track: &Track,
    index: usize,
    elapsed: f32,
    terminal: bool,
    actor: &mut ActorReferenceStorage,
    context: &PublicationContext,
) -> Result<(), &'static str> {
    if actor.gao_flags & 0x400000 != 0 || track.short1 != 65535 {
        return Err("Direct actor root publication required");
    }
    if !terminal && context.root_count > 1 && context.dispatch_flags & 0x12 == 0x12 {
        return Ok(());
    }
    let frame = track.frames.get(index).ok_or("Missing root frame")?;
    let next = track.frames.get((index + 1) % track.frames.len()).unwrap();
    if frame.flags & (0x20 | 0x800) != 0 || next.flags & (0x20 | 0x800) != 0 {
        return Err("Root mirror/hold semantics differ from ordinary sampler");
    }
    if terminal && frame.tick_raw != 0 {
        return Err("Nonzero terminal root duration requires consumer-specific sampling");
    }
    let reference = match context.reference {
        ReferenceSource::Actor => actor.reference.ok_or("Missing root reference")?,
        ReferenceSource::Explicit(matrix) => matrix,
    };
    let mut destination = actor.world;
    if frame.transform.flags & 0x14 != 0 {
        let rotation = sample_rotation(track, index, elapsed)?.ok_or("Missing root rotation")?;
        (destination.values, destination.flags) = compose_reference_basis(
            destination.values,
            destination.flags,
            quaternion_matrix(rotation),
            4,
            reference.values,
            reference.flags,
        )?;
        destination.flags |= 4;
    } else {
        if frame.transform.float3_channels.len() != 1
            || (!next.transform.float3_channels.is_empty()
                && next.transform.float3_channels.len() != 1)
        {
            return Err("Root position consumer requires a single vector key");
        }
        if reference.flags & 8 != 0 || reference.values.iter().any(|v| !v.is_finite()) {
            return Err("Nonfinite or scaled root position reference");
        }
        let position = sample_translation(track, index, elapsed)?.ok_or("Missing root position")?;
        let r = reference.values;
        for row in 0..3 {
            let [a, b, c] = if row == 0 { [0, 1, 2] } else { [1, 0, 2] };
            destination.values[12 + row] = ((position[a] * r[a * 4 + row]
                + position[b] * r[b * 4 + row])
                + position[c] * r[c * 4 + row])
                + r[12 + row];
        }
        destination.flags |= 2;
    }
    actor.world = destination;
    Ok(())
}

/// Execute one already-selected track with a scaled delta. Each actor/reference
/// input and alias observation is explicit. Return owned output only on success.
/// Other root tracks keep their own clocks; this does not advance a whole clip.
pub fn run_track(
    clock: &ClockTrack,
    source: &Track,
    state: ClockState,
    scaled_delta: f32,
    actor: &ActorReferenceStorage,
    entry: &EntryContext,
    publication: &PublicationContext,
) -> Result<Execution, &'static str> {
    if clock.flags & 0x8000 == 0 {
        return Err("Track is not dispatched through the root clock path");
    }
    if clock.frames.len() != source.frames.len()
        || clock
            .frames
            .iter()
            .zip(&source.frames)
            .any(|(a, b)| a.tick_raw != b.tick_raw || a.flags & !4 != b.flags & !4)
    {
        return Err("Root source and runtime clock definitions differ beyond entry bit4");
    }
    let pass = advance(clock, state, scaled_delta)?;
    let mut prepared = actor.clone();
    let entries = execute_effects(
        &mut prepared,
        &pass.effects,
        |_, _| {
            Ok(EntryContext {
                manager_gate: entry.manager_gate,
                clip_present: entry.clip_present,
                actor_present: entry.actor_present,
                reference_aliases_source: entry.reference_aliases_source,
            })
        },
        |index, elapsed, terminal, actor| {
            publish_direct(source, index, elapsed, terminal, actor, publication)
        },
    )?;
    Ok(Execution {
        pass,
        entries,
        actor: prepared,
    })
}

#[cfg(test)]
#[path = "../../tests/unit/animation/root_pipeline.rs"]
mod tests;
