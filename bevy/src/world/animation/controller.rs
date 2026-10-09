//! Preview action selection and transition requests.
use super::*;

impl Player {
    pub(super) fn select(&mut self, phase: ControlPhase, blend: bool) -> Result<(), &'static str> {
        self.select_at(phase, blend, None)
    }
    pub(super) fn select_at(
        &mut self,
        phase: ControlPhase,
        blend: bool,
        seek_seconds: Option<f32>,
    ) -> Result<(), &'static str> {
        self.select_at_duration(phase, blend, seek_seconds, None)
    }
    pub(super) fn select_at_duration(
        &mut self,
        phase: ControlPhase,
        blend: bool,
        seek_seconds: Option<f32>,
        duration_override: Option<u8>,
    ) -> Result<(), &'static str> {
        let controls = self
            .seed
            .controls
            .as_ref()
            .ok_or("Missing diagnostic clip bank")?;
        let mut template = match phase {
            ControlPhase::StandingNegative => {
                &controls
                    .standing_turn
                    .as_ref()
                    .ok_or("Missing standing turn bank")?
                    .negative
            }
            ControlPhase::StandingPositive => {
                &controls
                    .standing_turn
                    .as_ref()
                    .ok_or("Missing standing turn bank")?
                    .positive
            }
            ControlPhase::Running => &controls.run.as_ref().ok_or("Missing run bank")?.clip,
            ControlPhase::RunStoppingA => &controls.run.as_ref().ok_or("Missing run bank")?.stop_a,
            ControlPhase::RunStoppingB => &controls.run.as_ref().ok_or("Missing run bank")?.stop_b,
            ControlPhase::TurningA => &controls.turn.as_ref().ok_or("Missing turn clips")?.a,
            ControlPhase::TurningB => &controls.turn.as_ref().ok_or("Missing turn clips")?.b,
            ControlPhase::TurnStop => &controls.turn.as_ref().ok_or("Missing turn clips")?.stop,
            ControlPhase::TurnWalk => &controls.turn.as_ref().ok_or("Missing turn clips")?.walk,
            ControlPhase::Idle => &controls.idle,
            ControlPhase::WaitingIdle => &controls.waiting_idle,
            ControlPhase::Slow => &controls.slow,
            ControlPhase::Restart => &controls.restart,
            ControlPhase::RestartSecond => controls
                .restart_second
                .as_ref()
                .ok_or("Missing restart phase1")?,
            ControlPhase::Starting => &controls.start,
            ControlPhase::Walking => &controls.walk,
            ControlPhase::StoppingA => &controls.stop_a,
            ControlPhase::StoppingB => &controls.stop_b,
        }
        .clone();
        if let Some(seconds) = seek_seconds {
            for t in template
                .tracks
                .iter_mut()
                .chain(&mut template.root_tracks)
                .chain(&mut template.actor_tracks)
            {
                t.state =
                    crate::animation::action_progress::seek(&t.clock, seconds, t.state.flags)?;
            }
        }
        let mut duration = duration_override.unwrap_or(controls.transition_duration_byte);
        // Preview compensation for incomplete native gait phase alignment:
        // avoid a very short pose crossfade when leaving running.
        if blend
            && self.control_phase == ControlPhase::Running
            && matches!(phase, ControlPhase::StoppingA | ControlPhase::RunStoppingA)
        {
            duration = duration.max(14);
        }
        let old = Outgoing {
            // Preview interruption: retain the visible blend, not just its primary clip.
            // A completed turn exit also needs its visible terminal locals:
            // replaying it as an outgoing loop resets the model root backwards.
            interrupted_pose: (self.seed.transition.as_ref().is_some_and(|t| t.active)
                || (self.control_phase == ControlPhase::TurnWalk && phase == ControlPhase::Running)
                || (matches!(self.control_phase, ControlPhase::StandingNegative | ControlPhase::StandingPositive)
                    && phase == ControlPhase::Idle))
                .then(|| {
                self.pose
                    .bone_addresses
                    .iter()
                    .enumerate()
                    .filter_map(|(bone, address)| {
                        self.pose.nodes[address].local.map(|local| (bone, local))
                    })
                    .collect()
            }),
            // Preview workaround for missing outgoing actor-root continuation:
            // keep its root sample across gait blends so loops cannot wrap it.
            freeze_root: matches!(
                phase,
                ControlPhase::Slow
                    | ControlPhase::Starting
                    | ControlPhase::Walking
                    | ControlPhase::Running
                    | ControlPhase::StoppingA
                    | ControlPhase::StoppingB
                    | ControlPhase::RunStoppingA
                    | ControlPhase::RunStoppingB
                    | ControlPhase::Idle
            ) && matches!(
                self.control_phase,
                ControlPhase::Slow
                    | ControlPhase::Starting
                    | ControlPhase::Walking
                    | ControlPhase::Running
                    | ControlPhase::TurnWalk
            ),
            clip: self.seed.clip.clone(),
            tracks: self.seed.tracks.clone(),
            speed: self.seed.speed,
            duration_byte: duration,
            elapsed_u16: 0,
            ratio: 0.,
            active: blend,
            root: self.seed.root.clone(),
        };
        let node = &self.pose.nodes[&self.seed.actor_address];
        let actor = crate::animation::reference_entry::ActorReferenceStorage {
            gao_flags: node.flags,
            world: crate::animation::reference_entry::MatrixStorage {
                values: node.world,
                flags: node.world_flags,
            },
            linked_local: None,
            reference: self.seed.root.as_ref().map(|r| {
                crate::animation::reference_entry::MatrixStorage {
                    values: r.reference,
                    flags: r.reference_flags,
                }
            }),
        };
        let tracks: Vec<_> = template
            .actor_tracks
            .iter()
            .map(|t| crate::animation::root_pipeline::RefreshTrack {
                clock: &t.clock,
                source: &template.clip.tracks[t.index],
                state: t.state,
            })
            .collect();
        let refresh = crate::animation::root_pipeline::evaluate_refresh(
            &actor,
            &tracks,
            crate::animation::reference_entry::MatrixStorage {
                values: crate::animation::hierarchy::IDENTITY,
                flags: 0,
            },
            tracks.len() as u32,
            0,
        )?;
        let root = self
            .seed
            .root
            .as_ref()
            .ok_or("Diagnostic controls require root context")?;
        let new_root = RootSeed {
            tracks: template.root_tracks,
            reference: refresh.reference.values,
            reference_flags: refresh.reference.flags,
            height: root.height,
            add_height: root.add_height,
        };
        let targets = self
            .seed
            .binding
            .clip_targets(&self.seed.rig, &template.clip)?;
        let mut ordinary = BTreeSet::new();
        for t in &template.tracks {
            if let Some(TrackTarget::Bone(bone)) = targets.get(t.index) {
                ordinary.insert(*bone);
            } else {
                return Err("Control bank contains non-bone ordinary track");
            }
        }
        if blend {
            let targets = self.seed.binding.clip_targets(&self.seed.rig, &old.clip)?;
            for t in &old.tracks {
                if let Some(TrackTarget::Bone(bone)) = targets.get(t.index) {
                    ordinary.insert(*bone);
                }
            }
        }
        info!("Diagnostic input phase {phase:?}, source {}", template.key);
        self.seed.clip = template.clip;
        self.seed.tracks = template.tracks;
        self.seed.speed = template.speed;
        self.seed.root = Some(new_root);
        self.seed.actor_motion = Some(ActorMotion {
            tracks: template.actor_tracks,
            entry_gate: 1,
            dispatch_flags: 0,
        });
        self.outgoing_selection_velocity = self.selection_velocity;
        self.seed.transition = if blend { Some(old) } else { None };
        self.ordinary = ordinary;
        if phase != ControlPhase::Walking || self.control_phase != ControlPhase::Walking {
            self.walk_dwell = 0.;
        }
        if phase != ControlPhase::Running || self.control_phase != ControlPhase::Running {
            self.run_age = 0.;
        }
        if phase == ControlPhase::Running && self.control_phase != ControlPhase::Running {
            self.run_from_turn = self.control_phase == ControlPhase::TurnWalk;
        } else if phase != ControlPhase::Running {
            self.run_from_turn = false;
        }
        self.control_phase = phase;
        if matches!(phase, ControlPhase::TurningA | ControlPhase::TurningB
            | ControlPhase::StandingNegative | ControlPhase::StandingPositive) {
            self.pending_moving_turn = false;
        }
        if matches!(phase, ControlPhase::StandingNegative | ControlPhase::StandingPositive) {
            // Current bank116/117 phase0: native flags136, primary enabled.
            // Sa2D clears1198 for these source-owned turn phases.
            self.slow_heading_response = 0.;
        }
        if phase == ControlPhase::Idle {
            self.idle_action_time = self.scene_time - controls.stationary_context.time_origin;
        }
        self.clip_cycles = 0;
        self.action_phase = 0;
        self.action_repeat = 0;
        self.queued_action = None;
        Ok(())
    }
    pub(super) fn request_move(&mut self, moving: bool) -> Result<(), &'static str> {
        self.move_requested = moving;
        if self.seed.controls.is_none() {
            return Ok(());
        }
        // Native geometry with bounded preview eligibility. VM cooldown/mode
        // and pre-blend pending dispatch remain outside this adapter.
        if moving && self.pending_standing_turn.is_none() && !self.pending_moving_turn
            && matches!(self.control_phase, ControlPhase::Idle | ControlPhase::WaitingIdle
                | ControlPhase::Slow | ControlPhase::Restart | ControlPhase::Starting | ControlPhase::Walking)
            && self
                .seed
                .controls
                .as_ref()
                .is_some_and(|c| c.standing_turn.is_some())
        {
            let world = self.pose.nodes[&self.seed.actor_address].world;
            let forward = Vec3::new(-world[4], -world[5], -world[6]);
            let right = Vec3::new(world[0], world[1], world[2]).normalize_or_zero();
            // Native geometry and >2.5 branch threshold; velocity/mode
            // eligibility are approximate until runtime10D4 is reconstructed.
            let moving_candidate = matches!(self.control_phase,
                ControlPhase::Slow | ControlPhase::Starting | ControlPhase::Walking)
                && self.selection_velocity.length() > 2.5
                && self.seed.controls.as_ref().is_some_and(|c| c.turn.is_some());
            if let Some(action) = crate::input::turn_predicate::geometry_select(
                self.input_strength, self.control_direction.to_array(), forward.to_array(),
                right.to_array(), if moving_candidate { 79 } else { 116 }) {
                self.last_turn_candidate_speed = Some(self.selection_velocity.length());
                if action == 79 {
                    self.pending_moving_turn = true;
                } else {
                let phase = if action == 116 {
                    ControlPhase::StandingNegative
                } else {
                    ControlPhase::StandingPositive
                };
                // Capture a qualified angle before an incoming blend ends;
                // freezing an initial angle before the gate opens was wrong.
                self.pending_standing_turn.get_or_insert(phase);
                }
            }
        }
        if self.seed.transition.as_ref().is_some_and(|t| t.active) {
            return Ok(());
        }
        if self.pending_moving_turn {
            self.select_at_duration(ControlPhase::TurningA, true, None, Some(6))?;
            return Ok(());
        }
        if let Some(phase) = self.pending_standing_turn.take() {
            self.select_at_duration(phase, true, None, Some(6))?;
            return Ok(());
        }
        if matches!(
            self.control_phase,
            ControlPhase::StandingNegative | ControlPhase::StandingPositive
        ) {
            // Native A/D pulses (215901) retain 116/117 after input release.
            // Finish the single-pass source rotation; move_requested chooses
            // Slow or Idle at its boundary. VM predicate remains unresolved.
            return Ok(());
        }
        if !moving
            && matches!(
                self.control_phase,
                ControlPhase::Slow
                    | ControlPhase::Restart
                    | ControlPhase::RestartSecond
                    | ControlPhase::Starting
                    | ControlPhase::Walking
                    | ControlPhase::Running
            )
        {
            let controls = self.seed.controls.as_ref().unwrap();
            let tables = if self.control_phase == ControlPhase::Running {
                &controls.run.as_ref().ok_or("Missing run bank")?.transitions
            } else if matches!(
                self.control_phase,
                ControlPhase::Restart | ControlPhase::RestartSecond
            ) {
                &controls.restart_transitions
            } else if self.control_phase == ControlPhase::Slow {
                &controls.slow_transitions
            } else if self.control_phase == ControlPhase::Starting {
                &controls.start_transitions
            } else {
                &controls.walk_transitions
            };
            let rule = crate::animation::action_transition::lookup(tables, self.action_phase, 0)
                // 1409ad760: absent outgoing entry permits incoming phase0
                // self row when bit0x10 is set and the requested action differs.
                .or_else(|| {
                    crate::animation::action_transition::lookup(&controls.idle_transitions, 0, 0)
                        .filter(|r| r.flags & 0x10 != 0)
                })
                .ok_or("Release request has no supported transition rule")?;
            if rule.flags & !0x10 != 0 {
                return Err("Release rule requires unsupported action flags");
            }
            let next = match rule.target {
                0 => ControlPhase::Idle,
                54 => ControlPhase::StoppingA,
                53 => ControlPhase::RunStoppingA,
                _ => return Err("Release target missing from diagnostic clip bank"),
            };
            self.select_at_duration(next, true, None, Some(rule.duration_byte))?;
            self.queued_action = (rule.target != 0).then_some(0);
            return Ok(());
        }
        let next = match (moving, self.control_phase) {
            (true, ControlPhase::Idle | ControlPhase::WaitingIdle) => {
                let controls = self.seed.controls.as_ref().unwrap();
                let action = if self.joy_value >= 0.35 {
                    crate::input::animation_selector::moving_action(
                        self.joy_value,
                        &controls.preview_selector_actions(self.run_requested),
                        false,
                        false,
                        false,
                    )?
                    .ok_or("Unexpected idle input gate")?
                } else {
                    1
                };
                let outgoing = if self.control_phase == ControlPhase::Idle {
                    &controls.idle_transitions
                } else {
                    &controls.waiting_transitions
                };
                let incoming = match action {
                    1 => &controls.slow_transitions,
                    3 => &controls.walk_transitions,
                    4 => &controls.start_transitions,
                    _ => return Err("Idle moving target outside diagnostic bank"),
                };
                let rule = crate::animation::action_transition::lookup(outgoing, 0, action)
                    .or_else(|| {
                        crate::animation::action_transition::lookup(incoming, 0, action)
                            .filter(|r| r.flags & 0x10 != 0)
                    })
                    .ok_or("Missing idle moving transition")?;
                if !matches!(rule.flags, 0 | 0x10) {
                    return Err("Unsupported idle moving flags");
                }
                let next = match rule.target {
                    1 => ControlPhase::Slow,
                    51 => ControlPhase::Restart,
                    3 => ControlPhase::Walking,
                    4 => ControlPhase::Starting,
                    _ => return Err("Unsupported idle moving target"),
                };
                self.select_at_duration(next, true, None, Some(rule.duration_byte))?;
                self.queued_action = (rule.target as i32 != action).then_some(action);
                return Ok(());
            }
            // Stop re-entry waits for the sampled scalar and old blend in step.
            (true, ControlPhase::StoppingA | ControlPhase::StoppingB) => None,
            _ => None,
        };
        if let Some(next) = next {
            self.select(next, true)?;
        }
        Ok(())
    }
}
