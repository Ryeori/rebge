//! Channel preparation, root publication, and interrupted pose blending.
use super::*;

impl Player {
    pub(super) fn prepare_channels(
        &mut self,
        delta: f32,
        controller_terminal: bool,
        outgoing_delta: Option<f32>,
    ) -> Result<f32, &'static str> {
        let mut remaining = 0.;
        let mut motion_result = None;
        let mut base = RuntimePose {
            bone_addresses: self.pose.bone_addresses.clone(),
            nodes: self.pose.nodes.clone(),
        };
        if let (Some(motion), Some(root)) = (&self.seed.actor_motion, &self.seed.root) {
            let node = &self.pose.nodes[&self.seed.actor_address];
            let actor = crate::animation::reference_entry::ActorReferenceStorage {
                gao_flags: node.flags,
                world: crate::animation::reference_entry::MatrixStorage {
                    values: node.world,
                    flags: node.world_flags,
                },
                linked_local: None,
                reference: Some(crate::animation::reference_entry::MatrixStorage {
                    values: root.reference,
                    flags: root.reference_flags,
                }),
            };
            let inputs: Vec<_> = motion
                .tracks
                .iter()
                .map(|t| crate::animation::root_batch::TrackInput {
                    source: &self.seed.clip.tracks[t.index],
                    clock: &t.clock,
                    state: t.state,
                })
                .collect();
            let result = if controller_terminal {
                // Qualified action banks use track0 as the controlling actor-root track.
                if motion.tracks.first().map(|t| t.index) != Some(0) {
                    return Err("Action bank controlling track is not first");
                }
                let pass = crate::animation::root_batch::advance_once(
                    &inputs,
                    &actor,
                    delta,
                    self.seed.speed,
                    motion.entry_gate,
                    motion.dispatch_flags,
                )?;
                remaining = pass.remaining;
                pass.batch
            } else {
                crate::animation::root_batch::advance(
                    &inputs,
                    &actor,
                    delta,
                    self.seed.speed,
                    motion.entry_gate,
                    motion.dispatch_flags,
                )?
            };
            base = base.with_actor_root(self.seed.actor_address, &result.actor)?;
            motion_result = Some(result);
        }
        let selected: Vec<_> = self
            .seed
            .tracks
            .iter()
            .map(|t| playback::SelectedTrack {
                index: t.index,
                clock: &t.clock,
                state: t.state,
            })
            .collect();
        let primary = playback::sample(
            &self.seed.rig,
            &self.seed.binding,
            &self.seed.clip,
            &selected,
            delta,
            self.seed.speed,
            controller_terminal,
        )?;
        let mut prepared = None;
        let mut outgoing_clocks = None;
        let mut transition_step = None;
        if let Some(outgoing) = &self.seed.transition {
            if outgoing.active {
                let step = if let Some(outgoing_delta) = outgoing_delta {
                    crate::animation::transition::advance_transition(
                        true,
                        outgoing.duration_byte,
                        outgoing.elapsed_u16,
                        outgoing_delta,
                    )?
                } else {
                    crate::animation::transition::TransitionStep {
                        active: outgoing.active,
                        elapsed_u16: outgoing.elapsed_u16,
                        downstream_ratio: Some(outgoing.ratio),
                    }
                };
                if let Some(ratio) = step.downstream_ratio {
                    let selected: Vec<_> = outgoing
                        .tracks
                        .iter()
                        .map(|t| playback::SelectedTrack {
                            index: t.index,
                            clock: &t.clock,
                            state: t.state,
                        })
                        .collect();
                    let sampled = playback::sample(
                        &self.seed.rig,
                        &self.seed.binding,
                        &outgoing.clip,
                        &selected,
                        outgoing_delta.unwrap_or(0.),
                        outgoing.speed,
                        false,
                    )?;
                    prepared = Some(crate::animation::pose_transition::apply(
                        &base,
                        &self.seed.rig,
                        &sampled.locals,
                        &primary.locals,
                        &self.ordinary,
                        ratio,
                    )?);
                    if let Some(snapshot) = &outgoing.interrupted_pose {
                        let primary_pose = base.with_plain_channel_writes(
                            &self.seed.rig,
                            &primary.locals,
                            &self.ordinary,
                        )?;
                        prepared = Some(blend_interrupted_pose(
                            &primary_pose,
                            snapshot,
                            &self.ordinary,
                            ratio,
                        )?);
                    }
                    outgoing_clocks = Some(sampled.clocks);
                }
                transition_step = Some(step);
            }
        }
        if prepared.is_none() {
            prepared = Some(base.with_plain_channel_writes(
                &self.seed.rig,
                &primary.locals,
                &self.ordinary,
            )?);
        }
        let mut primary_root_clocks = None;
        let mut outgoing_root_clocks = None;
        if let Some(root) = &self.seed.root {
            let root_bone = self
                .seed
                .rig
                .objects
                .iter()
                .position(|b| b.slot == Some(0))
                .ok_or("Missing root bone")?;
            let selected: Vec<_> = root
                .tracks
                .iter()
                .map(|t| playback::SelectedTrack {
                    index: t.index,
                    clock: &t.clock,
                    state: t.state,
                })
                .collect();
            let sampled = playback::sample(
                &self.seed.rig,
                &self.seed.binding,
                &self.seed.clip,
                &selected,
                delta,
                self.seed.speed,
                controller_terminal,
            )?;
            let actor = &base.nodes[&self.seed.actor_address];
            let reference = motion_result
                .as_ref()
                .and_then(|r| r.actor.reference)
                .unwrap_or(crate::animation::reference_entry::MatrixStorage {
                    values: root.reference,
                    flags: root.reference_flags,
                });
            let context = crate::animation::runtime_pose::RootReferenceContext {
                actor_address: self.seed.actor_address,
                actor_matrix: actor.world,
                actor_matrix_flags: actor.world_flags,
                reference_matrix: reference.values,
                reference_flags: reference.flags,
                height: root.height,
                add_height: root.add_height,
            };
            let mut outgoing_root = None;
            if let (Some(outgoing), Some(step)) = (&self.seed.transition, &transition_step) {
                if let (Some(root), Some(ratio)) = (&outgoing.root, step.downstream_ratio) {
                    let selected: Vec<_> = root
                        .tracks
                        .iter()
                        .map(|t| playback::SelectedTrack {
                            index: t.index,
                            clock: &t.clock,
                            state: t.state,
                        })
                        .collect();
                    let old = playback::sample(
                        &self.seed.rig,
                        &self.seed.binding,
                        &outgoing.clip,
                        &selected,
                        // Preview policy: retain the outgoing root sample during
                        // fast-turn entry. Its loop otherwise wraps position
                        // without the outgoing actor-reference continuation.
                        if self.control_phase == ControlPhase::TurningA || outgoing.freeze_root {
                            0.
                        } else {
                            outgoing_delta.unwrap_or(0.)
                        },
                        outgoing.speed,
                        false,
                    )?;
                    let old_context = crate::animation::runtime_pose::RootReferenceContext {
                        actor_address: self.seed.actor_address,
                        actor_matrix: actor.world,
                        actor_matrix_flags: actor.world_flags,
                        reference_matrix: root.reference,
                        reference_flags: root.reference_flags,
                        height: root.height,
                        add_height: root.add_height,
                    };
                    outgoing_root =
                        Some((old.locals.writes[root_bone].clone(), old_context, ratio));
                    outgoing_root_clocks = Some(old.clocks);
                }
            }
            prepared = Some(crate::animation::root_transition::apply(
                prepared.as_ref().unwrap(),
                &self.seed.rig,
                root_bone,
                &sampled.locals.writes[root_bone],
                &context,
                outgoing_root
                    .as_ref()
                    .filter(|_| {
                        self.seed
                            .transition
                            .as_ref()
                            .is_none_or(|t| t.interrupted_pose.is_none())
                    })
                    .map(
                        |(write, context, ratio)| crate::animation::root_transition::Outgoing {
                            write,
                            context,
                            ratio: *ratio,
                        },
                    ),
            )?);
            if let Some((snapshot, ratio)) = self.seed.transition.as_ref().and_then(|t| {
                Some((
                    t.interrupted_pose.as_ref()?,
                    transition_step.as_ref()?.downstream_ratio?,
                ))
            }) {
                prepared = Some(blend_interrupted_pose(
                    prepared.as_ref().unwrap(),
                    snapshot,
                    &BTreeSet::from([root_bone]),
                    ratio,
                )?);
            }
            primary_root_clocks = Some(sampled.clocks);
        }
        for t in &mut self.seed.tracks {
            t.state = primary.clocks.states[t.index].ok_or("Missing playback output clock")?;
        }
        if let (Some(root), Some(clocks)) = (&mut self.seed.root, primary_root_clocks) {
            for t in &mut root.tracks {
                t.state = clocks.states[t.index].ok_or("Missing primary root clock")?;
            }
        }
        if let (Some(motion), Some(result)) = (&mut self.seed.actor_motion, motion_result) {
            self.root_cycles += result.completions;
            self.clip_cycles += result.completions;
            for (t, state) in motion.tracks.iter_mut().zip(result.states) {
                t.state = state;
            }
            if let (Some(root), Some(reference)) = (&mut self.seed.root, result.actor.reference) {
                root.reference = reference.values;
                root.reference_flags = reference.flags;
            }
        }
        if let (Some(outgoing), Some(step)) = (&mut self.seed.transition, transition_step) {
            outgoing.active = step.active;
            outgoing.elapsed_u16 = step.elapsed_u16;
            if let Some(ratio) = step.downstream_ratio {
                outgoing.ratio = ratio;
            }
            if let Some(clocks) = outgoing_clocks {
                for t in &mut outgoing.tracks {
                    t.state = clocks.states[t.index].ok_or("Missing outgoing clock")?;
                }
            }
            if let (Some(root), Some(clocks)) = (&mut outgoing.root, outgoing_root_clocks) {
                for t in &mut root.tracks {
                    t.state = clocks.states[t.index].ok_or("Missing outgoing root clock")?;
                }
            }
        }
        self.pose = prepared.ok_or("Missing prepared channel pose")?;
        Ok(remaining)
    }
}

// Diagnostic adapter only: preserve the composed pose when a blend is interrupted.
pub(super) fn blend_interrupted_pose(
    primary: &RuntimePose,
    snapshot: &BTreeMap<usize, ([f32; 16], u32)>,
    bones: &BTreeSet<usize>,
    ratio: f32,
) -> Result<RuntimePose, &'static str> {
    let mut writes = BTreeMap::new();
    for bone in bones {
        if let Some((old, old_flags)) = snapshot.get(bone) {
            let address = primary.bone_addresses[*bone];
            let (new, new_flags) = primary.nodes[&address]
                .local
                .ok_or("Missing interrupted primary local")?;
            let matrix = crate::animation::pose_blend::blend_local_no_scale(
                *old, *old_flags, new, new_flags, ratio,
            )?;
            writes.insert(*bone, (matrix, (*old_flags | new_flags | 6) & !8));
        }
    }
    primary.with_prepared_locals(&writes)
}

