//! Source bone indices mapped to explicit runtime nodes, without importing
//! source flags as clone flags. Prepared writes must already resolve root
//! references, channel flags and dynamic reparenting.
use super::{
    hierarchy::Node, local_pose::SampledLocalPose, skeleton::Skeleton,
    world_pose::compose_world_pose,
};
use std::collections::{BTreeMap, BTreeSet};

pub struct RootReferenceContext {
    pub actor_address: u64,
    pub actor_matrix: [f32; 16],
    pub actor_matrix_flags: u32,
    pub reference_matrix: [f32; 16],
    pub reference_flags: u32,
    pub height: f32,
    pub add_height: bool,
}

pub struct RuntimePose {
    pub bone_addresses: Vec<u64>,
    pub nodes: BTreeMap<u64, Node>,
}

pub struct FinalizedPose {
    pub runtime: RuntimePose,
    /// Keep published worlds after local restoration; recomposition differs.
    pub published_worlds: BTreeMap<u64, ([f32; 16], u32)>,
    pub modifier_states: BTreeMap<usize, super::modifier24::State>,
}

impl FinalizedPose {
    pub fn actor_palette(
        &self,
        actor_address: u64,
        ordered_bones: &[usize],
    ) -> Result<Vec<([f32; 16], u32)>, &'static str> {
        palette_from_worlds(
            &self.runtime.bone_addresses,
            &self.published_worlds,
            actor_address,
            ordered_bones,
        )
    }
}

fn palette_from_worlds(
    addresses: &[u64],
    worlds: &BTreeMap<u64, ([f32; 16], u32)>,
    actor_address: u64,
    bones: &[usize],
) -> Result<Vec<([f32; 16], u32)>, &'static str> {
    let (actor, actor_flags) = worlds.get(&actor_address).ok_or("Missing palette actor")?;
    bones
        .iter()
        .map(|bone| {
            let address = addresses.get(*bone).ok_or("Missing palette bone binding")?;
            let (world, flags) = worlds.get(address).ok_or("Missing palette bone world")?;
            super::skin_palette::palette_matrix(*actor, *actor_flags, *world, *flags)
        })
        .collect()
}

