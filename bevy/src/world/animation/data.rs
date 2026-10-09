//! Serialized diagnostic bank inputs and playback initialization.
use super::*;

#[derive(Deserialize)]
pub(super) struct SeedNode {
    pub(super) address: u64,
    pub(super) flags: u32,
    pub(super) world: [f32; 16],
    pub(super) world_flags: u32,
    pub(super) parent: Option<u64>,
    pub(super) local: Option<[f32; 16]>,
    pub(super) local_flags: Option<u32>,
}
#[derive(Clone, Deserialize)]
pub(super) struct Track {
    pub(super) index: usize,
    pub(super) clock: ClockTrack,
    pub(super) state: ClockState,
}
#[derive(Deserialize)]
pub(super) struct Modifier {
    pub(super) bone: usize,
    pub(super) state_hex: String,
    pub(super) record_flags: u32,
}
#[derive(Deserialize)]
pub(super) struct Outgoing {
    #[serde(default)]
    pub(super) interrupted_pose: Option<BTreeMap<usize, ([f32; 16], u32)>>,
    #[serde(default)]
    pub(super) freeze_root: bool,
    pub(super) clip: Clip,
    pub(super) tracks: Vec<Track>,
    pub(super) speed: u8,
    pub(super) duration_byte: u8,
    pub(super) elapsed_u16: u16,
    pub(super) ratio: f32,
    pub(super) active: bool,
    #[serde(default)]
    pub(super) root: Option<RootSeed>,
}
#[derive(Clone, Deserialize)]
pub(super) struct RootSeed {
    pub(super) tracks: Vec<Track>,
    pub(super) reference: [f32; 16],
    pub(super) reference_flags: u32,
    pub(super) height: f32,
    pub(super) add_height: bool,
}
#[derive(Clone, Deserialize)]
pub(super) struct ActorMotion {
    pub(super) tracks: Vec<Track>,
    pub(super) entry_gate: u32,
    pub(super) dispatch_flags: u8,
}
#[derive(Clone, Deserialize)]
pub(super) struct ClipTemplate {
    pub(super) clip: Clip,
    pub(super) tracks: Vec<Track>,
    pub(super) root_tracks: Vec<Track>,
    pub(super) actor_tracks: Vec<Track>,
    pub(super) speed: u8,
    pub(super) key: String,
}
#[derive(Deserialize)]
pub(super) struct StationaryContext {
    pub(super) scene_time: f32,
    pub(super) time_origin: f32,
    pub(super) interaction_time: f32,
    pub(super) mode: i32,
    pub(super) pending: i32,
    pub(super) selected_action: i32,
}
#[derive(Deserialize)]
pub(super) struct Controls {
    #[serde(default)]
    pub(super) standing_turn: Option<StandingTurnControls>,
    #[serde(default)]
    pub(super) run: Option<RunControls>,
    #[serde(default)]
    pub(super) turn: Option<TurnControls>,
    pub(super) idle: ClipTemplate,
    pub(super) waiting_idle: ClipTemplate,
    pub(super) slow: ClipTemplate,
    pub(super) restart: ClipTemplate,
    #[serde(default)]
    pub(super) restart_second: Option<ClipTemplate>,
    #[serde(default)]
    pub(super) restart_descriptor: Option<crate::animation::primary_phase::Descriptor>,
    pub(super) start: ClipTemplate,
    pub(super) walk: ClipTemplate,
    pub(super) stop_a: ClipTemplate,
    pub(super) stop_b: ClipTemplate,
    pub(super) transition_duration_byte: u8,
    pub(super) walk_descriptor: crate::animation::primary_phase::Descriptor,
    pub(super) stop_descriptor: crate::animation::primary_phase::Descriptor,
    pub(super) selector_actions: [i32; 12],
    pub(super) start_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) walk_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) idle_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) idle_descriptor: crate::animation::primary_phase::Descriptor,
    pub(super) slow_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) restart_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) stop_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) waiting_transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) stationary_context: StationaryContext,
}
impl Controls {
    pub(super) fn preview_selector_actions(&self, run_requested: bool) -> [i32; 12] {
        let mut actions = crate::input::animation_selector::ordinary_action_table(
            self.selector_actions, run_requested && self.run.is_some());
        // Native mode2 walking bins apply immediately, including a neutral R2
        // hold. Final Run2 eligibility still uses the existing approximate
        // walking dwell adapter below; it is not a qualified native gate.
        actions[9] = self.selector_actions[9];
        actions
    }
}
#[derive(Deserialize)]
pub(super) struct RunControls {
    pub(super) clip: ClipTemplate,
    pub(super) descriptor: crate::animation::primary_phase::Descriptor,
    pub(super) transitions: Vec<crate::animation::action_transition::Table>,
    pub(super) stop_a: ClipTemplate,
    pub(super) stop_b: ClipTemplate,
    pub(super) stop_descriptor: crate::animation::primary_phase::Descriptor,
    pub(super) stop_transitions: Vec<crate::animation::action_transition::Table>,
}
#[derive(Deserialize)]
pub(super) struct TurnControls {
    pub(super) a: ClipTemplate,
    pub(super) b: ClipTemplate,
    pub(super) stop: ClipTemplate,
    pub(super) walk: ClipTemplate,
    pub(super) descriptor: crate::animation::primary_phase::Descriptor,
}
#[derive(Deserialize)]
pub(super) struct StandingTurnControls {
    pub(super) negative: ClipTemplate,
    pub(super) positive: ClipTemplate,
}
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) enum ControlPhase {
    StandingNegative,
    StandingPositive,
    TurningA,
    TurningB,
    TurnStop,
    TurnWalk,
    Idle,
    WaitingIdle,
    Slow,
    Restart,
    RestartSecond,
    Starting,
    Walking,
    Running,
    RunStoppingA,
    RunStoppingB,
    StoppingA,
    StoppingB,
}
#[derive(Deserialize)]
pub(super) struct Seed {
    pub(super) rig: Skeleton,
    pub(super) binding: AnimationBinding,
    pub(super) clip: Clip,
    pub(super) tracks: Vec<Track>,
    pub(super) nodes: Vec<SeedNode>,
    pub(super) bone_addresses: Vec<u64>,
    pub(super) actor_address: u64,
    pub(super) modifiers: Vec<Modifier>,
    pub(super) modifier_requests: Vec<usize>,
    pub(super) speed: u8,
    pub(super) palette_bones: Vec<usize>,
    pub(super) limits: String,
    #[serde(default)]
    pub(super) transition: Option<Outgoing>,
    #[serde(default)]
    pub(super) root: Option<RootSeed>,
    #[serde(default)]
    pub(super) actor_motion: Option<ActorMotion>,
    #[serde(default)]
    pub(super) controls: Option<Controls>,
}
pub(crate) fn load(source: &Source) -> Result<Option<Player>, String> {
    let Some(path) = &source.scene.animation else {
        return Ok(None);
    };
    if std::path::Path::new(path)
        .components()
        .any(|c| !matches!(c, std::path::Component::Normal(_)))
    {
        return Err("Invalid animation asset path".into());
    }
    let seed: Seed =
        serde_json::from_slice(&std::fs::read(source.root.join(path)).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
    let nodes = seed
        .nodes
        .iter()
        .map(|n| {
            (
                n.address,
                Node {
                    flags: n.flags,
                    world: n.world,
                    world_flags: n.world_flags,
                    parent: n.parent,
                    local: n.local.map(|l| (l, n.local_flags.unwrap_or(0))),
                },
            )
        })
        .collect();
    let pose =
        RuntimePose::new(&seed.rig, seed.bone_addresses.clone(), nodes).map_err(str::to_owned)?;
    let mut records = BTreeMap::new();
    for m in &seed.modifiers {
        if m.state_hex.len() != 512 {
            return Err("Modifier seed must contain 256 bytes".into());
        }
        let bytes: Result<Vec<_>, _> = m
            .state_hex
            .as_bytes()
            .chunks_exact(2)
            .map(|p| {
                std::str::from_utf8(p)
                    .map_err(|e| e.to_string())
                    .and_then(|s| u8::from_str_radix(s, 16).map_err(|e| e.to_string()))
            })
            .collect();
        let state = bytes?
            .try_into()
            .map_err(|_| "Invalid modifier seed".to_owned())?;
        if records
            .insert(
                m.bone,
                modifier_cycle::Record {
                    state,
                    record_flags: m.record_flags,
                },
            )
            .is_some()
        {
            return Err("Duplicate modifier seed".into());
        }
    }
    let targets = seed
        .binding
        .clip_targets(&seed.rig, &seed.clip)
        .map_err(str::to_owned)?;
    let mut ordinary = BTreeSet::new();
    for t in &seed.tracks {
        let Some(TrackTarget::Bone(bone)) = targets.get(t.index) else {
            return Err("Non-bone diagnostic track".into());
        };
        if seed.rig.objects[*bone].slot == Some(0) {
            return Err("Diagnostic root must remain explicit".into());
        }
        ordinary.insert(*bone);
    }
    if let Some(outgoing) = &seed.transition {
        let targets = seed
            .binding
            .clip_targets(&seed.rig, &outgoing.clip)
            .map_err(str::to_owned)?;
        for t in &outgoing.tracks {
            let Some(TrackTarget::Bone(bone)) = targets.get(t.index) else {
                return Err("Non-bone outgoing track".into());
            };
            if seed.rig.objects[*bone].slot == Some(0) {
                return Err("Outgoing root requires a reference context".into());
            }
            ordinary.insert(*bone);
        }
    }
    info!("Animation: {}", seed.limits);
    let motion_origin = pose.nodes[&seed.actor_address].world[12..15]
        .try_into()
        .map_err(|_| "Missing actor position")?;
    let scene_time = seed
        .controls
        .as_ref()
        .map_or(0., |c| c.stationary_context.scene_time);
    let time_origin = seed
        .controls
        .as_ref()
        .map_or(0., |c| c.stationary_context.time_origin);
    let mut player = Player {
        seed,
        pose,
        records,
        ordinary,
        stopped: false,
        paused: false,
        motion_origin,
        root_cycles: 0,
        control_phase: ControlPhase::Idle,
        move_requested: false,
        pending_standing_turn: None,
        pending_moving_turn: false,
        selection_velocity: Vec3::ZERO,
        outgoing_selection_velocity: Vec3::ZERO,
        last_turn_candidate_speed: None,
        run_requested: false,
        walk_dwell: 0.,
        run_age: 0.,
        run_from_turn: false,
        input_strength: 1.,
        control_direction: Vec3::ZERO,
        filtered_direction: Vec3::ZERO,
        slow_heading_response: 1.,
        clip_cycles: 0,
        action_phase: 0,
        action_repeat: 0,
        queued_action: None,
        joy_value: 0.,
        scene_time,
        idle_action_time: scene_time - time_origin,
        projected_uvs: Vec::new(),
    };
    if player.seed.controls.is_some() {
        player
            .select(ControlPhase::WaitingIdle, false)
            .map_err(str::to_owned)?;
    }
    Ok(Some(player))
}


