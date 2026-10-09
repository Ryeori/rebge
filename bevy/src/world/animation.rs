//! Diagnostic playback and WASD adapter; approximate steering, no collisions.
use crate::{
    animation::{
        binding::{AnimationBinding, TrackTarget},
        channels::Clip,
        frame,
        hierarchy::Node,
        modifier_cycle, playback,
        runtime_pose::RuntimePose,
        skeleton::Skeleton,
        track_clock::{ClockState, ClockTrack},
    },
    assets::{Source, scene::jade_to_bevy},
};
use bevy::prelude::*;
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};

mod data;
mod controller;
mod pose;
mod stepping;
mod ecs;
mod telemetry;

use data::*;
pub(crate) use data::load;
pub(crate) use ecs::{controls, update};
pub(crate) use telemetry::MovementTrace;

#[derive(Resource)]
pub(crate) struct Player {
    seed: Seed,
    pose: RuntimePose,
    records: BTreeMap<usize, modifier_cycle::Record>,
    ordinary: BTreeSet<usize>,
    stopped: bool,
    paused: bool,
    motion_origin: [f32; 3],
    root_cycles: u32,
    control_phase: ControlPhase,
    move_requested: bool,
    // Preview adapter for the native track's wait-for-blend dispatch.
    // VM eligibility/cooldown and callback chronology remain unported.
    pending_standing_turn: Option<ControlPhase>,
    // Walking eligibility and wait-for-blend dispatch remain preview adapters.
    pending_moving_turn: bool,
    // Selection-only velocity proxy; actor trajectory is never changed by it.
    selection_velocity: Vec3,
    outgoing_selection_velocity: Vec3,
    last_turn_candidate_speed: Option<f32>,
    run_requested: bool,
    walk_dwell: f32,
    run_age: f32,
    run_from_turn: bool,
    input_strength: f32,
    control_direction: Vec3,
    filtered_direction: Vec3,
    // Native1198 is absent from the asset seed; steady1 is an adapter default.
    slow_heading_response: f32,
    clip_cycles: u32,
    action_phase: u8,
    action_repeat: u8,
    queued_action: Option<i32>,
    joy_value: f32,
    scene_time: f32,
    idle_action_time: f32,
    projected_uvs: Vec<(usize, Vec<[f32; 2]>)>,
}
#[derive(Component)]
pub(crate) struct AnimatedBatch(pub usize);

#[cfg(test)]
#[path = "../../tests/unit/world/animation.rs"]
mod tests;



