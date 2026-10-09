//! Per-frame playback clocks and controller progression.
use super::*;

impl Player {
    pub(super) fn step(
        &mut self,
        delta: f32,
        source: &Source,
    ) -> Result<Vec<(usize, Vec<[f32; 3]>)>, &'static str> {
        let actor_before_step = self.pose.nodes[&self.seed.actor_address].world;
        self.scene_time += delta;
        // Preview acceleration policy: preserve a walking stage before sprint,
        // including after a turn. These timings are not native VM parameters.
        if self.move_requested && self.control_phase == ControlPhase::Walking {
            self.walk_dwell += delta;
        }
        self.filtered_direction = crate::input::blend::blend_direction(
            self.filtered_direction,
            // Sally_sa_exec_joynorm_blend1560e4150 consumes Global+14,
            // whose magnitude retains stick strength, rather than unit +38.
            // Camera mapping and ordinary heading response remain adapters.
            self.control_direction * self.input_strength,
            delta,
        );
        if matches!(self.control_phase, ControlPhase::StandingNegative | ControlPhase::StandingPositive) {
            // Native joynorm116/117 resets1E4 to the current actor forward.
            let world = self.pose.nodes[&self.seed.actor_address].world;
            self.filtered_direction = Vec3::new(-world[4], -world[5], -world[6]);
        }
        // Opposite raw input threshold is explicitly a preview policy, not the native VM predicate.
        let world = self.pose.nodes[&self.seed.actor_address].world;
        let forward = Vec3::new(-world[4], -world[5], 0.).normalize_or_zero();
        // Native recordings202444/203116 follow run2 -> stop54/53 -> turn79.
        // The continuous-input trigger below is preview policy: that recording
        // contains an observed zero-input gap between keyboard directions.
        let entered_run_stop = self.control_phase == ControlPhase::Running
            && self.move_requested
            && self.input_strength >= 0.35
            && forward.dot(self.control_direction) < -0.5
            && !self.seed.transition.as_ref().is_some_and(|t| t.active)
            && self
                .seed
                .controls
                .as_ref()
                .is_some_and(|c| c.turn.is_some());
        if entered_run_stop {
            self.request_move(false)?;
            self.move_requested = true;
        }
        if self.pending_moving_turn && !entered_run_stop
            && !self.seed.transition.as_ref().is_some_and(|t| t.active) {
            self.select_at_duration(ControlPhase::TurningA, true, None, Some(6))?;
        }
        let early_stop = matches!(
            self.control_phase,
            ControlPhase::StoppingA | ControlPhase::RunStoppingA
        ) && self
            .seed
            .actor_motion
            .as_ref()
            .and_then(|m| m.tracks.first())
            .is_some_and(|t| t.state.index == 0 && t.state.elapsed < 0.2);
        if early_stop
            && !entered_run_stop
            && self.move_requested
            && self.input_strength >= 0.35
            && self.control_direction != Vec3::ZERO
            && self
                .seed
                .controls
                .as_ref()
                .is_some_and(|c| c.turn.is_some())
            && (early_stop || !self.seed.transition.as_ref().is_some_and(|t| t.active))
        {
            let world = self.pose.nodes[&self.seed.actor_address].world;
            let forward = Vec3::new(-world[4], -world[5], 0.).normalize_or_zero();
            if forward.dot(self.control_direction) < -0.5 {
                self.select_at_duration(ControlPhase::TurningA, true, None, Some(6))?;
            }
        }
        if self.move_requested && self.control_direction != Vec3::ZERO
            && self.pending_standing_turn.is_none()
            && !self.pending_moving_turn
            // Source phases A/B own the half-turn. Exit clips can respond to
            // new input through the approximate preview steering policy.
            && !matches!(self.control_phase, ControlPhase::TurningA | ControlPhase::TurningB | ControlPhase::StandingNegative | ControlPhase::StandingPositive)
        {
            let actor = &self.pose.nodes[&self.seed.actor_address];
            let pivot = actor.world[12..15].try_into().unwrap();
            let angle = if matches!(self.control_phase, ControlPhase::Slow | ControlPhase::Starting) {
                // Qualified native action1/4 uses mode1. Main-AI route runs
                // after animation time-scale flag is cleared. Phase mapping,
                // initial1198 and callback count remain preview adapters.
                let yaw = crate::input::diagnostic_steering::slow_turn(
                    actor.world, self.filtered_direction, self.input_strength,
                    self.slow_heading_response, delta);
                self.slow_heading_response = yaw.updated_response;
                yaw.yaw
            } else {
                crate::input::diagnostic_steering::turn(actor.world, self.filtered_direction, delta)
            };
            if angle != 0. {
                let actor = self.pose.nodes.get_mut(&self.seed.actor_address).unwrap();
                crate::input::diagnostic_steering::rotate(&mut actor.world, pivot, angle);
                actor.world_flags &= !1;
                if let Some(root) = &mut self.seed.root {
                    crate::input::diagnostic_steering::rotate(&mut root.reference, pivot, angle);
                    root.reference_flags &= !1;
                }
                if let Some(root) = self.seed.transition.as_mut().and_then(|t| t.root.as_mut()) {
                    crate::input::diagnostic_steering::rotate(&mut root.reference, pivot, angle);
                    root.reference_flags &= !1;
                }
            }
        }
        let ordinary_turn_exit = self.control_phase == ControlPhase::TurnWalk && !self.run_requested;
        if ordinary_turn_exit {
            // Native004413: action80 binds descriptor64 -> speed60, then
            // stable mode2 snapshots show56, matching quantized stored60.
            // Phase entry/carry retains the source binding below. This adapter
            // covers qualified no-sprint80, not the full VM speed scheduling.
            let stored = self.seed.controls.as_ref().and_then(|c| c.turn.as_ref())
                .ok_or("Missing ordinary turn exit speed source")?.walk.speed;
            self.seed.speed = crate::input::animation_speed::quantize(i32::from(stored));
        }
        let adapter_speed = self.seed.speed;
        if self.control_phase == ControlPhase::Running {
            self.run_age += delta;
            if let Some(run) = self.seed.controls.as_ref().and_then(|c| c.run.as_ref()) {
                self.seed.speed = if self.run_from_turn {
                    // Native205707/210317/210516/210624: exit80 already
                    // accelerates via its source translation, then run2 has
                    // speed56 during incoming blend and61 afterwards.
                    // This bounded adapter does not replace the full VM writer.
                    if self.seed.transition.as_ref().is_some_and(|t| t.active) {
                        56
                    } else {
                        run.clip.speed
                    }
                } else {
                    let ramp = (self.run_age / 0.3).clamp(0., 1.);
                    // Preview ramp starts near the walking root speed and has
                    // zero slope at its endpoints, avoiding the first-frame kick.
                    let ramp = ramp * ramp * (3. - 2. * ramp);
                    (run.clip.speed as f32 * (0.6 + 0.4 * ramp)).round() as u8
                };
            }
        }
        let mut remaining = delta;
        let mut first = true;
        let mut complete = false;
        for _ in 0..64 {
            let boundary = self.seed.controls.is_some()
                && matches!(
                    self.control_phase,
                    ControlPhase::StoppingA
                        | ControlPhase::StoppingB
                        | ControlPhase::Walking
                        | ControlPhase::Running
                        | ControlPhase::Restart
                        | ControlPhase::RestartSecond
                        | ControlPhase::RunStoppingA
                        | ControlPhase::RunStoppingB
                        | ControlPhase::TurningA
                        | ControlPhase::TurningB
                        | ControlPhase::TurnStop
                        | ControlPhase::TurnWalk
                        | ControlPhase::StandingNegative
                        | ControlPhase::StandingPositive
                );
            let cycles_before = self.clip_cycles;
            remaining = self.prepare_channels(remaining, boundary, first.then_some(delta))?;
            first = false;
            if !boundary || self.clip_cycles == cycles_before {
                complete = true;
                break;
            }
            if matches!(
                self.control_phase,
                ControlPhase::StandingNegative | ControlPhase::StandingPositive
            ) {
                // Single-pass source clips; completion dispatch is preview scheduling.
                let next = if self.move_requested {
                    ControlPhase::Slow
                } else {
                    ControlPhase::Idle
                };
                // Native rows 116/117 -> 0 have flags0, duration10 (221038).
                // Hold the visible terminal pose as the outgoing operand.
                if next == ControlPhase::Idle {
                    self.select_at_duration(next, true, None, Some(10))?;
                } else {
                    self.select(next, false)?;
                }
                if remaining == 0. {
                    self.prepare_channels(0., false, None)?;
                    complete = true;
                    break;
                }
                continue;
            }
            if matches!(
                self.control_phase,
                ControlPhase::TurningA
                    | ControlPhase::TurningB
                    | ControlPhase::TurnStop
                    | ControlPhase::TurnWalk
            ) {
                let next = match self.control_phase {
                    ControlPhase::TurningA => {
                        let descriptor = &self
                            .seed
                            .controls
                            .as_ref()
                            .unwrap()
                            .turn
                            .as_ref()
                            .unwrap()
                            .descriptor;
                        let decision =
                            crate::animation::primary_phase::complete(descriptor, 0, 0, false)?;
                        if !matches!(
                            decision.effect,
                            crate::animation::primary_phase::Effect::Bind { phase: 1, .. }
                        ) {
                            return Err("Unexpected reverse phase continuation");
                        }
                        ControlPhase::TurningB
                    }
                    // Native source table79phase1 maps request0→78 and request3→80.
                    // Dispatch at completion is a preview scheduling policy.
                    ControlPhase::TurningB => {
                        if self.move_requested {
                            ControlPhase::TurnWalk
                        } else {
                            ControlPhase::TurnStop
                        }
                    }
                    ControlPhase::TurnWalk => {
                        if self.move_requested && self.run_requested
                            && self.seed.controls.as_ref().unwrap().run.is_some()
                        {
                            ControlPhase::Running
                        } else if self.move_requested {
                            ControlPhase::Walking
                        } else {
                            ControlPhase::Idle
                        }
                    }
                    ControlPhase::TurnStop => {
                        if self.move_requested {
                            ControlPhase::Slow
                        } else {
                            ControlPhase::Idle
                        }
                    }
                    _ => unreachable!(),
                };
                if self.control_phase == ControlPhase::TurnWalk && next == ControlPhase::Running {
                    let rule = crate::animation::action_transition::lookup(
                        &self.seed.controls.as_ref().unwrap().run.as_ref().unwrap().transitions,
                        0, 2,
                    ).ok_or("Missing incoming run rule after turn")?;
                    if rule.target != 2 || rule.flags != 0x10 {
                        return Err("Unsupported incoming run rule after turn");
                    }
                    self.select_at_duration(next, true, None, Some(rule.duration_byte))?;
                    self.seed.speed = 56;
                } else {
                    self.select(next, false)?;
                    if next == ControlPhase::TurnWalk && self.run_requested {
                        self.seed.speed = self.seed.controls.as_ref().unwrap().run
                            .as_ref().ok_or("Missing run clip for turn exit")?.clip.speed;
                    }
                }
                if next == ControlPhase::TurningB {
                    self.action_phase = 1;
                }
                if remaining == 0. {
                    self.prepare_channels(0., false, None)?;
                    complete = true;
                    break;
                }
                continue;
            }
            let running = self.control_phase == ControlPhase::Running;
            let restarting = matches!(
                self.control_phase,
                ControlPhase::Restart | ControlPhase::RestartSecond
            );
            let run_stop = matches!(
                self.control_phase,
                ControlPhase::RunStoppingA | ControlPhase::RunStoppingB
            );
            let walking = self.control_phase == ControlPhase::Walking;
            let descriptor = if restarting {
                self.seed
                    .controls
                    .as_ref()
                    .unwrap()
                    .restart_descriptor
                    .as_ref()
                    .ok_or("Missing restart descriptor")?
            } else if running {
                &self
                    .seed
                    .controls
                    .as_ref()
                    .unwrap()
                    .run
                    .as_ref()
                    .unwrap()
                    .descriptor
            } else if run_stop {
                &self
                    .seed
                    .controls
                    .as_ref()
                    .unwrap()
                    .run
                    .as_ref()
                    .unwrap()
                    .stop_descriptor
            } else if walking {
                &self.seed.controls.as_ref().unwrap().walk_descriptor
            } else {
                &self.seed.controls.as_ref().unwrap().stop_descriptor
            };
            let decision = crate::animation::primary_phase::complete(
                descriptor,
                self.action_phase,
                self.action_repeat,
                self.queued_action.is_some(),
            )?;
            match decision.effect {
                crate::animation::primary_phase::Effect::Repeat => {}
                crate::animation::primary_phase::Effect::Bind { speed, .. } => {
                    let queued = self.queued_action;
                    // Binding a later phase of the same action must not erase
                    // its independent incoming action blend. A remapped Walk3
                    // phase can finish during the longer Slow1 -> Walk3 blend.
                    let continuing_blend = if walking || running {
                        self.seed.transition.take()
                    } else { None };
                    self.select(
                        if restarting {
                            ControlPhase::RestartSecond
                        } else if running {
                            ControlPhase::Running
                        } else if run_stop {
                            ControlPhase::RunStoppingB
                        } else if walking {
                            ControlPhase::Walking
                        } else {
                            ControlPhase::StoppingB
                        },
                        false,
                    )?;
                    if walking || running {
                        self.seed.transition = continuing_blend;
                    }
                    self.queued_action = queued;
                    if let Some(speed) = speed {
                        self.seed.speed = speed;
                    }
                    // Even zero carry needs the new clip's initial channel writes.
                    if remaining == 0. {
                        self.prepare_channels(0., false, None)?;
                    }
                }
                crate::animation::primary_phase::Effect::QueuedAction => {
                    if restarting && self.queued_action == Some(1) {
                        self.select(ControlPhase::Slow, false)?;
                        self.seed.speed = crate::input::animation_speed::source_speed(64);
                        if remaining == 0. {
                            self.prepare_channels(0., false, None)?;
                        }
                    } else {
                        if self.queued_action != Some(0) {
                            return Err("Unsupported queued action");
                        }
                        // 1409bd3b0 clears AA before calling 1409ad760. The pending
                        // record prevents incoming self-row fallback, so no new blend.
                        let idle_speed = self
                            .seed
                            .controls
                            .as_ref()
                            .unwrap()
                            .idle_descriptor
                            .phases
                            .first()
                            .ok_or("Missing idle descriptor")?
                            .speed_source_byte;
                        self.select(ControlPhase::Idle, false)?;
                        self.seed.speed = crate::input::animation_speed::source_speed(idle_speed);
                        if remaining == 0. {
                            self.prepare_channels(0., false, None)?;
                        }
                    }
                }
                _ => return Err("Unexpected diagnostic action completion"),
            }
            if decision.effect != crate::animation::primary_phase::Effect::QueuedAction {
                self.action_phase = decision.phase;
                self.action_repeat = decision.repeat;
            }
            if remaining == 0. {
                complete = true;
                break;
            }
        }
        // The adapter represents the observed per-frame VM speed overwrite.
        // Sally's writer is ported separately; its persistent inputs and ordering
        // are not integrated here. Phase speed only controls this frame's carry.
        self.seed.speed = if self.control_phase == ControlPhase::Running && self.run_from_turn {
            if self.seed.transition.as_ref().is_some_and(|t| t.active) { 56 } else { 61 }
        } else if self.control_phase == ControlPhase::TurnWalk && self.run_requested {
            61
        } else if ordinary_turn_exit {
            // Keep56 while80 remains active; preserve a newly bound phase's
            // own speed on completion instead of leaking56 into Walking3.
            self.seed.speed
        } else {
            adapter_speed
        };
        if !complete {
            return Err("Diagnostic phase carry exceeds bound");
        }
        if self.move_requested
            && self.joy_value >= 0.35
            && !self.seed.transition.as_ref().is_some_and(|t| t.active)
        {
            if matches!(
                self.control_phase,
                ControlPhase::StoppingA
                    | ControlPhase::StoppingB
                    | ControlPhase::RunStoppingA
                    | ControlPhase::RunStoppingB
            ) {
                let controls = self.seed.controls.as_ref().ok_or("Missing controls")?;
                let action =
                    if self.run_requested && controls.run.is_some() && self.walk_dwell >= 0.2 {
                        2
                    } else {
                        crate::input::animation_selector::moving_action(
                            self.joy_value,
                            &controls.preview_selector_actions(self.run_requested),
                            false,
                            false,
                            false,
                        )?
                        .ok_or("Unexpected blocked stop re-entry")?
                    };
                let stop_tables = if matches!(
                    self.control_phase,
                    ControlPhase::RunStoppingA | ControlPhase::RunStoppingB
                ) {
                    &controls.run.as_ref().unwrap().stop_transitions
                } else {
                    &controls.stop_transitions
                };
                let rule = crate::animation::action_transition::lookup(
                    stop_tables,
                    self.action_phase,
                    action,
                )
                .ok_or("Missing stop re-entry rule")?;
                if rule.flags != 0 {
                    return Err("Unsupported stop re-entry flags");
                }
                let next = match rule.target {
                    1 => ControlPhase::Slow,
                    2 => ControlPhase::Running,
                    51 => ControlPhase::Restart,
                    3 => ControlPhase::Walking,
                    4 => ControlPhase::Starting,
                    _ => return Err("Unsupported stop re-entry target"),
                };
                self.select_at_duration(next, true, None, Some(rule.duration_byte))?;
                self.queued_action = (rule.target as i32 != action).then_some(action);
                self.prepare_channels(0., false, None)?;
            } else if matches!(
                self.control_phase,
                ControlPhase::Idle | ControlPhase::WaitingIdle
            ) {
                // A held re-entry can survive stop completion before the gate opens.
                self.request_move(true)?;
                self.prepare_channels(0., false, None)?;
            }
        }
        if !self.move_requested
            && matches!(
                self.control_phase,
                ControlPhase::Slow
                    | ControlPhase::Restart
                    | ControlPhase::RestartSecond
                    | ControlPhase::Starting
                    | ControlPhase::Walking
                    | ControlPhase::Running
            )
            && !self.seed.transition.as_ref().is_some_and(|t| t.active)
        {
            self.request_move(false)?;
            self.prepare_channels(0., false, None)?;
        }
        if self.seed.controls.is_some()
            && !self.move_requested
            && self.joy_value < 0.35
            && self.control_phase == ControlPhase::Idle
        {
            let controls = self
                .seed
                .controls
                .as_ref()
                .ok_or("Missing stationary context")?;
            let context = &controls.stationary_context;
            let decision = crate::input::animation_selector::stationary_action(
                &crate::input::animation_selector::StationaryInputs {
                    mode: context.mode,
                    pending: context.pending,
                    last_action: 0,
                    selected_action: context.selected_action,
                    scene_time: self.scene_time,
                    time_origin: context.time_origin,
                    interaction_time: context.interaction_time,
                    action_time: self.idle_action_time,
                    idle: controls.selector_actions[0],
                    waiting: controls.selector_actions[11],
                    primary_disabled: false,
                    exception: false,
                    blend_active: self.seed.transition.as_ref().is_some_and(|t| t.active),
                },
            );
            if let Some(requested) = decision.requested {
                if requested == 123 {
                    let rule = crate::animation::action_transition::lookup(
                        &controls.waiting_transitions,
                        0,
                        123,
                    )
                    .ok_or("Missing incoming waiting row")?;
                    if rule.target != 123 || rule.flags != 0x10 || decision.consume_pending {
                        return Err("Unsupported stationary waiting rule");
                    }
                    self.select_at_duration(
                        ControlPhase::WaitingIdle,
                        true,
                        None,
                        Some(rule.duration_byte),
                    )?;
                    self.prepare_channels(0., false, None)?;
                } else if requested != 0 {
                    return Err("Stationary request outside diagnostic bank");
                }
            }
        }
        if let Some(controls) = &self.seed.controls {
            let active = self.seed.transition.as_ref().is_some_and(|t| t.active);
            if matches!(
                self.control_phase,
                ControlPhase::Slow
                    | ControlPhase::Restart
                    | ControlPhase::RestartSecond
                    | ControlPhase::Starting
                    | ControlPhase::Running
                    | ControlPhase::Walking
            ) {
                if self.move_requested && self.joy_value >= 0.35 {
                    let mut action = if self.run_requested
                        && controls.run.is_some()
                        && (self.control_phase == ControlPhase::Running
                            || (self.control_phase == ControlPhase::Walking
                                && self.walk_dwell >= 0.2))
                    {
                        (!active).then_some(2)
                    } else {
                        crate::input::animation_selector::moving_action(
                            self.joy_value,
                            &controls.preview_selector_actions(self.run_requested),
                            active,
                            false,
                            false,
                        )?
                    };
                    // A held sprint still reaches running with partial stick input;
                    // retain its walking stage rather than falling back to Slow
                    // before the dwell can finish.
                    if self.run_requested
                        && controls.run.is_some()
                        && !active
                        && self.input_strength < 0.925
                        && matches!(
                            self.control_phase,
                            ControlPhase::Slow | ControlPhase::Starting | ControlPhase::Walking
                        )
                    {
                        action = Some(
                            if self.control_phase == ControlPhase::Walking && self.walk_dwell >= 0.2
                            {
                                2
                            } else {
                                3
                            },
                        );
                    }
                    // Preview policy: a falling analog magnitude must not briefly
                    // enter the acceleration/start clip while crossing selector bin4.
                    if action == Some(4)
                        && self.input_strength < self.joy_value
                        && matches!(
                            self.control_phase,
                            ControlPhase::Walking | ControlPhase::Running
                        )
                    {
                        action = Some(3);
                    }
                    if let Some(action @ (1 | 2 | 3 | 4)) = action
                        && !(action == 4 && self.control_phase == ControlPhase::Starting)
                        && !(action == 2 && self.control_phase == ControlPhase::Running)
                        && !(action == 1 && self.control_phase == ControlPhase::Slow)
                        && !(action == 3 && self.control_phase == ControlPhase::Walking)
                        && !(action == 1
                            && matches!(
                                self.control_phase,
                                ControlPhase::Restart | ControlPhase::RestartSecond
                            ))
                    {
                        let next = if action == 1 {
                            ControlPhase::Slow
                        } else if action == 2 {
                            ControlPhase::Running
                        } else if action == 3 {
                            ControlPhase::Walking
                        } else {
                            ControlPhase::Starting
                        };
                        let tables = if self.control_phase == ControlPhase::Running {
                            &controls.run.as_ref().unwrap().transitions
                        } else if self.control_phase == ControlPhase::Walking {
                            &controls.walk_transitions
                        } else if matches!(
                            self.control_phase,
                            ControlPhase::Restart | ControlPhase::RestartSecond
                        ) {
                            &controls.restart_transitions
                        } else if self.control_phase == ControlPhase::Slow {
                            &controls.slow_transitions
                        } else {
                            &controls.start_transitions
                        };
                        let rule = crate::animation::action_transition::lookup(
                            tables,
                            self.action_phase,
                            action,
                        )
                        .or_else(|| {
                            let incoming = if action == 1 {
                                &controls.slow_transitions
                            } else if action == 2 {
                                &controls.run.as_ref().unwrap().transitions
                            } else if action == 3 {
                                &controls.walk_transitions
                            } else {
                                &controls.start_transitions
                            };
                            crate::animation::action_transition::lookup(incoming, 0, action)
                                .filter(|r| r.flags & 0x10 != 0)
                        })
                        .ok_or("Missing moving action transition")?;
                        if rule.target as i32 != action || !matches!(rule.flags, 1 | 0x10) {
                            return Err("Unsupported moving transition rule");
                        }
                        let motion = self
                            .seed
                            .actor_motion
                            .as_ref()
                            .ok_or("Missing action progress track")?;
                        let t = motion
                            .tracks
                            .first()
                            .ok_or("Missing controlling action track")?;
                        let (elapsed, duration) =
                            crate::animation::action_progress::progress(&t.clock, t.state)?;
                        let target = (if action == 1 {
                            &controls.slow
                        } else if action == 2 {
                            &controls.run.as_ref().unwrap().clip
                        } else if action == 3 {
                            &controls.walk
                        } else {
                            &controls.start
                        })
                        .actor_tracks
                        .first()
                        .ok_or("Missing target action track")?;
                        let (_, target_duration) = crate::animation::action_progress::progress(
                            &target.clock,
                            target.state,
                        )?;
                        let seconds = crate::animation::action_progress::remap(
                            elapsed,
                            duration,
                            target_duration,
                            1,
                        )?;
                        // The caller timing still belongs to the diagnostic adapter.
                        // Seek all new channels before refreshing the actor reference.
                        self.select_at_duration(
                            next,
                            true,
                            (rule.flags == 1).then_some(seconds),
                            Some(rule.duration_byte),
                        )?;
                        self.prepare_channels(0., false, None)?;
                    }
                }
            }
            self.joy_value = crate::input::animation_selector::joy_norm(
                self.joy_value,
                if self.move_requested {
                    self.input_strength
                } else {
                    0.
                },
                delta,
                true,
                false,
            )?;
        }
        let no_ordinary = BTreeSet::new();
        let result = frame::evaluate(
            &self.pose,
            frame::Inputs {
                rig: &self.seed.rig,
                actor_address: self.seed.actor_address,
                actor: None,
                local_pose: None,
                ordinary_bones: &no_ordinary,
                root: None,
                modifiers: &self.records,
                modifier_requests: &self.seed.modifier_requests,
                delta,
                normalize_modifier_publication: false,
                palette_bones: &self.seed.palette_bones,
            },
        )?;
        let mut output = Vec::new();
        let mut projected_uvs = Vec::new();
        for (index, batch) in source.scene.batches.iter().enumerate() {
            if let Some(data) = &batch.deformation {
                let vertices = crate::animation::skin::deform(data, &result.palette)?;
                if vertices.len() != batch.vertices.len() / 5 {
                    return Err("Deformed mesh vertex count mismatch");
                }
                if let Some(projection) = &batch.uv_projection {
                    projected_uvs.push((
                        index,
                        crate::animation::material_uv::project(
                            projection,
                            &vertices,
                            &result.palette,
                        )?,
                    ));
                }
                output.push((
                    index,
                    vertices.into_iter().map(|p| jade_to_bevy(&p)).collect(),
                ));
            }
        }
        self.pose = result.cycle.finalized.runtime;
        if delta > 0. {
            let actor = self.pose.nodes[&self.seed.actor_address].world;
            let velocity = Vec3::new((actor[12] - actor_before_step[12]) / delta,
                (actor[13] - actor_before_step[13]) / delta, 0.);
            if velocity.is_finite() {
                self.selection_velocity = if let Some(blend) = self.seed.transition.as_ref().filter(|t| t.active) {
                    // Missing outgoing actor-root publication: approximate its
                    // speed contribution only for next-frame turn selection.
                    self.outgoing_selection_velocity * (1. - blend.ratio) + velocity * blend.ratio
                } else { velocity };
            } else {
                self.selection_velocity = Vec3::ZERO;
            }
        }
        self.projected_uvs = projected_uvs;
        self.records = result.cycle.records;
        Ok(output)
    }
}