impl RuntimePose {
    /// Apply the evaluated correction before local restoration. Finalizer uses
    /// the saved state, while its separate publication retains the writer world.
    pub fn with_linked_modifier_evaluation(
        &self,
        bone: usize,
        evaluation: &super::modifier24::LinkedEvaluation,
    ) -> Result<Self, &'static str> {
        self.with_prepared_locals(&BTreeMap::from([(
            bone,
            (
                evaluation.corrected_local.values,
                evaluation.corrected_local.flags,
            ),
        )]))
    }
    /// Finalize explicitly supplied linked modifier nodes. World writer output
    /// is an input, not inferred from lag state or restored local matrices.
    /// Call only after the required nominal/procedural world stages.
    pub fn finalize_linked_modifiers(
        &self,
        publications: &BTreeMap<usize, super::modifier24::LinkedPublication>,
    ) -> Result<FinalizedPose, &'static str> {
        let mut worlds = self.worlds()?;
        let mut nodes = self.nodes.clone();
        let mut states = BTreeMap::new();
        let active_addresses: BTreeSet<_> = publications
            .iter()
            .filter(|(_, p)| p.processed_list_member)
            .map(|(bone, _)| {
                self.bone_addresses
                    .get(*bone)
                    .copied()
                    .ok_or("Missing modifier bone")
            })
            .collect::<Result<_, _>>()?;
        for (bone, publication) in publications {
            let address = *self
                .bone_addresses
                .get(*bone)
                .ok_or("Missing modifier bone")?;
            let node = nodes
                .get_mut(&address)
                .ok_or("Missing modifier runtime node")?;
            if node.flags & 0x400000 == 0 || node.local.is_none() {
                return Err("Direct modifier finalizer has different world restoration semantics");
            }
            let Some(finalized) =
                super::modifier24::finalize(&publication.state, publication.processed_list_member)
            else {
                continue;
            };
            if self.nodes.iter().any(|(child, n)| {
                n.flags & 0x400000 != 0
                    && n.parent == Some(address)
                    && !active_addresses.contains(child)
            }) {
                return Err("Modifier parent requires explicit child world publication");
            }
            if publication.published_world.flags & 8 != 0
                || publication
                    .published_world
                    .values
                    .iter()
                    .any(|v| !v.is_finite())
                || finalized.restored_local.flags & 8 != 0
                || finalized
                    .restored_local
                    .values
                    .iter()
                    .any(|v| !v.is_finite())
            {
                return Err("Nonfinite or scaled modifier publication unsupported");
            }
            node.local = Some((
                finalized.restored_local.values,
                finalized.restored_local.flags,
            ));
            node.world = publication.published_world.values;
            node.world_flags = publication.published_world.flags;
            worlds.insert(address, (node.world, node.world_flags));
            states.insert(*bone, finalized.state);
        }
        Ok(FinalizedPose {
            runtime: Self {
                bone_addresses: self.bone_addresses.clone(),
                nodes,
            },
            published_worlds: worlds,
            modifier_states: states,
        })
    }
    /// Attach an explicit direct actor root result. Reference storage remains
    /// owned by the root/controller state; this pose contains transform nodes.
    /// Recompose worlds from linked locals instead of trusting cached child worlds.
    pub fn with_actor_root(
        &self,
        actor_address: u64,
        actor: &super::reference_entry::ActorReferenceStorage,
    ) -> Result<Self, &'static str> {
        let prior = self
            .nodes
            .get(&actor_address)
            .ok_or("Missing runtime actor node")?;
        if (prior.flags | actor.gao_flags) & 0x400000 != 0 {
            return Err("Linked actor root requires explicit parent composition");
        }
        if prior.flags & !0x4000000 != actor.gao_flags & !0x4000000 {
            return Err("Actor runtime flags differ beyond reference allocation bit");
        }
        if actor.world.flags & 8 != 0 || actor.world.values.iter().any(|v| !v.is_finite()) {
            return Err("Nonfinite or scaled actor root unsupported");
        }
        let mut nodes = self.nodes.clone();
        let destination = nodes.get_mut(&actor_address).unwrap();
        destination.world = actor.world.values;
        destination.world_flags = actor.world.flags;
        destination.flags = actor.gao_flags;
        compose_world_pose(&nodes)?;
        Ok(Self {
            bone_addresses: self.bone_addresses.clone(),
            nodes,
        })
    }

    pub fn with_root_execution(
        &self,
        actor_address: u64,
        execution: &super::root_pipeline::Execution,
    ) -> Result<Self, &'static str> {
        self.with_actor_root(actor_address, &execution.actor)
    }

    /// Palette entries in caller-supplied bone order. The caller must apply
    /// required procedural locals before requesting the native final palette.
    /// No bind transforms, hidden bone selection or vertex deformation here.
    pub fn actor_palette(
        &self,
        actor_address: u64,
        ordered_bones: &[usize],
    ) -> Result<Vec<([f32; 16], u32)>, &'static str> {
        let worlds = self.worlds()?;
        palette_from_worlds(&self.bone_addresses, &worlds, actor_address, ordered_bones)
    }

    /// Ordinary slot0 linked-to-actor path; reference source is supplied by
    /// caller. Dynamic reparent and primary/transition choice are not inferred.
    pub fn with_reference_root_write(
        &self,
        rig: &Skeleton,
        bone: usize,
        write: &super::local_pose::LocalWrite,
        context: &RootReferenceContext,
    ) -> Result<Self, &'static str> {
        if rig.objects.get(bone).and_then(|b| b.slot) != Some(0) {
            return Err("Expected actor-root animation slot0");
        }
        let address = *self
            .bone_addresses
            .get(bone)
            .ok_or("Missing root binding")?;
        let node = self
            .nodes
            .get(&address)
            .ok_or("Missing root runtime node")?;
        if node.parent != Some(context.actor_address) {
            return Err("Root parent differs from explicit actor context");
        }
        let (mut local, mut flags) = node.local.ok_or("Missing root prior local")?;
        if flags & 8 != 0 {
            return Err("Scaled root prior local unsupported");
        }
        let (relative, relative_flags) = super::actor_reference::actor_relative_reference(
            context.reference_matrix,
            context.reference_flags,
            context.actor_matrix,
            context.actor_matrix_flags,
        )?;
        if let Some(q) = write.rotation {
            (local, flags) = super::actor_reference::compose_reference_basis(
                local,
                flags,
                super::pose_blend::quaternion_matrix(q),
                4,
                relative,
                relative_flags,
            )?;
            flags |= 4;
        }
        if let Some(position) = write.position {
            let p = super::actor_reference::actor_reference_position(
                position,
                context.reference_matrix,
                context.reference_flags,
                context.actor_matrix,
                context.actor_matrix_flags,
                context.height,
                context.add_height,
            )?;
            local[12..15].copy_from_slice(&p);
            flags |= 2;
        }
        let mut prepared = Self {
            bone_addresses: self.bone_addresses.clone(),
            nodes: self.nodes.clone(),
        };
        let actor = prepared
            .nodes
            .get_mut(&context.actor_address)
            .ok_or("Missing explicit actor node")?;
        if actor.flags & 0x400000 != 0 {
            return Err("Linked actor context unsupported");
        }
        actor.world = context.actor_matrix;
        actor.world_flags = context.actor_matrix_flags;
        prepared.with_prepared_locals(&BTreeMap::from([(bone, (local, flags))]))
    }
    /// Restricted ordinary linked-channel path. Root, reference-rebased and
    /// procedural destinations must be handled explicitly by another stage.
    pub fn with_plain_channel_writes(
        &self,
        rig: &Skeleton,
        pose: &SampledLocalPose,
        eligible: &BTreeSet<usize>,
    ) -> Result<Self, &'static str> {
        if pose.writes.len() != rig.objects.len() || self.bone_addresses.len() != rig.objects.len()
        {
            return Err("Local pose and rig length mismatch");
        }
        let mut writes = BTreeMap::new();
        for bone in eligible {
            let source = rig.objects.get(*bone).ok_or("Unknown eligible bone")?;
            let write = &pose.writes[*bone];
            if write.rotation.is_none() && write.position.is_none() {
                continue;
            }
            if source.slot == Some(0) || source.slot.is_none() {
                return Err("Root channels require reference context");
            }
            let node = &self.nodes[&self.bone_addresses[*bone]];
            let (prior, mut flags) = node
                .local
                .ok_or("Ordinary linked channel requires explicit prior local")?;
            if flags & 8 != 0 {
                return Err("Scaled local channels unsupported");
            }
            let matrix = write.apply(prior)?;
            //140b49fb0: output matrix+40 OR2 for position and OR4 for rotation.
            if write.position.is_some() {
                flags |= 2;
            }
            if write.rotation.is_some() {
                flags |= 4;
            }
            writes.insert(*bone, (matrix, flags));
        }
        self.with_prepared_locals(&writes)
    }
    pub fn new(
        rig: &Skeleton,
        bone_addresses: Vec<u64>,
        nodes: BTreeMap<u64, Node>,
    ) -> Result<Self, &'static str> {
        rig.topological_order()?;
        if bone_addresses.len() != rig.objects.len() {
            return Err("Runtime bone map length mismatch");
        }
        let mut used = BTreeSet::new();
        let keys: BTreeMap<_, _> = rig
            .objects
            .iter()
            .enumerate()
            .map(|(i, b)| (b.key.as_str(), i))
            .collect();
        for (index, address) in bone_addresses.iter().enumerate() {
            if *address == 0 || !used.insert(*address) {
                return Err("Null or aliased runtime bone");
            }
            let node = nodes.get(address).ok_or("Missing runtime bone")?;
            if let Some(parent) = rig.objects[index].linked_gao.as_ref() {
                let parent_index = *keys.get(parent.as_str()).ok_or("Unknown source parent")?;
                if node.parent != Some(bone_addresses[parent_index]) {
                    return Err(
                        "Runtime parent differs from source mapping; reparenting requires separate context",
                    );
                }
                if node.flags & 0x400000 == 0 || node.local.is_none() {
                    return Err("Source linked bone has no runtime local destination");
                }
            }
        }
        // Fail before use if any mapped hierarchy cannot be evaluated.
        compose_world_pose(&nodes)?;
        Ok(Self {
            bone_addresses,
            nodes,
        })
    }

    /// Apply complete prepared linked locals transactionally. Caller supplies
    /// flags; this API does not invent flag semantics or missing channels.
    pub fn with_prepared_locals(
        &self,
        writes: &BTreeMap<usize, ([f32; 16], u32)>,
    ) -> Result<Self, &'static str> {
        let mut nodes = self.nodes.clone();
        for (bone, (matrix, flags)) in writes {
            let address = *self.bone_addresses.get(*bone).ok_or("Unknown bone index")?;
            if matrix.iter().any(|v| !v.is_finite()) || flags & 8 != 0 {
                return Err("Nonfinite or scaled prepared local");
            }
            let node = nodes
                .get_mut(&address)
                .ok_or("Missing runtime destination")?;
            if node.flags & 0x400000 == 0 || node.local.is_none() {
                return Err("Prepared linked write requires linked runtime destination");
            }
            node.local = Some((*matrix, *flags));
        }
        compose_world_pose(&nodes)?;
        Ok(Self {
            bone_addresses: self.bone_addresses.clone(),
            nodes,
        })
    }

    pub fn worlds(&self) -> Result<BTreeMap<u64, ([f32; 16], u32)>, &'static str> {
        compose_world_pose(&self.nodes)
    }
}

#[cfg(test)]
#[path = "../../tests/unit/animation/runtime_pose.rs"]
mod tests;
